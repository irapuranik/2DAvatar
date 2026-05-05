from openai import AsyncOpenAI

from config import settings


class STTService:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes to text using OpenAI Whisper API.

        Args:
            audio_bytes: Raw audio data (webm, wav, mp3, etc.)
            filename: Filename hint for the API (helps with format detection).

        Returns:
            Transcribed text string.
        """
        transcript = await self._client.audio.transcriptions.create(
            model=settings.whisper_model,
            file=(filename, audio_bytes),
        )
        return transcript.text
