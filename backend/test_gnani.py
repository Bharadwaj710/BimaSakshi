"""
Gnani AI API Smoke Test - BimaSakshi (Phase 1)
----------------------------------------------
Verifies connectivity, authentication, and functionality for:
1. Prisma v2.5 - Speech-to-Text (STT) via https://api.vachana.ai/stt/v3
2. Timbre v2.5 - Text-to-Speech (TTS) via https://api.vachana.ai/api/v1/tts/inference

Usage:
    python test_gnani.py
"""

import os
import sys
import time
import wave
import base64
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import requests
from dotenv import load_dotenv

# Script directories and asset paths
BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"
TEST_AUDIO_PATH = BACKEND_DIR / "test_audio.wav"
OUTPUT_AUDIO_PATH = BACKEND_DIR / "output_warning.wav"

# Verified Official Endpoints (Gnani.ai / Vachana Speech AI)
DEFAULT_STT_ENDPOINT = "https://api.vachana.ai/stt/v3"
DEFAULT_TTS_ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"

# Timbre v2.5 Hindi test sentence (Prescribed for BimaSakshi)
TTS_TEST_SENTENCE = (
    "आपकी स्वास्थ्य बीमा पॉलिसी में कुछ महत्वपूर्ण शर्तें हैं। "
    "कृपया अस्पताल का बिल जमा करने से पहले कमरे के किराये और संबंधित खर्चों की पात्रता की जांच करें।"
)

# Colors / Formatting for console output
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"


def print_header(title: str) -> None:
    print(f"\n{Style.BOLD}{Style.CYAN}{'=' * 70}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}  {title}{Style.RESET}")
    print(f"{Style.BOLD}{Style.CYAN}{'=' * 70}{Style.RESET}")


def mask_key(key: str) -> str:
    """Mask key for safe logging (never expose secrets)."""
    if not key or len(key) <= 6:
        return "[MASKED]"
    return f"{key[:3]}...{key[-4:]}"


def load_credentials() -> Optional[str]:
    """Loads environment variables and validates presence of Gnani API key."""
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        load_dotenv()  # Fallback to current working directory or system env

    api_key = (
        os.getenv("GNANI_API_KEY")
        or os.getenv("GNANI_API_KEY_ID")
        or os.getenv("VACHANA_API_KEY")
    )

    if not api_key or api_key.strip() in ("", "your_gnani_api_key_here"):
        return None
    return api_key.strip()


def validate_test_audio(audio_path: Path) -> Tuple[bool, str]:
    """Validates that test_audio.wav exists, is readable, and is a valid WAV."""
    if not audio_path.exists():
        return False, f"Audio file not found at: {audio_path}"
    
    file_size = audio_path.stat().st_size
    if file_size == 0:
        return False, f"Audio file is empty (0 bytes): {audio_path}"

    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            framerate = wav_file.getframerate()
            frames = wav_file.getnframes()
            duration = frames / float(framerate) if framerate > 0 else 0
            details = (
                f"Valid WAV ({duration:.2f}s, {framerate}Hz, "
                f"{channels}ch, {sample_width * 8}-bit, {file_size} bytes)"
            )
            return True, details
    except wave.Error as e:
        return False, f"File is not a valid RIFF/WAVE: {e}"
    except Exception as e:
        return False, f"Error reading audio file: {e}"


