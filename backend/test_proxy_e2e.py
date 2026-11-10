import requests
import json
import time

print("=" * 60)
print("TESTING BIMASAKSHI FRONTEND-TO-BACKEND PIPELINE VIA VITE PROXY")
print("=" * 60)

# Step 1: Check proxy health
health_res = requests.get("http://localhost:5173/health")
print(f"Health check status: {health_res.status_code}")
assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
print(f"Health response: {health_res.json()}")

# Step 2: Check policy status
policy_res = requests.get("http://localhost:5173/api/policy/status")
print(f"Policy status: {policy_res.status_code}")
assert policy_res.status_code == 200, f"Policy status failed: {policy_res.text}"
print(f"Policy metadata: {policy_res.json()}")

# Step 3: Analyze audio through proxy
print("\nUploading sample_scenario.wav to POST http://localhost:5173/api/analyze-audio...")
t0 = time.time()
with open("d:/bimasakshi/frontend/public/sample_scenario.wav", "rb") as f:
    files = {"audio": ("sample_scenario.wav", f, "audio/wav")}
    analyze_res = requests.post("http://localhost:5173/api/analyze-audio", files=files, timeout=60)
elapsed = time.time() - t0

print(f"Analysis HTTP status: {analyze_res.status_code} (in {elapsed:.2f}s)")
assert analyze_res.status_code == 200, f"Analysis failed: {analyze_res.text}"

data = analyze_res.json()
print("\n--- TRANSCRIPTION (Prisma v2.5) ---")
print("Text:", data["transcription"]["text"])
print("Latency:", data["transcription"]["latency_sec"], "sec")

print("\n--- EXTRACTION (Gemini 2.5 Flash) ---")
ext = data["extracted_information"]
print("Age:", ext["age"])
print("Condition:", ext["diagnosis_or_condition"])
print("Treatment:", ext["treatment_type"])
print("Room Rent:", ext["selected_room_rent_per_day"])
print("Sum Insured:", ext["sum_insured"])
print("Tenure (months):", ext["policy_tenure_months"])
print("Differential Billing:", ext["hospital_differential_billing"])
print("Missing:", ext["missing_information"])
print("Normalized Query:", ext["normalized_english_query"])

print("\n--- RETRIEVED CLAUSES (ChromaDB) ---")
for c in data["retrieved_clauses"]:
    print(f"  [{c['clause_id']}] {c['clause_title']} -> {c['source_page']} (dist: {c['distance']:.3f})")

print("\n--- CALCULATIONS (Rule Engine) ---")
for calc in data["analysis"]["calculations"]:
    print(f"  [{calc['type']}] Result: {calc['result']} (illustrative_only: {calc['illustrative_only']})")
    print(f"    Formula: {calc['formula']}")
    print(f"    Explanation: {calc['explanation'][:100]}...")

print("\n--- TTS ADVISORY (Timbre v2.5) ---")
tts = data["tts"]
print("Status:", tts["status"])
print("Model:", tts["model"])
print("Spoken text:", tts["spoken_text"])
print("Audio base64 length:", len(tts["audio_base64"]) if tts["audio_base64"] else 0)

print("\n[SUCCESS] Entire frontend proxy + backend pipeline passed all checks!")

