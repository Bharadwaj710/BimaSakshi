"""
Live Unmocked End-to-End Integration Tests for Issues 1 & 4
1. Live Robotic Surgery End-to-End Test (Coverage 14)
2. Live Ambiguous Kidney Diagnosis End-to-End Test (Insufficient Information)
"""

import base64
import json
import sys
import time
from pathlib import Path
import requests

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.response_service import synthesize_speech

API_URL = "http://127.0.0.1:8000/api/analyze-audio"

print("======================================================================")
print("  LIVE TEST 1: ROBOTIC SURGERY (COVERAGE 14 - MODERN TREATMENT)")
print("======================================================================")
robotic_prompt = (
    "मेरे पास स्टार हेल्थ प्रीमियर की 10 लाख की पॉलिसी है, "
    "मुझे रोबोटिक सर्जरी करवानी है, इसमें कितना कवरेज मिलेगा?"
)

print(f"Spoken text prompt: '{robotic_prompt}'")
print("Synthesizing audio using Gnani Timbre v2.5...")
tts_robotic = synthesize_speech(robotic_prompt)
if tts_robotic.status != "success":
    print("TTS synthesis failed:", tts_robotic.error)
    sys.exit(1)

wav_bytes_robotic = base64.b64decode(tts_robotic.audio_base64)
print(f"Audio synthesized ({len(wav_bytes_robotic)} bytes). Submitting to live API...")

t0 = time.perf_counter()
res_robotic = requests.post(
    API_URL,
    files={"audio": ("robotic_query.wav", wav_bytes_robotic, "audio/wav")},
    timeout=60,
)
latency_robotic = time.perf_counter() - t0
print(f"HTTP Status: {res_robotic.status_code} in {latency_robotic:.2f}s")
data_robotic = res_robotic.json()

print("\n--- TRANSCRIPTION ---")
print("Text:", data_robotic.get("transcription", {}).get("text"))

print("\n--- EXTRACTED INFORMATION ---")
ext_robotic = data_robotic.get("extracted_information", {})
print("Diagnosis/Treatment:", ext_robotic.get("diagnosis_or_condition"), "|", ext_robotic.get("treatment_type"))
print("Sum Insured:", ext_robotic.get("sum_insured"))
print("Primary Intent:", ext_robotic.get("primary_intent"))
print("Identified Intents:", ext_robotic.get("identified_intents"))
print("Retrieval Queries:", ext_robotic.get("retrieval_queries"))

print("\n--- RETRIEVED CLAUSES ---")
for c in data_robotic.get("retrieved_clauses", []):
    print(f"Clause: {c.get('clause_id')} | Page: {c.get('source_page')} | Dist: {c.get('distance'):.4f} | Title: {c.get('clause_title')}")

print("\n--- FINDINGS ---")
for f in data_robotic.get("analysis", {}).get("findings", []):
    print("-", f)

print("\n--- WARNINGS ---")
for w in data_robotic.get("analysis", {}).get("warnings", []):
    print("-", w)

print("\n--- CALCULATIONS ---")
for calc in data_robotic.get("analysis", {}).get("calculations", []):
    print(f"- {calc.get('type')}: {calc.get('result')} (Formula: {calc.get('formula')})")

print("\n--- SPOKEN HINDI ADVISORY ---")
spoken_robotic = data_robotic.get("tts", {}).get("spoken_text")
print(spoken_robotic)
print("TTS Audio Generated:", len(data_robotic.get("tts", {}).get("audio_base64", "")) > 0)


print("\n======================================================================")
print("  LIVE TEST 2: AMBIGUOUS KIDNEY PROBLEM (INSUFFICIENT INFORMATION)")
print("======================================================================")
kidney_prompt = "मुझे किडनी की प्रॉब्लम है और डॉक्टर ने ऑपरेशन सजेस्ट किया है।"

print(f"Spoken text prompt: '{kidney_prompt}'")
print("Synthesizing audio using Gnani Timbre v2.5...")
tts_kidney = synthesize_speech(kidney_prompt)
if tts_kidney.status != "success":
    print("TTS synthesis failed:", tts_kidney.error)
    sys.exit(1)

wav_bytes_kidney = base64.b64decode(tts_kidney.audio_base64)
print(f"Audio synthesized ({len(wav_bytes_kidney)} bytes). Submitting to live API...")

t0 = time.perf_counter()
res_kidney = requests.post(
    API_URL,
    files={"audio": ("ambiguous_kidney.wav", wav_bytes_kidney, "audio/wav")},
    timeout=60,
)
latency_kidney = time.perf_counter() - t0
print(f"HTTP Status: {res_kidney.status_code} in {latency_kidney:.2f}s")
data_kidney = res_kidney.json()

print("\n--- TRANSCRIPTION ---")
print("Text:", data_kidney.get("transcription", {}).get("text"))

print("\n--- EXTRACTED INFORMATION ---")
ext_kidney = data_kidney.get("extracted_information", {})
print("Diagnosis/Treatment:", ext_kidney.get("diagnosis_or_condition"), "|", ext_kidney.get("treatment_type"))
print("Primary Intent:", ext_kidney.get("primary_intent"))
print("Identified Intents:", ext_kidney.get("identified_intents"))
print("Retrieval Queries:", ext_kidney.get("retrieval_queries"))

print("\n--- RETRIEVED CLAUSES ---")
for c in data_kidney.get("retrieved_clauses", []):
    print(f"Clause: {c.get('clause_id')} | Page: {c.get('source_page')} | Dist: {c.get('distance'):.4f} | Title: {c.get('clause_title')}")

print("\n--- FINDINGS ---")
for f in data_kidney.get("analysis", {}).get("findings", []):
    print("-", f)

print("\n--- WARNINGS ---")
for w in data_kidney.get("analysis", {}).get("warnings", []):
    print("-", w)

print("\n--- MISSING INFORMATION ---")
for m in data_kidney.get("analysis", {}).get("missing_information", []):
    print("-", m)

print("\n--- SPOKEN HINDI ADVISORY ---")
spoken_kidney = data_kidney.get("tts", {}).get("spoken_text")
print(spoken_kidney)
print("TTS Audio Generated:", len(data_kidney.get("tts", {}).get("audio_base64", "")) > 0)