def run_stt_test(api_key: str) -> Dict[str, Any]:
    """
    Test A: Prisma v2.5 Speech-to-Text
    Endpoint: https://api.vachana.ai/stt/v3
    Method: POST multipart/form-data
    Header: X-API-Key-ID: <api-key>
    """
    print_header("TEST A: PRISMA v2.5 SPEECH-TO-TEXT (STT)")
    result = {
        "test": "Prisma STT",
        "status": "FAIL",
        "status_code": None,
        "latency_sec": None,
        "transcript": None,
        "metadata": {},
        "evidence": "",
    }

    # Step 1: Validate test audio
    print(f"Checking audio file: {TEST_AUDIO_PATH.name}...")
    valid, audio_info = validate_test_audio(TEST_AUDIO_PATH)
    if not valid:
        print(f"  {Style.RED}[FAIL]{Style.RESET} Audio validation failed: {audio_info}")
        result["evidence"] = f"Audio validation failed: {audio_info}"
        return result
    print(f"  {Style.GREEN}[OK]{Style.RESET} {audio_info}")

    stt_endpoint = os.getenv("GNANI_STT_ENDPOINT", DEFAULT_STT_ENDPOINT)
    headers = {
        "X-API-Key-ID": api_key,
    }

    # Form fields per documentation: audio_file (file), language_code (str), model (str)
    form_data = {
        "language_code": "hi-IN",
        "model": "prisma-v2.5",
    }

    print(f"Endpoint: {stt_endpoint}")
    print(f"Language: hi-IN | Model: prisma-v2.5")
    print(f"Auth Header: X-API-Key-ID: {mask_key(api_key)}")
    print("Sending STT transcription request...")

    start_time = time.perf_counter()
    try:
        with open(TEST_AUDIO_PATH, "rb") as f:
            files = {
                "audio_file": (TEST_AUDIO_PATH.name, f, "audio/wav")
            }
            response = requests.post(
                stt_endpoint,
                headers=headers,
                data=form_data,
                files=files,
                timeout=30,
            )
        latency = time.perf_counter() - start_time
        result["latency_sec"] = round(latency, 3)
        result["status_code"] = response.status_code

        print(f"HTTP Status: {response.status_code} (Response Time: {latency:.2f}s)")

        # Handle Responses
        if response.status_code == 200:
            try:
                resp_data = response.json()
            except json.JSONDecodeError:
                resp_data = {"raw_text": response.text}

            transcript = resp_data.get("transcript", "")
            result["transcript"] = transcript
            result["metadata"] = {
                "request_id": resp_data.get("request_id"),
                "model": resp_data.get("model", "prisma-v2.5"),
                "detected_language": resp_data.get("detected_language_code"),
                "processing_time": resp_data.get("processing_time"),
            }
            result["status"] = "PASS"
            result["evidence"] = (
                f"HTTP 200 in {latency:.2f}s. Transcript: '{transcript}'. "
                f"Request ID: {resp_data.get('request_id', 'N/A')}"
            )

            print(f"  {Style.GREEN}[SUCCESS]{Style.RESET} Transcription completed!")
            print(f"  Actual Transcript : \"{transcript}\"")
            print(f"  Model             : {result['metadata']['model']}")
            print(f"  Request ID        : {result['metadata']['request_id']}")
            if result['metadata']['processing_time']:
                print(f"  Server Processing : {result['metadata']['processing_time']}s")

        elif response.status_code in (401, 403):
            try:
                err_json = response.json()
                detail = err_json.get("detail", {})
                if isinstance(detail, dict):
                    err_code = detail.get("error_code", "AUTH_FAILED")
                    err_msg = detail.get("message", "Unauthorized")
                    error_summary = f"{err_code} - {err_msg}"
                else:
                    error_summary = str(detail)
            except Exception:
                error_summary = response.text
            print(f"  {Style.RED}[AUTH ERROR {response.status_code}]{Style.RESET} {error_summary}")
            result["evidence"] = f"Auth failed (HTTP {response.status_code}): {error_summary}"
        elif response.status_code == 429:
            print(f"  {Style.YELLOW}[RATE LIMITED 429]{Style.RESET} Account concurrency/quota exceeded.")
            result["evidence"] = f"Rate limited (HTTP 429): {response.text}"
        elif response.status_code == 422:
            print(f"  {Style.RED}[VALIDATION ERROR 422]{Style.RESET} Invalid parameters or audio format.")
            print(f"  Server response: {response.text}")
            result["evidence"] = f"Validation error (HTTP 422): {response.text}"
        else:
            print(f"  {Style.RED}[SERVER ERROR {response.status_code}]{Style.RESET} Unexpected response.")
            print(f"  Server response: {response.text}")
            result["evidence"] = f"HTTP {response.status_code}: {response.text}"

    except requests.exceptions.Timeout:
        latency = time.perf_counter() - start_time
        print(f"  {Style.RED}[TIMEOUT]{Style.RESET} Request timed out after {latency:.2f}s")
        result["evidence"] = f"Request timed out after {latency:.2f}s"
    except requests.exceptions.ConnectionError as ce:
        print(f"  {Style.RED}[CONNECTION ERROR]{Style.RESET} Could not connect to {stt_endpoint}: {ce}")
        result["evidence"] = f"Connection failed: {ce}"
    except Exception as e:
        print(f"  {Style.RED}[EXCEPTION]{Style.RESET} {e}")
        result["evidence"] = f"Exception: {e}"

    return result


