# BimaSakshi — Phase 1.5 Targeted Remediation Report

**Date:** 2026-11-11  
**Author:** Senior Software Architect, AI Engineer & Independent QA Lead  
**Target Repository:** `https://github.com/Bharadwaj710/BimaSakshi.git`  
**Base Commit Hash:** `82214df`  
**Branch:** `main`

---

## 1. Executive Summary

Following the approval of the Phase 1 Engineering Audit ([`AUDIT_REPORT.md`](file:///d:/bimasakshi/AUDIT_REPORT.md)), targeted remediation was executed strictly against the 4 identified issues.

### Core Objectives Achieved:
1. **Removed all hardcoded drive paths:** Cleaned up Windows absolute paths from `backend/test_live_e2e.py` and `backend/test_proxy_e2e.py` using `pathlib.Path(__file__).resolve().parent.parent`.
2. **Configured scoped pytest discovery:** Added `backend/pytest.ini` configuring `testpaths = tests`, ensuring normal `pytest` executions never inadvertently invoke root live API scripts or consume API quotas.
3. **Implemented FFmpeg availability check & diagnostic:** Added `check_ffmpeg_availability()` in `backend/services/gnani_service.py` and verified startup reporting in `backend/main.py` with actionable diagnostic messages.
4. **Resolved checklist response contract:** Formally added `checklist: List[str] = Field(default_factory=list, ...)` to `AnalysisResult` in `backend/schemas/analysis.py`, dynamically generated in `policy_engine.py`, while preserving client fallback compatibility in `FindingsPanel.jsx`.
5. **Preserved zero credential exposure:** 0 API keys or private tokens introduced; working calculations and test assertions remain 100% intact.
6. **All tests verified:** Complete backend suite passed (**97 tests in 7.86s**); frontend production build succeeded (**755ms**).

---

## 2. Exact Changes by File

### A. `backend/pytest.ini` (New File)
- **Purpose:** Restricts default test collection to `backend/tests/` to prevent root scripts (`test_gnani.py`, `test_live_*.py`) from being collected or executed when running `pytest`.
- **Content:**
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  ```

### B. `backend/test_live_e2e.py`
- **File:** `backend/test_live_e2e.py` (Line 23)
- **Before:**
  ```python
  audio_path = Path("d:/bimasakshi/frontend/public/calculi_scenario.wav")
  ```
- **After:**
  ```python
  PROJECT_ROOT = Path(__file__).resolve().parent.parent
  audio_path = PROJECT_ROOT / "frontend" / "public" / "calculi_scenario.wav"
  ```

### C. `backend/test_proxy_e2e.py`
- **File:** `backend/test_proxy_e2e.py` (Lines 1–4, 27–29)
- **Before:**
  ```python
  import requests
  import json
  import time
  ...
  with open("d:/bimasakshi/frontend/public/sample_scenario.wav", "rb") as f:
  ```
- **After:**
  ```python
  import requests
  import json
  import time
  from pathlib import Path

  PROJECT_ROOT = Path(__file__).resolve().parent.parent
  ...
  sample_audio_path = PROJECT_ROOT / "frontend" / "public" / "sample_scenario.wav"
  with open(sample_audio_path, "rb") as f:
  ```

### D. `backend/services/gnani_service.py`
- **File:** `backend/services/gnani_service.py` (Lines 10, 51–110)
- **Changes:**
  - Added `import shutil`.
  - Added `check_ffmpeg_availability() -> Tuple[bool, Optional[str]]`.
  - In `normalize_to_pcm_wav(audio_bytes)`:
    - Retained fast-path for valid 16kHz PCM WAV without subprocess overhead.
    - If non-WAV / non-16kHz audio is provided and `ffmpeg` is not on PATH, raises `GnaniSTTError` with an actionable diagnostic message:
      > *"FFmpeg executable was not found on system PATH. FFmpeg is required to normalize browser audio (WebM/Opus) into 16,000 Hz 16-bit linear PCM WAV for Gnani Prisma STT. Please install FFmpeg (e.g. 'winget install Gyan.FFmpeg' on Windows or 'sudo apt-get install ffmpeg' on Linux) and ensure it is accessible in your system PATH."*

### E. `backend/main.py`
- **File:** `backend/main.py` (Lines 55–68, 96–100, 155–168)
- **Changes:**
  - In `lifespan(app)`: Verifies FFmpeg on startup and logs status.
  - In `HealthResponse`: Added `ffmpeg_available: bool = True`.
  - In `health_check()`: Dynamically probes `check_ffmpeg_availability()` and returns `ffmpeg_available` status.

### F. `backend/schemas/analysis.py`
- **File:** `backend/schemas/analysis.py` (Lines 201–204)
- **Changes:**
  - Added `checklist: List[str] = Field(default_factory=list, description="Actionable pre-admission checklist items for hospital desk and TPA reconciliation")` to `AnalysisResult`.
  - Fully backward-compatible; existing consumers receive an empty list if unspecified.

### G. `backend/services/policy_engine.py`
- **File:** `backend/services/policy_engine.py` (Lines 820–848)
- **Changes:**
  - Added deterministic checklist item generation in `evaluate_policy_rules`:
    - Mandatory schedule verification item.
    - Conditional differential billing inquiry item (if unconfirmed or True).
    - Room rent 1% cap threshold item (if room rent stated).
    - Code Excl 02 portability credit check item (if tenure < 24 months).
    - Hospital deposit reconciliation / refund assurance item (if hospital deposit stated).
    - Mandatory itemized hospital estimate item.
  - Passed `checklist=checklist` into `AnalysisResult`.

### H. `frontend/src/components/FindingsPanel.jsx` & `frontend/src/App.jsx`
- **Changes:**
  - `FindingsPanel`: Accepts `checklist` prop. If populated by backend, renders backend items; otherwise falls back to standard default items.
  - `App.jsx`: Passes `checklist={analysisResponse.analysis?.checklist}` to `<FindingsPanel />`.

### I. `backend/tests/test_policy_engine.py`
- **Changes:**
  - Added `test_dynamic_pre_admission_checklist_generation()` verifying dynamic checklist population.
  - Added `test_ffmpeg_availability_and_pcm_wav_passthrough()` verifying FFmpeg availability check and PCM WAV passthrough.

---

## 3. Automated Test Suite & Build Verification Results

### Backend `pytest` Suite:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-8.3.4, pluggy-1.6.0
rootdir: D:\bimasakshi\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.12.1
collected 97 items

tests/test_accident_intent_regression.py ........                        [  8%]
tests/test_analysis_api.py ........                                      [ 16%]
tests/test_api.py .......                                                [ 23%]
tests/test_gemini_service.py .....                                       [ 28%]
tests/test_multi_intent_deposit_regression.py ......                     [ 35%]
tests/test_policy_engine.py ................                             [ 51%]
tests/test_policy_engine_v2_regression.py ..........                     [ 61%]
tests/test_query_generalization.py ....................                  [ 82%]
tests/test_unseen_scenarios_audit.py ..........                          [ 92%]
tests/test_vectorstore.py .......                                        [100%]

============================= 97 passed in 7.86s ==============================
```
- **Total Tests:** 97
- **Passed:** 97 (100%)
- **Failed:** 0
- **Duration:** 7.86 seconds
- **Safety Verification:** Running bare `pytest` collected strictly from `backend/tests/` and did **not** execute live API scripts in root.

### Frontend Production Build (`npm run build`):
```text
> frontend@0.0.0 build
> vite build

vite v8.3.7 building client environment for production...
transforming...
✓ 2087 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.13 kB │ gzip:  0.62 kB
dist/assets/index-Bo9JGDcQ.css   31.23 kB │ gzip:  6.58 kB
dist/assets/index-BMeKAylr.js   290.63 kB │ gzip: 85.99 kB

✓ built in 755ms
```
- **Vite Bundling:** Clean compile in 755ms with 0 errors or warnings.

---

## 4. Git Diff Inspection & Credential Verification

### Credential & Secrets Verification:
- `git diff | grep -i 'key\|token\|secret'` confirmed **0 credentials** introduced into Git.
- Working tree remains clean with `.env` properly excluded by `.gitignore`.

### Full `git status`:
```text
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
	modified:   backend/main.py
	modified:   backend/schemas/analysis.py
	modified:   backend/services/gnani_service.py
	backend/services/policy_engine.py
	backend/test_live_e2e.py
	backend/test_proxy_e2e.py
	backend/tests/test_policy_engine.py
	frontend/src/App.jsx
	frontend/src/components/FindingsPanel.jsx

Untracked files:
	AUDIT_REPORT.md
	PHASE_1_5_REMEDIATION_REPORT.md
	backend/pytest.ini
```

---

## 5. Remaining Limitations

1. **Policy Scope Boundary:** Vector store currently indexes the 4 core clauses of the Star Health Premier policy (Room Rent, Kidney Calculi, PED, Robotic Surgery). Expanding to maternity, cataract, and daycare sub-limits will require indexing additional schedule clauses.
2. **Hospital Differential Billing Verification:** As health insurance pre-authorisations depend on hospital billing policy, differential billing status remains a user- or hospital-desk-confirmed parameter.
3. **Special Schedule Endorsements:** Specific customer endorsements (co-pay waivers, voluntary deductibles) require manual review of the policy schedule.

---

## 6. Next Step

Per your instructions, **no Git commit or remote push has been performed**. 

Please review the diff and this report. Upon your explicit approval, I will stage and commit these targeted remediation files to the private GitHub repository.

