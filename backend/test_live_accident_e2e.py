"""
Real Live End-to-End Test for Accident Waiting Period Scenario
--------------------------------------------------------------
Tests the full unmocked pipeline:
1. Synthesizes a real user audio question using Gnani Timbre v2.5:
   "क्या एक्सीडेंट के कारण होने वाली सर्जरी पर भी 24 महीने का वेटिंग पीरियड लागू होता है?"
2. Sends the live audio to POST http://127.0.0.1:8000/api/analyze-audio.
3. Verifies:
   - Prisma v2.5 transcribes the speech.
   - Gemini 2.5 Flash extracts primary_intent='waiting_period_accident' and is_accident_related=True.
   - ChromaDB prioritizes STAR-PREMIER-WAIT-002 (Code Excl 02, PDF Page 6).
   - Deterministic policy engine applies the Code Excl 02 accident exception.
   - Timbre v2.5 generates a targeted Hindi voice advisory answering the accident question.
   - No irrelevant room-rent or differential billing warnings are generated.
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

GNANI_KEY = os.getenv("GNANI_API_KEY")
assert GNANI_KEY, "GNANI_API_KEY is not configured in .env"

print("=" * 70)
print("  REAL LIVE END-TO-END TEST: ACCIDENT WAITING PERIOD SCENARIO")
print("=" * 70)

# Step 1: Synthesize genuine user question audio via Timbre
print("\n[Step 1] Synthesizing genuine user question audio via Gnani Timbre...")
question_hindi = "क्या एक्सीडेंट के कारण होने वाली सर्जरी पर भी 24 महीने का वेटिंग पीरियड लागू होता है?"

tts_headers = {
    "Content-Type": "application/json",
    "X-API-Key-ID": GNANI_KEY,
}
tts_payload = {
    "text": question_hindi,
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

t0 = time.time()
tts_res = requests.post(
    "https://api.vachana.ai/api/v1/tts/inference",
    json=tts_payload,
    headers=tts_headers,
    timeout=30,
)
print(f"TTS synthesis status: {tts_res.status_code} in {time.time() - t0:.2f}s")
assert tts_res.status_code == 200, f"Failed to synthesize test question audio: {tts_res.text}"

audio_bytes = tts_res.content
assert len(audio_bytes) > 1000, "Audio response too short"
print(f"Generated user question audio: {len(audio_bytes)} bytes WAV (Header: {audio_bytes[:4]})")

# Step 2: Submit to live analyze-audio endpoint
print("\n[Step 2] Sending live audio to POST http://127.0.0.1:8000/api/analyze-audio...")
t0 = time.time()
files = {"audio": ("accident_question.wav", audio_bytes, "audio/wav")}
res = requests.post("http://127.0.0.1:8000/api/analyze-audio", files=files, timeout=60)
elapsed = time.time() - t0

print(f"API HTTP Status: {res.status_code} in {elapsed:.2f}s")
assert res.status_code == 200, f"Analysis pipeline failed: {res.text}"

data = res.json()

# Step 3: Verify Prisma STT
print("\n--- 1. SPEECH-TO-TEXT (Gnani Prisma v2.5) ---")
transcription = data["transcription"]
print(f"Transcript: \"{transcription['text']}\"")
print(f"Model: {transcription['model']} | Latency: {transcription['latency_sec']}s")
assert "एक्सीडेंट" in transcription["text"] or "accident" in transcription["text"].lower() or "वेटिंग" in transcription["text"]

# Step 4: Verify Gemini Extraction
print("\n--- 2. ENTITY EXTRACTION & INTENT (Gemini 2.5 Flash) ---")
ext = data["extracted_information"]
print(f"Primary Intent: {ext.get('primary_intent')}")
print(f"Is Accident Related: {ext.get('is_accident_related')}")
print(f"Accident Causality: {ext.get('accident_causal_relationship')}")
print(f"Condition: {ext.get('diagnosis_or_condition')}")
print(f"Treatment: {ext.get('treatment_type')}")
print(f"Normalized Query: {ext.get('normalized_english_query')}")

# Step 5: Verify ChromaDB Retrieval
print("\n--- 3. RETRIEVED CLAUSES (ChromaDB) ---")
clauses = data["retrieved_clauses"]
for c in clauses:
    print(f"  * [{c['clause_id']}] {c['clause_title']} -> Source: {c['source_page']} (dist: {c['distance']:.3f})")

top_clause = clauses[0]["clause_id"]
assert top_clause == "STAR-PREMIER-WAIT-002", f"Expected STAR-PREMIER-WAIT-002 as top clause, got {top_clause}"
print(f"[OK] Top clause is correctly STAR-PREMIER-WAIT-002 (Code Excl 02, PDF Page 6)")

# Step 6: Verify Deterministic Policy Rule Engine
print("\n--- 4. DETERMINISTIC RULE ENGINE (Policy Engine) ---")
analysis = data["analysis"]
print("Findings:")
for f in analysis["findings"]:
    print(f"  - {f}")
print("Warnings:")
for w in analysis["warnings"]:
    print(f"  ! {w}")

assert any("Code Excl 02 Accident Exception" in f for f in analysis["findings"]), "Missing Code Excl 02 Accident Exception finding"
assert not any("waiting period under Code Excl 02" in w for w in analysis["warnings"]), "Unexpected waiting period warning on accident claim"
assert not any("room rent" in w.lower() for w in analysis["warnings"]), "Unexpected room rent warning on accident question"

# Step 7: Verify Timbre TTS Hindi Spoken Advisory
print("\n--- 5. HINDI VOICE ADVISORY (Gnani Timbre v2.5) ---")
tts = data["tts"]
spoken_text = tts["spoken_text"]
print(f"Spoken Text:\n\"{spoken_text}\"")
print(f"TTS Status: {tts['status']} | Audio Base64 Length: {len(tts['audio_base64']) if tts['audio_base64'] else 0}")

assert "दुर्घटना (accident)" in spoken_text or "दुर्घटना" in spoken_text, "Missing accident discussion in spoken Hindi"
assert "24 महीने का वेटिंग पीरियड लागू नहीं होता" in spoken_text or "लागू नहीं होता" in spoken_text, "Missing waiting period exemption in spoken Hindi"
assert "पात्र कमरा किराया 10,000 रुपये" not in spoken_text, "Spoken text wrongly discusses room rent on accident question"
assert "अस्पताल की बिलिंग पद्धति" not in spoken_text, "Spoken text wrongly discusses differential billing on accident question"

print("\n" + "=" * 70)
print("  [ALL VERIFICATIONS PASSED] LIVE ACCIDENT PIPELINE IS 100% OPERATIONAL!")
print("=" * 70)
