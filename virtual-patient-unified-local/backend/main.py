import asyncio
import base64
import json
import logging
import os
import re
import uuid
from pathlib import Path


from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from sqlalchemy import text

from config import FRONTEND_PUBLIC_DIR, settings
from prompt_utils import compact_prompt, truncate_prompt
from database import engine, init_db, validate_db_connection, SessionLocal
from models.db_models import User, UserRole, Case, CaseStatus, PracticeSession, PracticeStatus, AppSettings
from services.llm_service import LLMService
from services.tts_service import TTSService
from services.stt_service import STTService
from services.auth_service import decode_access_token
from services.password_utils import hash_password
from routes.auth import router as auth_router
from routes.cases import router as cases_router
from routes.assignments import router as assignments_router
from routes.practice import router as practice_router
from routes.settings import router as settings_router
from routes.viseme_generation import router as viseme_generation_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Virtual Patient — Unified Local")


async def _safe_send_json(websocket: WebSocket, payload: dict) -> bool:
    """Send JSON, returning False if the socket is closed.

    Prevents cascading errors like: 'Cannot call \"send\" once a close message has been sent.'
    """
    try:
        await websocket.send_json(payload)
        return True
    except WebSocketDisconnect:
        return False
    except RuntimeError:
        # Starlette raises RuntimeError when send is attempted after close.
        return False

# ── Rate limiting ──
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Startup: verify keys are present (never log key contents)
logger.info(f"OPENAI_API_KEY loaded: {'yes' if settings.openai_api_key else 'NO - MISSING'}")
logger.info(f"ELEVEN_LABS_API_KEY loaded: {'yes' if settings.eleven_labs_api_key else 'NO - MISSING'}")

# CORS — local Vite + optional FRONTEND_URL
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:7008",
]
if settings.frontend_url:
    _allowed_origins.append(settings.frontend_url.rstrip("/"))

logger.info(f"CORS allowed origins: {_allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    if request.method != "OPTIONS":
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
    return response


# ── Register API routers ──
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(assignments_router)
app.include_router(practice_router)
app.include_router(settings_router)
app.include_router(viseme_generation_router)

# 2D mouth shapes (Vite also serves public/; this lets the API host them if needed)
_PUBLIC = FRONTEND_PUBLIC_DIR
_SHAPES = _PUBLIC / "static" / "shapes"
if _SHAPES.is_dir():
    app.mount("/static/shapes", StaticFiles(directory=str(_SHAPES)), name="shapes")

# Mount local avatar uploads (only when NOT using Supabase Storage)
from services.storage_service import is_using_supabase, get_local_dir
if not is_using_supabase():
    _AVATAR_DIR = get_local_dir()
    app.mount("/uploads/avatars", StaticFiles(directory=str(_AVATAR_DIR)), name="avatars")

# Services
llm_service = LLMService()
tts_service = TTSService()
stt_service = STTService()


# ── Startup: validate config and init DB ──

def _seed_admin_user() -> None:
    if not settings.seed_admin_email or not settings.seed_admin_password:
        return
    db = SessionLocal()
    try:
        email = settings.seed_admin_email.strip().lower()
        if db.query(User).filter(User.email == email).first():
            return
        uid = uuid.uuid4().hex
        u = User(
            id=uid,
            email=email,
            display_name=settings.seed_admin_display_name,
            role=UserRole.ADMIN,
            is_active=True,
            password_hash=hash_password(settings.seed_admin_password),
        )
        db.add(u)
        db.commit()
        logger.info("Seeded admin user from SEED_ADMIN_EMAIL")
    finally:
        db.close()


@app.on_event("startup")
async def startup():
    """Initialize DB and optional admin seed (local)."""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set — LLM calls will fail")
    if not settings.eleven_labs_api_key:
        logger.warning("ELEVEN_LABS_API_KEY is not set — TTS will fail")
    if settings.jwt_secret.startswith("change-me"):
        logger.warning("JWT_SECRET is using the default — set a strong secret in .env for anything beyond local dev")

    try:
        validate_db_connection()
        init_db()
        _seed_admin_user()
        logger.info("Database initialized (unified-local)")
    except Exception as exc:
        logger.error(f"Startup database error: {exc}")
        raise


@app.on_event("shutdown")
async def shutdown():
    """Gracefully release database connections on shutdown."""
    logger.info("Shutting down...")
    engine.dispose()


@app.get("/")
async def root():
    index_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "AIMII API is running. Frontend is served separately."}


