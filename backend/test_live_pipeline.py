"""
Live End-to-End Pipeline Verification Script (Phase 3)
------------------------------------------------------
Executes a 100% live test using:
1. Real synthesized Hindi spoken audio (Kidney calculi scenario)
2. Live Gnani Prisma v2.5 Speech-to-Text
3. Live Google Gemini 2.5 Flash entity extraction & English query normalization
4. Live ChromaDB EphemeralClient policy retrieval
5. Live Python deterministic insurance rule engine
6. Live Gnani Timbre v2.5 Text-to-Speech synthesis
7. Validates full HTTP 200 JSON response
"""

import base64
import json
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import requests
from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from services.response_service import synthesize_speech
from main import app
from fastapi.testclient import TestClient

SAMPLE_SPEECH_HINDI = (
    "मेरी उम्र बावन वर्ष है। मुझे किडनी की पथरी की सर्जरी करानी है। "
    "अस्पताल में कमरे का किराया पंद्रह हजार रुपये प्रतिदिन है। "
    "मेरी स्टार हेल्थ पॉलिसी चौदह महीने पुरानी है।"
)

AUDIO_SAMPLE_PATH = BACKEND_DIR / "data" / "live_input_calculi.wav"


def generate_live_hindi_sample() -> bytes:
    """Uses live Timbre to generate a genuine spoken Hindi WAV recording for testing."""
    print(f"\n[1/4] Generating authentic spoken Hindi test audio with Timbre v2.5...")
    print(f"Spoken Text: \"{SAMPLE_SPEECH_HINDI}\"")
    tts_res = synthesize_speech(SAMPLE_SPEECH_HINDI)
    if tts_res.status != "success" or not tts_res.audio_base64:
        raise RuntimeError(f"Failed to generate test audio: {tts_res.error}")

    audio_bytes = base64.b64decode(tts_res.audio_base64)
    with open(AUDIO_SAMPLE_PATH, "wb") as f:
        f.write(audio_bytes)
    print(f"  -> Generated {len(audio_bytes):,} bytes at {AUDIO_SAMPLE_PATH.name}")
    return audio_bytes


def run_live_pipeline_test():
    print("=" * 70)
    print("  BIMASAKSHI PHASE 3: LIVE END-TO-END PIPELINE VERIFICATION")
    print("=" * 70)

    # Step 1: Generate or load real spoken Hindi audio
    if not AUDIO_SAMPLE_PATH.exists():
        audio_bytes = generate_live_hindi_sample()
    else:
        print(f"[1/4] Using existing spoken Hindi audio: {AUDIO_SAMPLE_PATH.name}")
        audio_bytes = AUDIO_SAMPLE_PATH.read_bytes()

    # Step 2: Submit to FastAPI /api/analyze-audio via TestClient
    print("\n[2/4] Submitting audio to POST /api/analyze-audio...")
    start_time = time.perf_counter()

    with TestClient(app) as client:
        files = {
            "audio": (AUDIO_SAMPLE_PATH.name, audio_bytes, "audio/wav")
        }
        response = client.post("/api/analyze-audio", files=files)

    total_time = round(time.perf_counter() - start_time, 2)
    print(f"  -> API Response Code: {response.status_code} in {total_time}s")

    if response.status_code != 200:
        print(f"[FAIL] HTTP {response.status_code}: {response.text}")
        return False

    data = response.json()

    # Step 3: Print Detailed Evidence
    print("\n[3/4] Live Pipeline Output Verification:")
    print("-" * 70)
    
    print("\nA. PRISMA v2.5 TRANSCRIPTION:")
    print(f"  Transcript  : \"{data['transcription']['text']}\"")
    print(f"  Model       : {data['transcription']['model']}")
    print(f"  Request ID  : {data['transcription']['request_id']}")
    print(f"  Latency     : {data['transcription']['latency_sec']}s")

    print("\nB. GEMINI ENTITY EXTRACTION:")
    extracted = data["extracted_information"]
    print(f"  Age                  : {extracted.get('age')}")
    print(f"  Diagnosis/Condition  : {extracted.get('diagnosis_or_condition')}")
    print(f"  Selected Room Rent   : ₹{extracted.get('selected_room_rent_per_day') or 0:,.2f}/day")
    print(f"  Policy Tenure        : {extracted.get('policy_tenure_months')} months")
    print(f"  Normalized Query     : \"{extracted.get('normalized_english_query')}\"")
    print(f"  Missing Details      : {extracted.get('missing_information')}")

    print("\nC. CHROMADB RETRIEVED CLAUSES:")
    for i, c in enumerate(data["retrieved_clauses"], 1):
        print(f"  [{i}] {c['clause_id']} (Page {c['source_page']}): {c['clause_title']} (dist: {c['distance']})")

    print("\nD. DETERMINISTIC RULE-ENGINE AUDIT:")
    print("  Calculations:")
    for calc in data["analysis"]["calculations"]:
        print(f"    - {calc['type']}: {calc['explanation']}")
    print("  Warnings:")
    for warn in data["analysis"]["warnings"]:
        print(f"    - [WARNING] {warn}")
    print("  Findings:")
    for f in data["analysis"]["findings"]:
        print(f"    - {f}")
    print("  Assumptions:")
    for a in data["analysis"]["assumptions"]:
        print(f"    - {a}")
    print("  Relevant Clauses :", data["analysis"]["relevant_clause_ids"])

    print("\nE. TIMBRE v2.5 HINDI VOICE ADVISORY:")
    tts = data["tts"]
    print(f"  Status        : {tts['status']}")
    print(f"  Voice Model   : {tts['model']} (Nalini)")
    print(f"  Spoken Hindi  : \"{tts.get('spoken_text')}\"")
    b64_len = len(tts.get("audio_base64") or "")
    print(f"  WAV Base64    : {b64_len:,} chars (MIME: {tts.get('mime_type')})")

    # Step 4: Save returned advisory WAV for inspection
    if tts.get("audio_base64"):
        out_wav_path = BACKEND_DIR / "output_live_advisory.wav"
        with open(out_wav_path, "wb") as f:
            f.write(base64.b64decode(tts["audio_base64"]))
        print(f"  -> Saved synthesized advisory to: {out_wav_path.name} ({out_wav_path.stat().st_size:,} bytes)")

    print("\n" + "=" * 70)
    print("  LIVE END-TO-END PIPELINE VERIFICATION PASSED SUCCESSFULLY!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = run_live_pipeline_test()
    sys.exit(0 if success else 1)

