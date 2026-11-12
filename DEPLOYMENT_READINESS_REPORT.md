# BimaSakshi — Production Deployment Preparation Audit Report

**Audit Date:** 2026-11-12  
**Target Hosting:** Render (Backend Web Service via Docker) + Vercel (Frontend Static SPA)  
**Repository Baseline:** Commit `114b3c5` (`main`) — `https://github.com/Bharadwaj710/BimaSakshi.git`  
**Audit Scope:** Full backend, frontend, dependency, FFmpeg, ChromaDB, CORS, security, and hosting readiness inspection (zero business logic or rule-engine edits).

---

## 1. Executive Summary & Deployment Readiness Verdict

Three critical public-deployment blockers were discovered during code inspection and resolved with minimal configuration updates:

| Blocker Discovered During Inspection | Root Cause | Minimal Resolution Applied | Status |
| :--- | :--- | :--- | :---: |
| **1. Production Frontend API Routing** | [`frontend/src/services/api.js`](file:///d:/bimasakshi/frontend/src/services/api.js) used relative `/health` and `/api/...` paths relying on `vite.config.js` dev proxy, which does not exist on Vercel static hosting. | Updated `api.js` to read `import.meta.env.VITE_API_BASE_URL` (falling back to `''` for local Vite dev proxy). Added [`frontend/.env.example`](file:///d:/bimasakshi/frontend/.env.example) and [`frontend/vercel.json`](file:///d:/bimasakshi/frontend/vercel.json). | `FIXED` |
| **2. Production CORS Rejection** | [`backend/main.py`](file:///d:/bimasakshi/backend/main.py) hardcoded `allow_origins` strictly to `http://localhost:5173` and `http://127.0.0.1:5173`. Requests from Vercel (`*.vercel.app`) would be blocked by browser CORS policy. | Added configurable `CORS_ORIGINS` (comma-separated) and optional `CORS_ORIGIN_REGEX` in `backend/main.py` while keeping localhost dev origins intact. | `FIXED` |
| **3. Host `ffmpeg` Dependency on Render** | [`backend/services/gnani_service.py`](file:///d:/bimasakshi/backend/services/gnani_service.py) requires the `ffmpeg` binary on `PATH` to convert browser `WebM/Opus` recordings into `16,000 Hz` mono 16-bit PCM WAV for Prisma v2.5 STT. Render's native Python runtime does not pre-install `ffmpeg`. | Created production [`backend/Dockerfile`](file:///d:/bimasakshi/backend/Dockerfile) (`python:3.12-slim` + `apt-get install ffmpeg`), pre-warmed ChromaDB ONNX embeddings, and bound `uvicorn` to `0.0.0.0:${PORT:-8000}`. Added [`backend/.dockerignore`](file:///d:/bimasakshi/backend/.dockerignore). | `FIXED` |

**Deployment Readiness Status:** **READY FOR STAGING / PUBLIC DEPLOYMENT** (pending execution of Docker build on Render and setting the environment variables documented below).

---

## 2. Backend Audit Findings

| Inspection Area | Observed Implementation & Findings | Status |
| :--- | :--- | :---: |
| **FastAPI Entry Point** | [`backend/main.py`](file:///d:/bimasakshi/backend/main.py) defines `app` (`FastAPI(..., lifespan=lifespan)`). Listens cleanly via `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}` inside Docker CMD. | `PASS` |
| **`requirements.txt`** | Verified against all imports across `main.py`, `vectorstore.py`, `schemas/`, and `services/`: `requests`, `python-dotenv`, `fastapi>=0.115.0` (`0.115.6` tested), `uvicorn>=0.30.0` (`0.34.0`), `pydantic>=2.7.0` (`2.14.3`), `chromadb>=0.5.0` (`1.5.9`), `httpx>=0.27.0`, `pytest>=8.0.0`, `google-genai>=3.0.0` (`3.0.0`), `python-multipart>=0.0.9`. No missing dependencies. | `PASS` |
| **Python Version** | Verified locally on Python `3.13.3`. Docker image uses `python:3.12-slim` for optimal pre-built Linux wheels (`onnxruntime`, `chromadb`, `pydantic-core`). | `PASS` |
| **FFmpeg & Audio Pipeline** | `normalize_to_pcm_wav()` uses in-memory `subprocess.run(["ffmpeg", ...])` pipes (`pipe:0` $\rightarrow$ `pipe:1`), converting browser `WebM/Opus`, `OGG`, `MP3`, `M4A`, or headerless PCM into `16,000 Hz`, mono, `pcm_s16le` WAV. Fast-paths valid 16kHz PCM WAV. Docker guarantees `ffmpeg` availability. | `PASS` |
| **Gnani Prisma v2.5 STT** | Endpoint `https://api.vachana.ai/stt/v3` (overrideable via `GNANI_STT_ENDPOINT`). Header `X-API-Key-ID`. Request timeout: `30.0s`. Upload limit enforced at `MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024` (10 MB, returns HTTP 413). | `PASS` |
| **Gnani Timbre v2.5 TTS** | Endpoint `https://api.vachana.ai/api/v1/tts/inference` (overrideable via `GNANI_TTS_ENDPOINT`). Voice `Nalini` (`hi-IN`, 48kHz WAV). Request timeout: `30.0s`. Fails gracefully without breaking JSON analysis if TTS errors or times out. | `PASS` |
| **Google Gemini 2.5 Flash** | [`backend/services/gemini_service.py`](file:///d:/bimasakshi/backend/services/gemini_service.py) uses `google-genai` SDK (`v1beta`), model `gemini-2.5-flash` (overrideable via `GEMINI_MODEL`), strict `response_schema=ExtractedInsuranceInfo`, `temperature=0.0`. Reads `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) directly from environment. | `PASS` |
| **ChromaDB & Policy Corpus** | [`backend/vectorstore.py`](file:///d:/bimasakshi/backend/vectorstore.py) uses `chromadb.EphemeralClient()` + `DefaultEmbeddingFunction()` (`all-MiniLM-L6-v2` ONNX) and loads the tracked Markdown corpus [`backend/data/policy_clauses.md`](file:///d:/bimasakshi/backend/data/policy_clauses.md) inside FastAPI `lifespan` via `Path(__file__).resolve().parent / "data" / "policy_clauses.md"`. **No external DB or persisted disk volume is required.** ONNX model (~79 MB) is pre-cached during `Dockerfile` build so container startup does not rely on S3 downloads at boot. | `PASS` |
| **Memory Footprint** | Measured actual Python process Working Set after FastAPI startup + ChromaDB indexing + semantic query execution: **150.6 MB**, leaving substantial headroom under Render's **512 MB** Free tier RAM limit. | `PASS` |
| **CORS & Health Check** | `/health` verifies both ChromaDB initialization (`indexed_documents_count > 0`) and FFmpeg PATH availability (`ffmpeg_available: true`). CORS now reads `CORS_ORIGINS` and optional `CORS_ORIGIN_REGEX`. | `PASS` |
| **`.env` Behavior in Prod** | Services call `load_dotenv(dotenv_path=env_path)` only when `backend/.env` exists; `.dockerignore` and `.gitignore` exclude `.env`, so Render platform environment variables are used directly with zero file leakage. | `PASS` |

---

## 3. Frontend Audit Findings

| Inspection Area | Observed Implementation & Findings | Status |
| :--- | :--- | :---: |
| **`package.json` & Tooling** | React `19.3.1`, Vite `8.3.6`, `@tailwindcss/vite` `4.3.5`, `lucide-react` `1.71.0`. Clean static bundle output (`dist/`). | `PASS` |
| **Vite Dev vs. Vercel Prod** | [`frontend/vite.config.js`](file:///d:/bimasakshi/frontend/vite.config.js) proxies `/api` and `/health` to `http://127.0.0.1:8000` during local `vite dev` only. Vercel ignores `vite.config.js` dev server proxy when serving `dist/`. | `VERIFIED` |
| **API Client Config** | [`frontend/src/services/api.js`](file:///d:/bimasakshi/frontend/src/services/api.js) now reads `import.meta.env.VITE_API_BASE_URL` (strips trailing slash). When set on Vercel, `/health`, `/api/policy/status`, `/api/policy/search`, and `/api/analyze-audio` target Render directly. Sample scenario `.wav` assets in `frontend/public/*.wav` remain relative to Vercel's own origin. | `PASS` |
| **Audio Capture & Playback** | `VoiceRecorder.jsx` captures `audio/webm;codecs=opus` (Chrome/Edge) or `ogg`/`wav` via `MediaRecorder`. `VoiceAdvisoryBanner.jsx` decodes Base64 WAV into `Blob` (`URL.createObjectURL`) and revokes URLs cleanly on unmount. | `PASS` |
| **Secret Isolation** | Zero secrets in frontend code. Only non-secret public `VITE_API_BASE_URL` is used. | `PASS` |

---

## 4. Complete Environment Variables Reference

Every environment variable below was verified directly from source inspection (`backend/main.py`, `backend/services/*.py`, `frontend/src/services/api.js`). No secret values are included.

| Variable Name | Required By | Purpose | Secret or Public | Where to Configure |
| :--- | :--- | :--- | :---: | :--- |
| `GNANI_API_KEY` | Backend (`gnani_service.py`, `response_service.py`) | Authenticates Prisma v2.5 STT and Timbre v2.5 TTS requests (`X-API-Key-ID` header). *(Fallback aliases supported in code: `GNANI_API_KEY_ID`, `VACHANA_API_KEY`)* | **Secret** | **Render** Web Service Environment Variables (and local `backend/.env`) |
| `GEMINI_API_KEY` | Backend (`gemini_service.py`) | Authenticates Google Gen AI SDK (`gemini-2.5-flash`) entity extraction & query normalization. *(Fallback alias: `GOOGLE_API_KEY`)* | **Secret** | **Render** Web Service Environment Variables (and local `backend/.env`) |
| `CORS_ORIGINS` | Backend (`main.py`) | Comma-separated production frontend URLs permitted for CORS (e.g., `https://bimasakshi.vercel.app`). Localhost `5173` defaults are always included. | **Public** | **Render** Web Service Environment Variables |
| `CORS_ORIGIN_REGEX` | Backend (`main.py`) | *(Optional)* Scoped regex for Vercel preview URLs only when needed (e.g., `https://bimasakshi-[a-z0-9-]+\.vercel\.app`). Prefer exact `CORS_ORIGINS` in production. | **Public** | **Render** Web Service Environment Variables |
| `GEMINI_MODEL` | Backend (`gemini_service.py`) | *(Optional)* Overrides default `gemini-2.5-flash`. | **Public** | **Render** Environment Variables (optional) |
| `GNANI_STT_ENDPOINT` | Backend (`gnani_service.py`) | *(Optional)* Overrides default `https://api.vachana.ai/stt/v3`. | **Public** | **Render** Environment Variables (optional) |
| `GNANI_TTS_ENDPOINT` | Backend (`response_service.py`) | *(Optional)* Overrides default `https://api.vachana.ai/api/v1/tts/inference`. | **Public** | **Render** Environment Variables (optional) |
| `PORT` | Render / Docker (`Dockerfile`) | Port Uvicorn binds to (`0.0.0.0:${PORT:-8000}`). Auto-injected by Render (`10000` by default). | **Platform** | Auto-injected by **Render** (do not hardcode unless overriding) |
| `VITE_API_BASE_URL` | Frontend (`frontend/src/services/api.js`) | Full HTTPS origin of deployed Render backend (e.g., `https://bimasakshi-backend.onrender.com`, no trailing slash). Leave unset in local Vite dev. | **Public** | **Vercel** Project Environment Variables (Production & Preview) |

> **Security Note:** Never create `VITE_GNANI_API_KEY` or `VITE_GEMINI_API_KEY`. Vite embeds all `VITE_*` variables into client-side JavaScript bundles. Only `VITE_API_BASE_URL` belongs in Vercel.

---

## 5. Exact Render Deployment Instructions (Backend)

Render's **Docker** runtime is required so `ffmpeg` and pre-warmed ChromaDB ONNX weights are reliably available.

1. Log in to **Render** (`https://dashboard.render.com`) $\rightarrow$ click **New +** $\rightarrow$ **Web Service**.
2. Connect your private GitHub repository (`Bharadwaj710/BimaSakshi`), branch `main`.
3. Configure service settings:
   - **Name:** `bimasakshi-backend` (or preferred name)
   - **Region:** Singapore or Oregon (choose closest region to users / low latency)
   - **Root Directory:** `backend`
   - **Language / Environment:** **Docker**
   - **Dockerfile Path:** `./Dockerfile` *(relative to `backend/` root directory)*
   - **Docker Build Context Directory:** `.` *(relative to `backend/`)*
   - **Instance Type:** Free (512 MB RAM) or Starter (recommended to avoid 15-minute cold spin-down)
4. Configure **Health Check Path** (under Advanced):
   - **Health Check Path:** `/health`
5. Add **Environment Variables** under the **Environment** tab:
   - `GNANI_API_KEY` = `<your Gnani API key>`
   - `GEMINI_API_KEY` = `<your Gemini API key>`
   - `CORS_ORIGINS` = `https://<your-vercel-domain>.vercel.app` *(exact production origin preferred; comma-separate multiple exact domains if needed)*
   - *(Optional)* `CORS_ORIGIN_REGEX` = `https://bimasakshi-[a-z0-9-]+\.vercel\.app` *(omit in production unless preview deployments are strictly required; never use an unanchored `.*\.vercel\.app` wildcard)*
6. Deploy and note the assigned public URL (e.g., `https://bimasakshi-backend.onrender.com`).

---

## 6. Exact Vercel Deployment Instructions (Frontend)

1. Log in to **Vercel** (`https://vercel.com/dashboard`) $\rightarrow$ **Add New...** $\rightarrow$ **Project**.
2. Import your GitHub repository (`Bharadwaj710/BimaSakshi`).
3. Configure **Project Settings**:
   - **Framework Preset:** `Vite` *(also declared in `frontend/vercel.json`)*
   - **Root Directory:** Click **Edit** and select `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add **Environment Variable** before clicking Deploy:
   - **Name:** `VITE_API_BASE_URL`
   - **Value:** `https://bimasakshi-backend.onrender.com` *(exact Render URL from Step 5, without a trailing slash)*
   - **Environments:** Production, Preview
5. Click **Deploy**. Note the deployed frontend URL (e.g., `https://bimasakshi.vercel.app`).
6. Return to **Render $\rightarrow$ Environment** and set `CORS_ORIGINS=https://bimasakshi.vercel.app` (triggering a quick Render restart/redeploy if not already set).

---

## 7. Post-Deployment Verification Checklist

Run these checks once both Render and Vercel finish deploying:

1. **Render Backend Health Check:**
   ```bash
   curl https://<your-render-url>.onrender.com/health
   ```
   Expected HTTP `200`:
   ```json
   {"app_name":"BimaSakshi Backend","status":"ok","vector_store_initialized":true,"ffmpeg_available":true}
   ```
   Verify `"vector_store_initialized": true` AND `"ffmpeg_available": true`.

2. **Policy Corpus Verification:**
   ```bash
   curl https://<your-render-url>.onrender.com/api/policy/status
   ```
   Expected HTTP `200` with `"indexed_documents_count": 4` and `"uin": "SHAHLIP22226V012122"`.

3. **CORS Preflight Check (simulating Vercel browser request):**
   ```bash
   curl -i -X OPTIONS https://<your-render-url>.onrender.com/api/analyze-audio \
     -H "Origin: https://<your-vercel-app>.vercel.app" \
     -H "Access-Control-Request-Method: POST"
   ```
   Confirm `HTTP/2 200` and response header `access-control-allow-origin: https://<your-vercel-app>.vercel.app`.

4. **Vercel Frontend Live Verification (Browser):**
   - Open `https://<your-vercel-app>.vercel.app` over **HTTPS** (required by browsers for `navigator.mediaDevices.getUserMedia` microphone access).
   - Confirm header shows green **`System Ready (4 clauses)`**.
   - Switch to **Preset Scenarios** $\rightarrow$ select **Scenario A** $\rightarrow$ click **Analyze Policy Claim** $\rightarrow$ verify transcript, extracted parameters, calculation receipt, policy evidence, and Hindi voice audio playback + WAV download.
   - Test **Record Voice** using your microphone (verifying browser WebM $\rightarrow$ Render FFmpeg $\rightarrow$ Prisma STT pipeline end-to-end).

---

## 8. Actual Tests & Checks Executed

| Check Executed | Command / Method | Result |
| :--- | :--- | :--- |
| **Backend Automated Test Suite** | `pytest -v` in `d:\bimasakshi\backend` (scoped via `pytest.ini` to `tests/`) | **97 passed in 14.97s** (final re-run after all config updates) |
| **Frontend Production Build** | `npm run build` in `d:\bimasakshi\frontend` | **Built cleanly in 925ms** (`dist/index.html` 1.18 kB, CSS 37.24 kB, JS 293.03 kB) |
| **Dynamic CORS Preflight Check** | FastAPI `TestClient` `OPTIONS /api/analyze-audio` with `CORS_ORIGINS=https://bimasakshi.vercel.app` | **HTTP 200**, `Access-Control-Allow-Origin: https://bimasakshi.vercel.app` |
| **ChromaDB ONNX Cache Alignment** | Inspected `ONNXMiniLM_L6_V2.DOWNLOAD_PATH` (`Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2"`) | Verified `ENV HOME=/root` in `Dockerfile` pins build warmup & runtime to `/root/.cache/...` |
| **Process Memory Footprint** | FastAPI lifespan + ChromaDB init + `/api/policy/search` measured via Windows WorkingSet64 | **150.6 MB** (safe for Render 512 MB Free tier) |
| **Secret & Gitignore Audit** | Complete `git status` and `git diff` inspection across all 9 touched/added files | **0 secrets, 0 generated binaries, 0 local databases** in diff; `.env` excluded from Git & `.dockerignore` |
| **Docker Image Build** | Attempted `Docker Desktop.exe` launch + `docker build -t bimasakshi-backend ./backend` | **Unverified locally** — `Docker Desktop.exe` exists in AppData, but `npipe:////./pipe/dockerDesktopLinuxEngine` did not come online in this session. Image build must be verified on Render or after manually starting Docker Desktop. |

---

## 9. Remaining Operational Limitations

1. **Render Free Tier Cold Starts & Timeouts:** On Render's Free plan, services spin down after 15 minutes of inactivity. The first request after idle incurs ~30–50s spin-up delay; if `/health` is polled by the browser every 15s, it will automatically trigger wake-up once opened. Also note Free tier has **512 MB RAM** and Render's proxy has an idle timeout (~100s), whereas typical E2E analysis finishes in 4–12s.
2. **External API Quotas & Network Latency:** Live analysis relies on Gnani Prisma v2.5 (5,000-credit limit), Gnani Timbre v2.5, and Gemini 2.5 Flash free/paid tier quotas. HTTP 429 from Gemini or timeout (>30s) on Gnani returns an error status (TTS timeout degrades gracefully to text-only).
3. **Upload File Size Limit:** Backend enforces `MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024` (10 MB) in `gnani_service.py` (HTTP 413); browser microphone clips are typically <500 KB, while huge uncompressed desktop `.wav` uploads >10 MB will be rejected.
4. **In-Memory ChromaDB Ephemeral Scope:** Policy corpus (`backend/data/policy_clauses.md`) currently holds 4 core Star Health Premier clauses. Updates require editing `policy_clauses.md` and redeploying Render.
5. **Local Docker Build Unverified:** Since the local Docker Desktop engine is stopped, run your first build directly on Render or start Docker Desktop locally and run `docker build -t bimasakshi-backend ./backend` to validate before pushing.

---

**Next Step:** Review the modified and newly added deployment files (`backend/Dockerfile`, `backend/.dockerignore`, `backend/main.py`, `frontend/src/services/api.js`, `frontend/vercel.json`, `frontend/.env.example`, `.env.example`, `backend/.env.example`). Let me know if you approve committing and pushing these preparation files to GitHub before deploying on Render and Vercel.

