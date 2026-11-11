"""
Gnani AI Prisma v2.5 STT Service
--------------------------------
Wraps Gnani AI's Speech-to-Text REST endpoint for Hindi/Hinglish audio transcription.
"""

import json
import logging
import os
import shutil
import time
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv

logger = logging.getLogger("bimasakshi.gnani_service")

# Default verified endpoint
DEFAULT_STT_ENDPOINT = "https://api.vachana.ai/stt/v3"
MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB maximum upload


class GnaniSTTError(Exception):
    """Custom exception for Gnani STT failures."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


def get_gnani_api_key() -> str:
    """Retrieves GNANI_API_KEY from environment."""
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    key = (
        os.getenv("GNANI_API_KEY")
        or os.getenv("GNANI_API_KEY_ID")
        or os.getenv("VACHANA_API_KEY")
    )
    if not key or key.strip() in ("", "your_gnani_api_key_here"):
        raise GnaniSTTError("GNANI_API_KEY is not configured in .env.")
    return key.strip()


def check_ffmpeg_availability() -> Tuple[bool, Optional[str]]:
    """
    Checks whether the ffmpeg binary is accessible on the system PATH.
    Returns (True, path) if available, (False, None) otherwise.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    return (ffmpeg_path is not None, ffmpeg_path)


