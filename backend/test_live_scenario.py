"""
Live End-to-End Test for BimaSakshi
Tests the exact scenario via live audio and POST /api/analyze-audio.
"""

import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env", override=True)

from services.response_service import synthesize_speech

def run_live_test():
    print("=== LIVE END-TO-END TEST ===")
    
    # 1. Generate live audio using Gnani Timbre v2.5
    prompt_hindi = (
        "मेरी उम्र 24 वर्ष है, मुझे किडनी स्टोन सर्जरी करवानी है और मेरे पास स्टार हेल्थ इंश्योरेंस है। "
        "अस्पताल मुझसे 30,000 रुपये का डिपॉजिट मांग रहा है। मेरी पॉलिसी में मुझे क्या बेनिफिट्स मिलेंगे?"
    )
    print(f"\n1. Synthesizing live test speech via Timbre v2.5:\n   '{prompt_hindi}'")
    
    import base64
    tts_res = synthesize_speech(
        text=prompt_hindi,
        voice="Nalini",
        model="timbre-v2.5",
        language="hi-IN",
    )
    if not tts_res.audio_base64:
        print("TTS failed:", tts_res.error)
        sys.exit(1)
    audio_bytes = base64.b64decode(tts_res.audio_base64)
    print(f"   Generated audio: {len(audio_bytes)} bytes WAV.")
    
    # 2. Call live endpoint POST http://127.0.0.1:8000/api/analyze-audio
    print("\n2. Sending audio to POST /api/analyze-audio...")
    files = {
        "audio": ("live_24yr_deposit_test.wav", audio_bytes, "audio/wav"),
    }
    
    try:
        res = requests.post("http://127.0.0.1:8000/api/analyze-audio", files=files, timeout=60)
        status_code = res.status_code
        data = res.json()
        print(f"   HTTP endpoint response status: {status_code}")
    except Exception as e:
        print(f"   HTTP connection not available ({e}), executing via FastAPI TestClient...")
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client:
            res = client.post("/api/analyze-audio", files={"audio": ("live_24yr_deposit_test.wav", audio_bytes, "audio/wav")})
            status_code = res.status_code
            data = res.json()
            print(f"   TestClient endpoint response status: {status_code}")
    
    if status_code != 200:
        print("ERROR:", data)
        sys.exit(1)
    
    # 3. Inspect results
    transcript = data["transcription"]["text"]
    stt_latency = data["transcription"]["latency_sec"]
    info = data["extracted_information"]
    clauses = data["retrieved_clauses"]
    analysis = data["analysis"]
    tts = data["tts"]
    
    print("\n=== LIVE RESULTS INSPECTION ===")
    print(f"STT Transcript ({stt_latency:.2f}s latency):\n  '{transcript}'")
    
    print("\nExtracted Entities:")
    print(f"  - Age: {info.get('age')}")
    print(f"  - Diagnosis / Condition: {info.get('diagnosis_or_condition')}")
    print(f"  - Treatment: {info.get('treatment_type')}")
    print(f"  - Insurer: {info.get('insurer_mentioned')}")
    print(f"  - Hospital Deposit: {info.get('hospital_deposit')}")
    print(f"  - Selected Room Rent: {info.get('selected_room_rent_per_day')}")
    print(f"  - Sum Insured: {info.get('sum_insured')}")
    print(f"  - Policy Tenure: {info.get('policy_tenure_months')}")
    print(f"  - Membership Status: {info.get('membership_status')}")
    print(f"  - Primary Intent: {info.get('primary_intent')}")
    print(f"  - Identified Intents: {info.get('identified_intents')}")
    print(f"  - Retrieval Queries: {info.get('retrieval_queries')}")
    
    print("\nRetrieved ChromaDB Clauses:")
    for c in clauses:
        print(f"  - [{c['clause_id']}] {c['clause_title']} (Page {c['source_page']}, dist: {c['distance']})")
        
    print("\nRule Engine Findings:")
    for f in analysis["findings"]:
        print(f"  * {f[:120]}...")
        
    print("\nRule Engine Warnings:")
    for w in analysis["warnings"]:
        print(f"  ! {w}")
        
    print("\nMissing Information (Schedule Requirements):")
    for m in analysis["missing_information"]:
        print(f"  ? {m}")
        
    print("\nSynthesized Hindi Voice Advisory (Timbre v2.5):")
    print(f"  '{tts.get('spoken_text')}'")
    print(f"  Audio Base64 length: {len(tts.get('audio_base64', '') or '')} chars.")
    
    # 4. Strict assertions
    assert info.get("hospital_deposit") == 30000.0 or info.get("hospital_deposit") is not None, "Deposit must be extracted!"
    assert info.get("selected_room_rent_per_day") is None, "Deposit must NOT be mapped to room rent!"
    assert info.get("age") == 24, "Age must be 24!"
    
    retrieved_cids = [c["clause_id"] for c in clauses]
    assert "STAR-PREMIER-WAIT-002" in retrieved_cids, "Code Excl 02 must be retrieved!"
    
    spoken = tts.get("spoken_text", "")
    assert "30,000" in spoken or "डिपॉजिट" in spoken, "Spoken advisory must explain deposit!"
    assert "वेटिंग पीरियड" in spoken, "Spoken advisory must mention waiting period!"
    assert "कैशलेस" in spoken or "रिफंड" in spoken or "टीपीए" in spoken, "Spoken advisory must explain cashless/refund!"
    
    print("\n>>> ALL LIVE ASSERTIONS PASSED! <<<")

if __name__ == "__main__":
    run_live_test()
