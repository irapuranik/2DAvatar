import io
import os
import json
import logging
import shutil
import subprocess
import tempfile
import asyncio
import re
import base64
from typing import Tuple
from elevenlabs.client import AsyncElevenLabs
from config import settings

logger = logging.getLogger(__name__)

# FFmpeg for MP3→WAV (Rhubarb input). Avoid pydub here: it often fails to find ffmpeg in PATH.
os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"


def _ffmpeg_mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            mp3_path,
            "-ac", "1",
            "-ar", "16000",
            wav_path,
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if proc.returncode != 0:
        logger.error(
            "ffmpeg mp3→wav failed (is ffmpeg installed?): %s",
            (proc.stderr or proc.stdout or "")[:800],
        )
        return False
    return True


def generate_cues_sync(audio_bytes: bytes) -> list:
    """Decode MP3 with ffmpeg, run Rhubarb on WAV, return mouthCues."""
    mp3_path = None
    wav_path = None
    try:
        mp3_fd, mp3_path = tempfile.mkstemp(suffix=".mp3")
        os.write(mp3_fd, audio_bytes)
        os.close(mp3_fd)

        wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(wav_fd)
        if not _ffmpeg_mp3_to_wav(mp3_path, wav_path):
            return []

        rhubarb_exe = getattr(settings, "rhubarb_path", "") or shutil.which("rhubarb") or "/opt/homebrew/bin/rhubarb"
        if not os.path.isfile(rhubarb_exe):
            logger.error("Rhubarb binary not found at %s — set RHUBARB_PATH in .env", rhubarb_exe)
            return []

        proc = subprocess.run(
            [rhubarb_exe, "-f", "json", wav_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            logger.warning(
                "rhubarb failed (exit %s): %s",
                proc.returncode,
                (proc.stderr or proc.stdout or "")[:600],
            )
            return []
        data = json.loads(proc.stdout)
        return data.get("mouthCues", [])
    except subprocess.TimeoutExpired:
        logger.error("Rhubarb/ffmpeg timed out")
        return []
    except json.JSONDecodeError as e:
        logger.error("Invalid Rhubarb JSON: %s", e)
        return []
    except Exception as e:
        logger.exception("generate_cues_sync: %s", e)
        return []
    finally:
        for p in (mp3_path, wav_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


class TTSService:
    def __init__(self):
        self._client = AsyncElevenLabs(api_key=settings.eleven_labs_api_key)

    @staticmethod
    def _estimate_mp3_duration_seconds(audio_bytes: bytes) -> float:
        """Estimate MP3 duration from configured output bitrate."""
        out_fmt = getattr(settings, "eleven_labs_output_format", "mp3_22050_32")
        m = re.search(r"_(\d+)$", str(out_fmt))
        kbps = int(m.group(1)) if m else 32
        # bytes/s = (kbps * 1000) / 8
        bytes_per_sec = max(1.0, (kbps * 1000.0) / 8.0)
        return max(0.35, len(audio_bytes) / bytes_per_sec)

    @staticmethod
    def _word_to_viseme(word: str) -> str:
        w = word.lower()
        if any(ch in w for ch in ("o", "u")):
            return "E"
        if any(ch in w for ch in ("a",)):
            return "A"
        if any(ch in w for ch in ("e", "i", "y")):
            return "C"
        if any(ch in w for ch in ("m", "b", "p")):
            return "A"
        if any(ch in w for ch in ("f", "v")):
            return "G"
        if any(ch in w for ch in ("t", "d", "n", "s", "z", "l", "r")):
            return "D"
        if any(ch in w for ch in ("k", "g", "q", "x")):
            return "H"
        return "B"

    def fallback_cues_for_text(self, text: str, audio_bytes: bytes) -> list:
        """Generate quick, deterministic cues so lips always move with audio."""
        duration = self._estimate_mp3_duration_seconds(audio_bytes)
        words = [w for w in re.findall(r"[A-Za-z']+", text) if w]
        if not words:
            return [{"start": 0.0, "end": round(duration, 3), "value": "X"}]

        cues: list[dict] = []
        total_weight = sum(max(1, len(w)) for w in words)
        speaking_ratio = 0.82
        speech_total = duration * speaking_ratio
        pause_total = max(0.0, duration - speech_total)
        pause_each = pause_total / max(1, len(words))

        t = 0.0
        for w in words:
            seg = speech_total * (max(1, len(w)) / total_weight)
            end = min(duration, t + seg)
            if end > t:
                cues.append({
                    "start": round(t, 3),
                    "end": round(end, 3),
                    "value": self._word_to_viseme(w),
                })
            t = end
            if t >= duration:
                break
            pause_end = min(duration, t + pause_each)
            if pause_end > t:
                cues.append({
                    "start": round(t, 3),
                    "end": round(pause_end, 3),
                    "value": "X",
                })
            t = pause_end
            if t >= duration:
                break

        if not cues:
            return [{"start": 0.0, "end": round(duration, 3), "value": "X"}]
        if cues[-1]["end"] < duration:
            cues.append({
                "start": round(cues[-1]["end"], 3),
                "end": round(duration, 3),
                "value": "X",
            })
        return cues

    @staticmethod
    def _char_to_viseme(ch: str) -> str:
        c = ch.lower()
        if c in {" ", "\t", "\n"}:
            return "X"
        if c in {".", ",", "!", "?", ":", ";", "-", "(", ")", "\"", "'"}:
            return "X"
        if c in {"a"}:
            return "A"
        if c in {"e", "i", "y"}:
            return "C"
        if c in {"o", "u"}:
            return "E"
        if c in {"m", "b", "p"}:
            return "A"
        if c in {"f", "v"}:
            return "G"
        if c in {"t", "d", "n", "s", "z", "l", "r"}:
            return "D"
        if c in {"k", "g", "q", "x"}:
            return "H"
        if "a" <= c <= "z":
            return "B"
        return "X"

    @staticmethod
    def _char_to_viseme_context(chars: list[str], i: int) -> str:
        c = (chars[i] or "").lower()
        nxt = (chars[i + 1] if i + 1 < len(chars) else "").lower()
        prv = (chars[i - 1] if i - 1 >= 0 else "").lower()
        pair = c + nxt

        if c in {" ", "\t", "\n"}:
            return "X"
        if c in {".", ",", "!", "?", ":", ";", "-", "(", ")", "\"", "'", "[", "]", "{", "}"}:
            return "X"

        # Multi-character consonant hints.
        if pair in {"th"}:
            return "F"
        if pair in {"sh", "ch"}:
            return "H"
        if pair in {"ph"}:
            return "G"
        if pair in {"qu"}:
            return "H"

        # Vowels.
        if c in {"a"}:
            return "A"
        if c in {"e", "i", "y"}:
            return "C"
        if c in {"o", "u", "w"}:
            return "E"

        # Consonants.
        if c in {"m", "b", "p"}:
            return "A"
        if c in {"f", "v"}:
            return "G"
        if c in {"k", "g", "q", "x"}:
            return "H"
        if c in {"t", "d", "n", "s", "z", "l", "r", "c", "j"}:
            # Soften "r" after vowels to avoid over-snapping.
            if c == "r" and prv in {"a", "e", "i", "o", "u"}:
                return "B"
            return "D"

        if "a" <= c <= "z":
            return "B"
        return "X"

    @staticmethod
    def _fill_x_gaps(cues: list[dict], audio_duration: float) -> list[dict]:
        if not cues:
            return [{"start": 0.0, "end": round(audio_duration, 3), "value": "X"}]
        out: list[dict] = []
        t = 0.0
        for cue in cues:
            s = max(t, float(cue["start"]))
            e = max(s, float(cue["end"]))
            if s >= audio_duration:
                break
            e = min(e, audio_duration)
            if s > t:
                out.append({"start": round(t, 3), "end": round(s, 3), "value": "X"})
            if e > s:
                out.append({"start": round(s, 3), "end": round(e, 3), "value": cue["value"]})
            t = e
        if t < audio_duration:
            out.append({"start": round(t, 3), "end": round(audio_duration, 3), "value": "X"})
        return out

    @staticmethod
    def _apply_duration_calibration(cues: list[dict], audio_duration: float) -> list[dict]:
        if not cues:
            return cues
        # Per-shape tweak to better match this avatar sprite set.
        scale = {
            "A": 1.10,
            "B": 0.92,
            "C": 1.02,
            "D": 0.96,
            "E": 1.10,
            "F": 1.06,
            "G": 1.06,
            "H": 1.04,
            "X": 1.00,
        }
        out = [dict(c) for c in cues]
        for i, cue in enumerate(out):
            v = str(cue["value"])
            if v == "X":
                continue
            s = float(cue["start"])
            e = float(cue["end"])
            dur = max(0.0, e - s)
            if dur <= 0:
                continue
            center = (s + e) / 2.0
            target = dur * scale.get(v, 1.0)
            # Clamp growth/shrink per cue to avoid timeline instability.
            max_delta = 0.028
            target = max(dur - max_delta, min(dur + max_delta, target))
            ns = center - target / 2.0
            ne = center + target / 2.0

            left_bound = 0.0 if i == 0 else float(out[i - 1]["end"])
            right_bound = audio_duration if i + 1 >= len(out) else float(out[i + 1]["start"])
            ns = max(left_bound, ns)
            ne = min(right_bound, ne)
            if ne - ns > 0.004:
                cue["start"] = round(ns, 3)
                cue["end"] = round(ne, 3)
        return out

    @staticmethod
    def _merge_adjacent_same(cues: list[dict]) -> list[dict]:
        if not cues:
            return cues
        merged: list[dict] = [dict(cues[0])]
        for cue in cues[1:]:
            prev = merged[-1]
            if cue["value"] == prev["value"] and float(cue["start"]) <= float(prev["end"]) + 0.001:
                prev["end"] = round(max(float(prev["end"]), float(cue["end"])), 3)
            else:
                merged.append(dict(cue))
        return merged

    def cues_from_alignment(self, alignment, audio_duration: float) -> list:
        """Convert ElevenLabs character alignment into Rhubarb-style A-H/X cues."""
        if not alignment:
            return []
        chars = list(getattr(alignment, "characters", []) or [])
        starts = list(getattr(alignment, "character_start_times_seconds", []) or [])
        ends = list(getattr(alignment, "character_end_times_seconds", []) or [])
        n = min(len(chars), len(starts), len(ends))
        if n == 0:
            return []

        raw: list[dict] = []
        for i in range(n):
            s = float(starts[i])
            e = float(ends[i])
            if e <= s:
                continue
            s = max(0.0, min(s, audio_duration))
            e = max(0.0, min(e, audio_duration))
            if e <= s:
                continue
            raw.append({
                "start": round(s, 3),
                "end": round(e, 3),
                "value": self._char_to_viseme_context(chars, i),
            })
        if not raw:
            return []

        # Merge consecutive same-viseme segments.
        merged: list[dict] = [raw[0].copy()]
        for cue in raw[1:]:
            prev = merged[-1]
            if cue["value"] == prev["value"] and cue["start"] <= prev["end"] + 0.01:
                prev["end"] = max(prev["end"], cue["end"])
            else:
                merged.append(cue.copy())

        # Coarticulation: pull non-silence slightly into neighbor silence.
        for i, cue in enumerate(merged):
            if cue["value"] == "X":
                continue
            lead = 0.012
            lag = 0.012
            left_bound = 0.0 if i == 0 else float(merged[i - 1]["start"])
            right_bound = audio_duration if i + 1 >= len(merged) else float(merged[i + 1]["end"])
            cue["start"] = round(max(left_bound, float(cue["start"]) - lead), 3)
            cue["end"] = round(min(right_bound, float(cue["end"]) + lag), 3)

        # Smooth extremely short non-silence segments to avoid visual chatter.
        min_dur = 0.055
        smoothed: list[dict] = []
        for cue in merged:
            dur = float(cue["end"]) - float(cue["start"])
            if dur < min_dur and cue["value"] != "X" and smoothed:
                smoothed[-1]["end"] = max(smoothed[-1]["end"], cue["end"])
                continue
            smoothed.append(cue)

        if not smoothed:
            return []
        smoothed = self._fill_x_gaps(smoothed, audio_duration)
        smoothed = self._apply_duration_calibration(smoothed, audio_duration)
        smoothed = self._fill_x_gaps(smoothed, audio_duration)
        return self._merge_adjacent_same(smoothed)

    async def text_to_audio_only(self, text: str, voice_id: str | None = None) -> bytes:
        """ElevenLabs MP3 only — fastest path to first sound (Rhubarb runs separately)."""
        voice_id = voice_id or settings.default_voice_id
        model_id = getattr(settings, "eleven_labs_model", "eleven_turbo_v2_5")

        out_fmt = getattr(settings, "eleven_labs_output_format", "mp3_22050_32")
        audio_generator = self._client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format=out_fmt,
        )

        audio_buffer = io.BytesIO()
        async for chunk in audio_generator:
            if isinstance(chunk, bytes):
                audio_buffer.write(chunk)

        return audio_buffer.getvalue()

    async def text_to_audio_with_best_cues(self, text: str, voice_id: str | None = None) -> Tuple[bytes, list]:
        """Fast path: ElevenLabs audio+timestamps; fallback to heuristic cues."""
        voice_id = voice_id or settings.default_voice_id
        model_id = getattr(settings, "eleven_labs_model", "eleven_turbo_v2_5")
        out_fmt = getattr(settings, "eleven_labs_output_format", "mp3_22050_32")
        try:
            resp = await self._client.text_to_speech.convert_with_timestamps(
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                output_format=out_fmt,
            )
            audio_bytes = base64.b64decode(resp.audio_base_64) if getattr(resp, "audio_base_64", "") else b""
            if not audio_bytes:
                return b"", []
            duration = self._estimate_mp3_duration_seconds(audio_bytes)
            alignment = getattr(resp, "alignment", None) or getattr(resp, "normalized_alignment", None)
            cues = self.cues_from_alignment(alignment, duration)
            if not cues:
                cues = self.fallback_cues_for_text(text, audio_bytes)
            return audio_bytes, cues
        except Exception:
            logger.exception("convert_with_timestamps failed; using fallback cue generation")
            audio_bytes = await self.text_to_audio_only(text=text, voice_id=voice_id)
            if not audio_bytes:
                return b"", []
            return audio_bytes, self.fallback_cues_for_text(text, audio_bytes)

    async def cues_for_audio(self, audio_bytes: bytes) -> list:
        """Rhubarb lip-sync for an existing MP3 (run off the playback hot path)."""
        return await asyncio.to_thread(generate_cues_sync, audio_bytes)

    async def text_to_audio_with_cues(self, text: str, voice_id: str | None = None) -> Tuple[bytes, list]:
        """Single-call convenience (not used on the low-latency path)."""
        audio_bytes = await self.text_to_audio_only(text, voice_id=voice_id)
        cues = await self.cues_for_audio(audio_bytes)
        return audio_bytes, cues