@app.get("/health")
@app.get("/api/health")
@limiter.limit("60/minute")
async def health(request: Request):
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_ok = True
        db.close()
    except Exception:
        pass

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "database": "connected" if db_ok else "unreachable",
        "openai_key_set": bool(settings.openai_api_key),
        "elevenlabs_key_set": bool(settings.eleven_labs_api_key),
    }


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for chunked TTS generation."""
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def should_flush_stream_chunk(buffer: str, clean: str, first_chunk: bool) -> bool:
    """Size-based flush to avoid punctuation-induced stop/start between chunks."""
    if not clean:
        return False
    at_break = buffer.endswith((" ", "\n"))
    # First clause often ends with comma — flush early for TTS+Rhubarb.
    if first_chunk and len(clean) >= 14 and at_break:
        if re.search(r"[,;:]$", clean.rstrip()):
            return True
    if first_chunk:
        return len(clean) >= 24 and at_break
    return len(clean) >= 80 and at_break


def _save_session(user_id: str, case_id: str, history: list[dict]):
    """Persist conversation history to DB and auto-mark as in_progress."""
    db = SessionLocal()
    try:
        practice = db.query(PracticeSession).filter_by(user_id=user_id, case_id=case_id).first()
        if practice:
            practice.conversation_history = json.dumps(history)
            # Auto-promote to in_progress once conversation starts
            if practice.status == PracticeStatus.NOT_STARTED and len(history) > 0:
                practice.status = PracticeStatus.IN_PROGRESS
            db.commit()
    finally:
        db.close()


def _clear_conversation_on_disconnect(user_id: str, case_id: str) -> None:
    """When the practice WebSocket closes (tab closed, navigation away, etc.), drop in-progress chat.

    Submitted sessions are unchanged so admin/student transcripts stay available.
    """
    db = SessionLocal()
    try:
        practice = db.query(PracticeSession).filter_by(user_id=user_id, case_id=case_id).first()
        if not practice:
            return
        if practice.status == PracticeStatus.SUBMITTED:
            return
        practice.conversation_history = "[]"
        practice.status = PracticeStatus.NOT_STARTED
        db.commit()
    finally:
        db.close()


@app.websocket("/ws/conversation")
async def conversation_websocket(websocket: WebSocket):
    """Main conversation WebSocket endpoint with per-user session persistence.

    Protocol:
        Client MUST send first message: {"type": "auth", "token": "JWT", "case_id": "..."}

        Client sends JSON: {"type": "text", "content": "..."} or
                           {"type": "audio", "audio_data": "<base64>"}
                           {"type": "reset"}

        Server sends JSON: {"type": "history", "messages": [...]} (prior conversation on connect)
                           {"type": "transcript", "content": "..."} (student's transcribed text)
                           {"type": "response_stream", "content": "..."} (patient reply while still generating)
                           {"type": "response_text", "content": "..."} (patient's full text response)
                           {"type": "audio_chunk", "data": "<base64 mp3>", "seq": N, "turn_id": T, "cues": [...]}
                           {"type": "audio_end"} (signals all audio sent)
                           {"type": "error", "content": "..."} (error message)
    """
    await websocket.accept()

    # ── Authenticate via first message (not query string, to keep token out of server logs) ──
    try:
        raw_auth = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_msg = json.loads(raw_auth)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await websocket.close(code=4001, reason="Auth message required")
        return

    if auth_msg.get("type") != "auth":
        await websocket.close(code=4001, reason="First message must be auth")
        return

    token = auth_msg.get("token")
    case_id = auth_msg.get("case_id")

    if not token or not case_id:
        await websocket.close(code=4001, reason="Missing token or case_id")
        return

    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    user_id = payload["sub"]

    # ── Load case and session from DB ──
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            await websocket.close(code=4004, reason="Case not found")
            return

        # Build system prompt: compact + optional cap to limit tokens (latency).
        global_row = db.query(AppSettings).filter(AppSettings.key == "global_prompt").first()
        raw_global = global_row.value.strip() if global_row and global_row.value else ""
        global_prompt = compact_prompt(raw_global)
        if settings.global_prompt_max_chars > 0:
            global_prompt = truncate_prompt(global_prompt, settings.global_prompt_max_chars)
        case_prompt = compact_prompt(case.system_prompt or "")
        if global_prompt:
            system_prompt = global_prompt + "\n\n" + case_prompt
        else:
            system_prompt = case_prompt
        voice_id = case.voice_id or settings.default_voice_id

        practice = db.query(PracticeSession).filter_by(user_id=user_id, case_id=case_id).first()
        if not practice:
            practice = PracticeSession(user_id=user_id, case_id=case_id, conversation_history="[]")
            db.add(practice)
            db.commit()

        try:
            existing_history = json.loads(practice.conversation_history)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Corrupted history for user={user_id}, case={case_id} — resetting")
            existing_history = []
    finally:
        db.close()

    # Per-connection session state
    session_state = {
        "system_prompt": system_prompt,
        "conversation_history": existing_history,
        "voice_id": voice_id,
        "user_id": user_id,
        "case_id": case_id,
        "lip_turn": 0,
        "active_turn": False,
    }

    logger.info(f"WebSocket connected: user={user_id}, case={case_id}")

    # Send existing history to client so it can restore the chat
    if existing_history:
        await websocket.send_json({
            "type": "history",
            "messages": existing_history,
        })

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                raise
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _safe_send_json(websocket, {"type": "error", "content": "Invalid JSON"})
                continue
            msg_type = msg.get("type")

            if msg_type == "text":
                user_text = msg.get("content", "").strip()
                if not user_text:
                    continue
                if len(user_text) > 5000:
                    await _safe_send_json(websocket, {"type": "error", "content": "Message too long"})
                    continue
                await handle_conversation_turn(websocket, user_text, session_state)

            elif msg_type == "audio":
                audio_b64 = msg.get("audio_data", "")
                if not audio_b64:
                    continue
                # Reject payloads over 10 MB (base64-encoded) to prevent DoS
                if len(audio_b64) > 10 * 1024 * 1024:
                    await websocket.send_json({"type": "error", "content": "Audio payload too large"})
                    continue
                audio_bytes = base64.b64decode(audio_b64)

                try:
                    user_text = await stt_service.transcribe(audio_bytes)
                    logger.info(f"Transcribed: {user_text}")
                    await _safe_send_json(websocket, {
                        "type": "transcript",
                        "content": user_text,
                    })
                    await handle_conversation_turn(websocket, user_text, session_state)
                except Exception as e:
                    logger.error(f"STT error: {e}")
                    await _safe_send_json(websocket, {
                        "type": "error",
                        "content": "Transcription failed. Please try again.",
                    })

            elif msg_type == "setup":
                # Legacy support — no-op since setup is now automatic
                await _safe_send_json(websocket, {
                    "type": "info",
                    "content": "Session ready",
                })

            elif msg_type == "reset":
                session_state["conversation_history"] = []
                _save_session(user_id, case_id, [])
                await _safe_send_json(websocket, {
                    "type": "info",
                    "content": "Conversation reset",
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}, case={case_id}")
        # Don't wipe state mid-turn (browser can reconnect frequently during long responses).
        if not session_state.get("active_turn", False):
            _clear_conversation_on_disconnect(user_id, case_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def handle_conversation_turn(websocket: WebSocket, user_text: str, session_state: dict):
    """LLM stream + progressive text; send audio immediately with guaranteed cues."""

    session_state["active_turn"] = True
    session_state["lip_turn"] = session_state.get("lip_turn", 0) + 1
    turn_id = session_state["lip_turn"]

    logger.info(f"User: {user_text}")
    full_response = ""
    stream_buffer = ""
    first_chunk_scheduled = False
    loop = asyncio.get_running_loop()
    turn_start = loop.time()
    first_token_time = None
    first_queue_time = None
    first_audio_time = None

    chunk_index = 0
    results_buf: dict[int, tuple[str | None, list]] = {}
    next_send = 0
    send_lock = asyncio.Lock()
    chunk_tasks: list[asyncio.Task] = []

    cancel_event = asyncio.Event()

    async def emit_chunk_in_order(index: int, audio_b64: str | None, cues: list | None):
        """Ordered audio path; cues may arrive later (lip_cues)."""
        nonlocal next_send, first_audio_time
        async with send_lock:
            results_buf[index] = (audio_b64, cues if cues is not None else [])
            while next_send in results_buf:
                b64, cue_list = results_buf.pop(next_send)
                if b64:
                    ok = await _safe_send_json(websocket, {
                        "type": "audio_chunk",
                        "data": b64,
                        "seq": next_send,
                        "turn_id": turn_id,
                        "cues": cue_list,
                    })
                    if not ok:
                        cancel_event.set()
                        return
                    if first_audio_time is None:
                        first_audio_time = loop.time()
                next_send += 1

    # Conveyor belt: TTS for chunk N+1 while chunk N may already be playing.
    tts_semaphore = asyncio.Semaphore(8)

    async def process_chunk(index: int, text: str):
        text = text.strip()
        if not text:
            await emit_chunk_in_order(index, None, None)
            return
        try:
            if cancel_event.is_set():
                return
            # 1) TTS + timestamp-driven cues (bounded concurrency)
            async with tts_semaphore:
                audio_bytes, cues = await tts_service.text_to_audio_with_best_cues(
                    text=text,
                    voice_id=session_state["voice_id"],
                )
            if not audio_bytes:
                await emit_chunk_in_order(index, None, None)
                return
            if cancel_event.is_set():
                return

            # Cues are guaranteed from either ElevenLabs alignment or fallback synthesis.
            b64 = base64.b64encode(audio_bytes).decode("utf-8")
            await emit_chunk_in_order(index, b64, cues)
        except Exception as e:
            logger.exception("TTS/Rhubarb chunk error")
            await emit_chunk_in_order(index, None, None)

    def schedule_tts(text: str):
        nonlocal chunk_index, first_chunk_scheduled, first_queue_time
        chunk_text = text.strip()
        if not chunk_text:
            return
        i = chunk_index
        chunk_index += 1
        if not first_chunk_scheduled:
            first_chunk_scheduled = True
            first_queue_time = loop.time()
        chunk_tasks.append(asyncio.create_task(process_chunk(i, chunk_text)))

    last_stream_ts: float | None = None
    STREAM_INTERVAL = 0.06

    try:
        async for token in llm_service.stream_response(
            system_prompt=session_state["system_prompt"],
            history=session_state["conversation_history"],
            user_message=user_text,
        ):
            if first_token_time is None:
                first_token_time = loop.time()
            full_response += token
            stream_buffer += token

            clean = stream_buffer.strip()
            if clean:
                now = loop.time()
                if last_stream_ts is None or now - last_stream_ts >= STREAM_INTERVAL:
                    ok = await _safe_send_json(websocket, {
                        "type": "response_stream",
                        "content": full_response,
                    })
                    if not ok:
                        cancel_event.set()
                        return
                    last_stream_ts = now

                first_until_flush = not first_chunk_scheduled
                if should_flush_stream_chunk(stream_buffer, clean, first_until_flush):
                    schedule_tts(stream_buffer)
                    stream_buffer = ""

        logger.info(f"Patient: {full_response}")

        await websocket.send_json({
            "type": "response_stream",
            "content": full_response,
        })
        # If socket closed during final stream, stop.
        if cancel_event.is_set():
            return

        tail = stream_buffer.strip()
        if tail:
            schedule_tts(tail)

        ok = await _safe_send_json(websocket, {
            "type": "response_text",
            "content": full_response,
        })
        if not ok:
            cancel_event.set()
            return

        if not chunk_tasks:
            await _safe_send_json(websocket, {
                "type": "error",
                "content": "Audio generation failed — text response was sent",
            })
        else:
            await asyncio.gather(*chunk_tasks)

        if first_token_time is not None:
            logger.info(f"[latency] first_token_ms={int((first_token_time - turn_start) * 1000)}")
        if first_queue_time is not None:
            logger.info(f"[latency] first_chunk_scheduled_ms={int((first_queue_time - turn_start) * 1000)}")
        if first_audio_time is not None:
            logger.info(f"[latency] first_audio_chunk_sent_ms={int((first_audio_time - turn_start) * 1000)}")

        await _safe_send_json(websocket, {"type": "audio_end"})

        session_state["conversation_history"].append(
            {"role": "user", "content": user_text}
        )
        session_state["conversation_history"].append(
            {"role": "assistant", "content": full_response}
        )

        if len(session_state["conversation_history"]) > 40:
            session_state["conversation_history"] = session_state["conversation_history"][-40:]

        _save_session(
            session_state["user_id"],
            session_state["case_id"],
            session_state["conversation_history"],
        )

    except Exception as e:
        logger.exception("Conversation turn error")
        await _safe_send_json(websocket, {
            "type": "error",
            "content": "Failed to generate response. Please try again.",
        })
    finally:
        session_state["active_turn"] = False


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)