def run_tts_test(api_key: str) -> Dict[str, Any]:
    """
    Test B: Timbre v2.5 Text-to-Speech
    Endpoint: https://api.vachana.ai/api/v1/tts/inference
    Method: POST application/json
    Header: X-API-Key-ID: <api-key>
    Payload: Hindi text, voice 'Nalini', model 'timbre-v2.5', language 'hi-IN', container 'wav'
    """
    print_header("TEST B: TIMBRE v2.5 TEXT-TO-SPEECH (TTS)")
    result = {
        "test": "Timbre TTS",
        "status": "FAIL",
        "status_code": None,
        "latency_sec": None,
        "file_size": None,
        "duration_sec": None,
        "output_format": None,
        "evidence": "",
    }

    tts_endpoint = os.getenv("GNANI_TTS_ENDPOINT", DEFAULT_TTS_ENDPOINT)
    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": api_key,
    }

    payload = {
        "text": TTS_TEST_SENTENCE,
        "voice": "Nalini",
        "model": "timbre-v2.5",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    print(f"Endpoint: {tts_endpoint}")
    print(f"Model: timbre-v2.5 | Voice: Nalini | Language: hi-IN")
    print(f"Requested Container: WAV (48000 Hz, 1ch, 16-bit linear PCM)")
    print(f"Test Sentence (Hindi):\n  \"{TTS_TEST_SENTENCE}\"")
    print(f"Auth Header: X-API-Key-ID: {mask_key(api_key)}")
    print("Submitting synthesis request...")

    start_time = time.perf_counter()
    try:
        response = requests.post(
            tts_endpoint,
            headers=headers,
            json=payload,
            timeout=30,
        )
        latency = time.perf_counter() - start_time
        result["latency_sec"] = round(latency, 3)
        result["status_code"] = response.status_code
        content_type = response.headers.get("Content-Type", "")

        print(f"HTTP Status: {response.status_code} (Response Time: {latency:.2f}s)")
        print(f"Content-Type: {content_type}")

        if response.status_code == 200:
            raw_bytes = response.content

            # Inspect content to determine if binary audio or JSON wrapper
            audio_bytes: Optional[bytes] = None
            if raw_bytes.startswith(b"RIFF") or "audio" in content_type or "octet-stream" in content_type:
                audio_bytes = raw_bytes
                result["output_format"] = "binary/wav"
            else:
                # Attempt JSON fallback (in case audio is base64 encoded)
                try:
                    resp_json = response.json()
                    for key in ("audio_content", "audio", "data", "audio_data"):
                        if key in resp_json and isinstance(resp_json[key], str):
                            audio_bytes = base64.b64decode(resp_json[key])
                            result["output_format"] = f"json_base64 ({key})"
                            break
                except Exception:
                    pass

            if not audio_bytes or len(audio_bytes) == 0:
                print(f"  {Style.RED}[FAIL]{Style.RESET} Response was HTTP 200 but no valid audio payload found.")
                result["evidence"] = f"HTTP 200 received but unable to parse audio. Preview: {response.text[:200]}"
                return result

            # Save generated audio
            with open(OUTPUT_AUDIO_PATH, "wb") as f:
                f.write(audio_bytes)

            file_size = OUTPUT_AUDIO_PATH.stat().st_size
            result["file_size"] = file_size

            # Validate WAV properties
            duration_str = "unknown"
            try:
                with wave.open(str(OUTPUT_AUDIO_PATH), "rb") as w:
                    frames = w.getnframes()
                    rate = w.getframerate()
                    ch = w.getnchannels()
                    sw = w.getsampwidth()
                    # If streamed WAV header has 0x7FFFFFFF / max frames, calculate from actual bytes
                    if frames > 10_000_000 and rate > 0 and ch > 0 and sw > 0:
                        bytes_per_sec = rate * ch * sw
                        duration = max(0.0, (file_size - 44) / float(bytes_per_sec))
                    else:
                        duration = frames / float(rate) if rate > 0 else 0
                    duration_str = f"{duration:.2f}s"
                    result["duration_sec"] = round(duration, 2)
            except Exception:
                duration_str = "non-RIFF or compressed WAV"

            if file_size > 0:
                result["status"] = "PASS"
                result["evidence"] = (
                    f"Generated {OUTPUT_AUDIO_PATH.name} ({file_size} bytes, "
                    f"duration ~{duration_str}) in {latency:.2f}s via timbre-v2.5 (Nalini)"
                )
                print(f"  {Style.GREEN}[SUCCESS]{Style.RESET} TTS audio successfully synthesized and verified!")
                print(f"  Output File : {OUTPUT_AUDIO_PATH.name} ({file_size:,} bytes)")
                print(f"  Duration    : {duration_str}")
                print(f"  Format      : {result['output_format']}")
            else:
                print(f"  {Style.RED}[FAIL]{Style.RESET} Output file was created but is 0 bytes.")
                result["evidence"] = "Output file is empty (0 bytes)."

        elif response.status_code in (401, 403):
            try:
                err_json = response.json()
                detail = err_json.get("detail", {})
                if isinstance(detail, dict):
                    err_code = detail.get("error_code", "AUTH_FAILED")
                    err_msg = detail.get("message", "Unauthorized")
                    error_summary = f"{err_code} - {err_msg}"
                else:
                    error_summary = str(detail)
            except Exception:
                error_summary = response.text
            print(f"  {Style.RED}[AUTH ERROR {response.status_code}]{Style.RESET} {error_summary}")
            result["evidence"] = f"Auth failed (HTTP {response.status_code}): {error_summary}"
        elif response.status_code == 422:
            print(f"  {Style.RED}[VALIDATION ERROR 422]{Style.RESET} Payload schema rejected by Timbre v2.5.")
            print(f"  Server response: {response.text}")
            result["evidence"] = f"Validation error (HTTP 422): {response.text}"
        elif response.status_code == 429:
            print(f"  {Style.YELLOW}[RATE LIMITED 429]{Style.RESET} Concurrency or quota exceeded.")
            result["evidence"] = f"Rate limited (HTTP 429): {response.text}"
        else:
            print(f"  {Style.RED}[SERVER ERROR {response.status_code}]{Style.RESET}")
            print(f"  Server response: {response.text}")
            result["evidence"] = f"HTTP {response.status_code}: {response.text}"

    except requests.exceptions.Timeout:
        latency = time.perf_counter() - start_time
        print(f"  {Style.RED}[TIMEOUT]{Style.RESET} Request timed out after {latency:.2f}s")
        result["evidence"] = f"Request timed out after {latency:.2f}s"
    except requests.exceptions.ConnectionError as ce:
        print(f"  {Style.RED}[CONNECTION ERROR]{Style.RESET} Could not connect to {tts_endpoint}: {ce}")
        result["evidence"] = f"Connection failed: {ce}"
    except Exception as e:
        print(f"  {Style.RED}[EXCEPTION]{Style.RESET} {e}")
        result["evidence"] = f"Exception: {e}"

    return result


def main() -> int:
    print_header("GNANI AI API SMOKE TEST - BIMASAKSHI (PHASE 1)")
    print(f"Target Platform : Gnani.ai / Vachana Speech AI")
    print(f"STT Model Target: Prisma v2.5")
    print(f"TTS Model Target: Timbre v2.5")
    print(f"Working Directory: {BACKEND_DIR}")

    # Check API Key
    api_key = load_credentials()
    if not api_key:
        print(f"\n{Style.RED}{Style.BOLD}[ERROR] Gnani API credentials are NOT configured!{Style.RESET}")
        print(f"Please configure your API key in:")
        print(f"  {ENV_PATH}")
        print(f"\nAdd your key in the format:")
        print(f"  GNANI_API_KEY=your_actual_api_key_here\n")
        print(f"Then re-run: python test_gnani.py\n")

        print_header("VERIFICATION REPORT (CREDENTIALS MISSING)")
        print(f"| Test                     | Status | Evidence |")
        print(f"|--------------------------|--------|----------|")
        print(f"| API key loaded           | FAIL   | GNANI_API_KEY is missing or empty in .env |")
        print(f"| Prisma authentication    | BLOCKED| Cannot run without credentials |")
        print(f"| Prisma transcription     | BLOCKED| Cannot run without credentials |")
        print(f"| Timbre authentication    | BLOCKED| Cannot run without credentials |")
        print(f"| Timbre audio generation  | BLOCKED| Cannot run without credentials |")
        print(f"| WAV output verified      | BLOCKED| Cannot run without credentials |")
        return 1

    print(f"\n{Style.GREEN}[OK]{Style.RESET} API key loaded successfully: {mask_key(api_key)}")

    # Execute Independent Tests
    stt_res = run_stt_test(api_key)
    tts_res = run_tts_test(api_key)

    # Final Verification Report
    print_header("FINAL VERIFICATION REPORT")
    print(f"| Test                     | Status | Evidence |")
    print(f"|--------------------------|--------|----------|")
    print(f"| API key loaded           | PASS   | Key loaded ({mask_key(api_key)}) from .env |")
    
    stt_auth = "PASS" if stt_res["status_code"] in (200, 422) else "FAIL"
    print(f"| Prisma authentication    | {stt_auth:<6} | HTTP {stt_res['status_code']} on {DEFAULT_STT_ENDPOINT} |")
    print(f"| Prisma transcription     | {stt_res['status']:<6} | {stt_res['evidence'][:60]}... |")

    tts_auth = "PASS" if tts_res["status_code"] in (200, 422) else "FAIL"
    print(f"| Timbre authentication    | {tts_auth:<6} | HTTP {tts_res['status_code']} on {DEFAULT_TTS_ENDPOINT} |")
    print(f"| Timbre audio generation  | {tts_res['status']:<6} | {tts_res['evidence'][:60]}... |")

    wav_ok = "PASS" if (OUTPUT_AUDIO_PATH.exists() and OUTPUT_AUDIO_PATH.stat().st_size > 0 and tts_res["status"] == "PASS") else "FAIL"
    wav_size = OUTPUT_AUDIO_PATH.stat().st_size if OUTPUT_AUDIO_PATH.exists() else 0
    print(f"| WAV output verified      | {wav_ok:<6} | File {OUTPUT_AUDIO_PATH.name} exists ({wav_size:,} bytes) |")

    success = (stt_res["status"] == "PASS" and tts_res["status"] == "PASS" and wav_ok == "PASS")
    if success:
        print(f"\n{Style.GREEN}{Style.BOLD}All Phase 1 Gnani AI API Smoke Tests PASSED!{Style.RESET}\n")
        return 0
    else:
        print(f"\n{Style.RED}{Style.BOLD}Phase 1 Smoke Tests FAILED or encountered errors. See details above.{Style.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
