"""POST /api/tts — speak any text the app is showing.

Deliberately a standalone endpoint rather than audio attached to every chat
and journal reply. Synthesis adds seconds and costs credits, and most replies
are read, not listened to — so the client asks for audio when the traveler
taps play, and the same endpoint serves Ask answers, journal responses,
recommendations, and the morning guide without any of them knowing about it.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app import config
from app.services import tts

router = APIRouter()


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1)
    # Both optional: the defaults are the Greek voice and Flash 2.5.
    voice_id: str | None = None
    model_id: str | None = None


@router.post("/api/tts")
def speak(req: SpeakRequest):
    """Return MP3 audio for `text`.

    Responds with audio/mpeg bytes, not JSON — the client plays the body
    directly. `X-Hodegos-Cached` says whether it cost any credits.
    """
    try:
        audio, cached = tts.synthesize(req.text, req.voice_id, req.model_id)
    except tts.TTSError as exc:
        # 503 when the server is unconfigured, 502 when the upstream failed —
        # the client can retry the second and never the first.
        status = 503 if "not set" in str(exc) else 502
        raise HTTPException(status, str(exc)) from exc
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "X-Hodegos-Cached": "1" if cached else "0",
            "Cache-Control": "private, max-age=86400",
            "Content-Length": str(len(audio)),
        },
    )


@router.post("/api/tts/preview")
def preview(req: SpeakRequest):
    """What the voice will actually be given, without spending credits.

    Markdown stripping is the part most likely to surprise, so it is
    inspectable on its own.
    """
    spoken = tts.speakable(req.text)
    return {
        "spoken_text": spoken,
        "characters": len(spoken),
        "original_characters": len(req.text),
        "within_limit": len(spoken) <= config.TTS_MAX_CHARS,
        "voice_id": req.voice_id or config.TTS_VOICE_ID,
        "model_id": req.model_id or config.TTS_MODEL,
    }


@router.get("/api/tts/voices")
def list_voices():
    try:
        return {"voices": tts.voices(), "default_voice_id": config.TTS_VOICE_ID}
    except tts.TTSError as exc:
        raise HTTPException(503, str(exc)) from exc
