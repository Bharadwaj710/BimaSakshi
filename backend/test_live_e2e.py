import base64
import json
import sys
import time
from pathlib import Path
import requests

from services.response_service import synthesize_speech

transcript_text = (
    "मेरे एज 52 इयर्स है और मेरे पास स्टार हेल्थ प्रीमियर की 10,00,000 की पॉलिसी है जो 14 मंथ पुराना है "
    "मुझे किडनी स्टोन सर्जरी करवाना है रूम रेंट 30,000 पर डे और हॉस्पिटल डिफरेंट रूम कैटेगरीज़ के हिसाब से "
    "बिल करता है क्या प्रोपोर्शनेट डिडक्शन 24 मंथ वेटिंग पीरियड अप्लाई होगा?"
)

print("1. Synthesizing audio for transcript with Gnani Timbre...")
tts_res = synthesize_speech(transcript_text)
if tts_res.status != "success":
    print("TTS synthesis failed:", tts_res.error)
    sys.exit(1)

wav_bytes = base64.b64decode(tts_res.audio_base64)
audio_path = Path("d:/bimasakshi/frontend/public/calculi_scenario.wav")
audio_path.write_bytes(wav_bytes)
print(f"WAV generated: {len(wav_bytes)} bytes saved to {audio_path}")

print("\n2. Calling live POST http://127.0.0.1:8000/api/analyze-audio...")
t0 = time.perf_counter()
resp = requests.post(
    "http://127.0.0.1:8000/api/analyze-audio",
    files={"audio": ("calculi_scenario.wav", wav_bytes, "audio/wav")},
    timeout=60,
)
total_latency = time.perf_counter() - t0

print(f"Response Status: {resp.status_code} in {total_latency:.2f}s")
data = resp.json()
print("\n--- TRANSCRIPT ---")
transcription_obj = data.get("transcription", {})
print("Text:", transcription_obj.get("text"))
print("Model:", transcription_obj.get("model"))
print("Latency (s):", transcription_obj.get("latency_sec"))

print("\n--- EXTRACTED INFO ---")
extracted = data.get("extracted_information", {})
print("Age:", extracted.get("age"))
print("Sum Insured:", extracted.get("sum_insured"))
print("Tenure (months):", extracted.get("policy_tenure_months"))
print("Room Rent:", extracted.get("selected_room_rent_per_day"))
print("Differential Billing:", extracted.get("hospital_differential_billing"))
print("Diagnosis:", extracted.get("diagnosis_or_condition"))
print("Identified Intents:", extracted.get("identified_intents"))
print("Retrieval Queries:", extracted.get("retrieval_queries"))
print("Units & Amounts:", extracted.get("units_and_amounts"))

print("\n--- RETRIEVED CLAUSES ---")
for c in data.get("retrieved_clauses", []):
    cid = c.get("clause_id")
    page = c.get("source_page")
    dist = c.get("distance", 0.0)
    print(f"Clause: {cid} | Page: {page} | Distance: {dist:.4f}")

print("\n--- FINDINGS ---")
analysis_obj = data.get("analysis", {})
for f in analysis_obj.get("findings", []):
    print("-", f)

print("\n--- WARNINGS ---")
for w in analysis_obj.get("warnings", []):
    print("-", w)

print("\n--- CALCULATIONS ---")
for calc in analysis_obj.get("calculations", []):
    ctype = calc.get("type")
    cres = calc.get("result")
    cill = calc.get("illustrative_only")
    cexp = calc.get("explanation")
    print(f"- {ctype}: {cres} (Illustrative: {cill}) -> {cexp}")

print("\n--- HINDI ADVISORY SPOKEN ---")
tts_obj = data.get("tts", {})
print(tts_obj.get("spoken_text"))
has_audio = len(tts_obj.get("audio_base64", "")) > 0
print(f"Audio Base64 Generated: {has_audio} (Length: {len(tts_obj.get('audio_base64', ''))} chars)")