def normalize_to_pcm_wav(audio_bytes: bytes) -> bytes:
    """
    Normalizes any incoming audio stream (WebM, Opus, MP3, M4A, AAC, OGG, or non-standard WAV)
    into standard 16,000 Hz, 1-channel, 16-bit linear PCM WAV.
    If the audio is already a standard 16kHz PCM WAV, returns it directly.
    """
    # 1. Fast path: check if audio is already standard 16kHz 1-channel PCM WAV
    if len(audio_bytes) >= 44 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        try:
            import struct
            if audio_bytes[12:16] == b"fmt ":
                fmt_tag = struct.unpack("<H", audio_bytes[20:22])[0]
                channels = struct.unpack("<H", audio_bytes[22:24])[0]
                sample_rate = struct.unpack("<I", audio_bytes[24:28])[0]
                if fmt_tag == 1 and channels == 1 and sample_rate == 16000:
                    return audio_bytes
        except Exception:
            pass

    # 2. Verify FFmpeg availability before invoking conversion
    ffmpeg_ok, ffmpeg_bin = check_ffmpeg_availability()
    if not ffmpeg_ok:
        err_msg = (
            "FFmpeg executable was not found on system PATH. "
            "FFmpeg is required to normalize browser audio (WebM/Opus) into 16,000 Hz 16-bit linear PCM WAV for Gnani Prisma STT. "
            "Please install FFmpeg (e.g. 'winget install Gyan.FFmpeg' on Windows or 'sudo apt-get install ffmpeg' on Linux) "
            "and ensure it is accessible in your system PATH."
        )
        logger.error(err_msg)
        raise GnaniSTTError(err_msg)

    try:
        import subprocess
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", "pipe:0",
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            "pipe:1",
        ]
        proc = subprocess.run(
            cmd,
            input=audio_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20.0,
        )
        if proc.returncode == 0 and proc.stdout and proc.stdout[:4] == b"RIFF":
            logger.info(
                f"Audio normalized to 16kHz PCM WAV: input {len(audio_bytes)} bytes -> output {len(proc.stdout)} bytes"
            )
            return proc.stdout

        # Fallback for raw headerless PCM stream (e.g. 48kHz or 16kHz s16le)
        for rate in ["48000", "16000"]:
            pcm_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-f", "s16le",
                "-ar", rate,
                "-ac", "1",
                "-i", "pipe:0",
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                "pipe:1",
            ]
            pcm_proc = subprocess.run(
                pcm_cmd,
                input=audio_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10.0,
            )
            if pcm_proc.returncode == 0 and pcm_proc.stdout and pcm_proc.stdout[:4] == b"RIFF":
                logger.info(
                    f"Raw PCM normalized to 16kHz PCM WAV: input {len(audio_bytes)} bytes -> output {len(pcm_proc.stdout)} bytes"
                )
                return pcm_proc.stdout
    except GnaniSTTError:
        raise
    except Exception as e:
        logger.warning(f"Audio normalization via ffmpeg failed or ffmpeg error: {e}. Passing raw bytes.")

    return audio_bytes


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    content_type: str = "audio/wav",
    language_code: str = "hi-IN",
    model: str = "prisma-v2.5",
    timeout_sec: float = 30.0,
) -> Dict[str, Any]:
    """
    Sends audio bytes to Gnani Prisma v2.5 REST API and returns transcription data.

    Args:
        audio_bytes: Raw binary audio.
        filename: Filename with extension (e.g. .wav).
        content_type: MIME type of audio.
        language_code: Language code (default 'hi-IN').
        model: Model version (default 'prisma-v2.5').
        timeout_sec: Request timeout in seconds.

    Returns:
        dict: {
            "text": str (actual transcript),
            "model": str,
            "request_id": str or None,
            "latency_sec": float,
            "metadata": dict
        }

    Raises:
        GnaniSTTError: When file validation or API request fails.
    """
    if not audio_bytes or len(audio_bytes) == 0:
        raise GnaniSTTError("Audio payload is empty (0 bytes).", status_code=400)

    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise GnaniSTTError(
            f"Audio file size ({len(audio_bytes)} bytes) exceeds max limit of {MAX_AUDIO_SIZE_BYTES} bytes (10MB).",
            status_code=413,
        )

    # Normalize incoming audio (WebM, Opus, MP3, etc.) to 16kHz mono PCM WAV
    normalized_bytes = normalize_to_pcm_wav(audio_bytes)
    if normalized_bytes[:4] == b"RIFF" and normalized_bytes[8:12] == b"WAVE":
        effective_payload = normalized_bytes
        effective_filename = "recording.wav"
        effective_content_type = "audio/wav"
    else:
        effective_payload = audio_bytes
        effective_filename = filename
        effective_content_type = content_type

    api_key = get_gnani_api_key()
    endpoint = os.getenv("GNANI_STT_ENDPOINT", DEFAULT_STT_ENDPOINT)

    headers = {
        "X-API-Key-ID": api_key,
    }

    form_data = {
        "language_code": language_code,
        "model": model,
    }

    files = {
        "audio_file": (effective_filename, effective_payload, effective_content_type)
    }

    start_time = time.perf_counter()
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            data=form_data,
            files=files,
            timeout=timeout_sec,
        )
    except requests.exceptions.Timeout:
        latency = time.perf_counter() - start_time
        logger.error(f"Prisma STT request timed out after {latency:.2f}s")
        raise GnaniSTTError(f"Prisma STT request timed out after {latency:.2f}s", status_code=504)
    except requests.exceptions.ConnectionError as ce:
        logger.error(f"Prisma STT connection failed: {ce}")
        raise GnaniSTTError(f"Failed to connect to Prisma STT service: {ce}", status_code=502)
    except Exception as e:
        logger.error(f"Unexpected error calling Prisma STT: {e}")
        raise GnaniSTTError(f"STT request failed: {e}", status_code=500)

    latency = round(time.perf_counter() - start_time, 3)

    if response.status_code == 200:
        try:
            resp_json = response.json()
        except json.JSONDecodeError:
            resp_json = {"transcript": response.text}

        transcript = resp_json.get("transcript", "")
        request_id = resp_json.get("request_id")

        logger.info(
            f"Prisma STT completed in {latency:.2f}s (Req ID: {request_id}, "
            f"Chars: {len(transcript)})"
        )

        return {
            "text": transcript,
            "model": resp_json.get("model", model),
            "request_id": request_id,
            "latency_sec": latency,
            "metadata": {
                "detected_language": resp_json.get("detected_language_code"),
                "processing_time": resp_json.get("processing_time"),
            },
        }

    # Handle error responses
    error_detail = response.text
    try:
        err_json = response.json()
        if "detail" in err_json:
            error_detail = json.dumps(err_json["detail"])
    except Exception:
        pass

    logger.error(f"Prisma STT error {response.status_code}: {error_detail}")
    raise GnaniSTTError(
        f"Prisma STT API error (HTTP {response.status_code}): {error_detail}",
        status_code=response.status_code,
        response_body=response.text,
    )
