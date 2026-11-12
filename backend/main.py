"""
FastAPI Backend for BimaSakshi (Phase 2 & Phase 3)
---------------------------------------------------
End-to-end AI pipeline for voice-driven health insurance policy analysis:
- Speech-to-Text via Gnani Prisma v2.5
- Entity extraction & query normalization via Google Gemini (google-genai SDK)
- Policy clause semantic search via ChromaDB EphemeralClient
- Deterministic insurance rule engine (Star Health Premier Policy)
- Voice advisory synthesis via Gnani Timbre v2.5 (Hindi / Nalini)
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from schemas.analysis import (
    AnalysisResult,
    AudioAnalysisResponse,
    CalculationDetail,
    ExtractedInsuranceInfo,
    PolicyDocumentInfo,
    RetrievedClauseInfo,
    TranscriptionResult,
    TTSResult,
)
from services.gemini_service import extract_insurance_info, GeminiServiceError
from services.gnani_service import transcribe_audio, GnaniSTTError
from services.policy_engine import evaluate_policy_rules
from services.response_service import compose_hindi_advisory_text, synthesize_speech
from vectorstore import (
    get_collection_status,
    initialize_vector_store,
    retrieve_policy_clauses,
    retrieve_policy_clauses_multi,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bimasakshi.api")

# Lifespan Management: In-memory ChromaDB re-indexed on every startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BimaSakshi Backend (Phase 3 AI Pipeline)...")
    try:
        col = initialize_vector_store()
        logger.info(f"Vector store initialized successfully with {col.count()} clauses.")
    except Exception as e:
        logger.error(f"Failed to initialize vector store at startup: {e}")
        raise e

    # Check FFmpeg availability for audio conversion
    from services.gnani_service import check_ffmpeg_availability
    ffmpeg_ok, ffmpeg_bin = check_ffmpeg_availability()
    if ffmpeg_ok:
        logger.info(f"FFmpeg binary detected at: {ffmpeg_bin}")
    else:
        logger.warning(
            "FFmpeg binary was NOT found on PATH. "
            "Normalization from browser WebM/Opus to 16kHz PCM WAV requires FFmpeg."
        )
    yield
    logger.info("Shutting down BimaSakshi Backend.")


app = FastAPI(
    title="BimaSakshi Backend",
    version="0.3.0",
    description="Voice-driven Health Insurance Policy Pre-Audit & Claim Advisory API",
    lifespan=lifespan,
)

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> List[str]:
    """Builds allowed CORS origins from local defaults plus comma-separated CORS_ORIGINS env var."""
    raw = os.getenv("CORS_ORIGINS", "")
    extra = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    merged: List[str] = []
    for origin in DEFAULT_CORS_ORIGINS + extra:
        if origin not in merged:
            merged.append(origin)
    return merged


cors_origins = get_cors_origins()
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --- Phase 2 Schemas ---

class HealthResponse(BaseModel):
    app_name: str = "BimaSakshi Backend"
    status: str = "ok"
    vector_store_initialized: bool = True
    ffmpeg_available: bool = True


class PolicyStatusResponse(BaseModel):
    collection_name: str
    indexed_documents_count: int
    policy_name: str
    insurer: str
    uin: str
    document_version: str


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Policy query or coverage question",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of matching clauses to retrieve",
    )


class ClauseResult(BaseModel):
    clause_id: str
    clause_title: str
    retrieved_text: str
    source_page: str
    policy_info: PolicyDocumentInfo
    distance: float


class SearchResponse(BaseModel):
    query: str
    total_retrieved: int
    results: List[ClauseResult]


# --- Phase 2 Endpoints (Preserved) ---

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend Health Check",
    tags=["System"],
)
async def health_check():
    """Returns backend health and vector store initialization status."""
    try:
        status_info = get_collection_status()
        is_ready = status_info["indexed_documents_count"] > 0
    except Exception as e:
        logger.warning(f"Vector store health check failed: {e}")
        is_ready = False

    try:
        from services.gnani_service import check_ffmpeg_availability
        ffmpeg_ok, _ = check_ffmpeg_availability()
    except Exception:
        ffmpeg_ok = False

    return HealthResponse(
        app_name="BimaSakshi Backend",
        status="ok",
        vector_store_initialized=is_ready,
        ffmpeg_available=ffmpeg_ok,
    )


@app.get(
    "/api/policy/status",
    response_model=PolicyStatusResponse,
    summary="Policy Vector Store Status",
    tags=["Policy Retrieval"],
)
async def policy_status():
    """Returns current indexed collection metadata and document count."""
    try:
        info = get_collection_status()
        return PolicyStatusResponse(**info)
    except Exception as e:
        logger.error(f"Error fetching policy status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve policy vector store status: {e}",
        )


@app.post(
    "/api/policy/search",
    response_model=SearchResponse,
    summary="Semantic Search on Policy Clauses",
    tags=["Policy Retrieval"],
)
async def policy_search(request: SearchRequest):
    """Retrieves authentic policy clauses relevant to the user query using ChromaDB semantic retrieval."""
    stripped_query = request.query.strip()
    if not stripped_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query must not be empty or blank whitespace.",
        )

    try:
        matches = retrieve_policy_clauses(
            query=stripped_query,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error(f"Policy retrieval error for query '{stripped_query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector retrieval failed: {e}",
        )

    results: List[ClauseResult] = []
    for match in matches:
        results.append(
            ClauseResult(
                clause_id=match["clause_id"],
                clause_title=match["clause_title"],
                retrieved_text=match["retrieved_text"],
                source_page=match["source_page"],
                policy_info=PolicyDocumentInfo(**match["policy_info"]),
                distance=match["distance"],
            )
        )

    return SearchResponse(
        query=stripped_query,
        total_retrieved=len(results),
        results=results,
    )


# --- Phase 3 Endpoint: Complete End-to-End AI Analysis Pipeline ---

@app.post(
    "/api/analyze-audio",
    response_model=AudioAnalysisResponse,
    summary="Complete Audio Claim Analysis Pipeline",
    tags=["AI Pipeline"],
)
async def analyze_audio(
    audio: UploadFile = File(..., description="Uploaded audio recording (WAV, MP3, etc.)"),
    policy_id: Optional[str] = Form(None, description="Optional policy identifier"),
):
    """
    Executes the full BimaSakshi voice-to-voice insurance pre-audit pipeline:
    1. Validates and forwards audio to Gnani Prisma v2.5 for Speech-to-Text.
    2. Sends the Hindi/Hinglish transcript to Gemini for structured extraction & query normalization.
    3. Performs vector retrieval in ChromaDB with the normalized English query.
    4. Evaluates deterministic policy rules, deductions, and waiting periods.
    5. Synthesizes a context-specific Hindi advisory using Gnani Timbre v2.5.
    6. Returns a complete, verified analysis response.
    """
    logger.info(f"Incoming audio analysis request: filename='{audio.filename}', type='{audio.content_type}'")

    # Step 1: Read and validate audio file
    try:
        audio_bytes = await audio.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded audio file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read audio file: {e}",
        )

    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    filename = audio.filename or "upload.wav"
    content_type = audio.content_type or "audio/wav"

    # Step 2: Speech-to-Text via Gnani Prisma v2.5
    try:
        stt_result = transcribe_audio(
            audio_bytes=audio_bytes,
            filename=filename,
            content_type=content_type,
            language_code="hi-IN",
            model="prisma-v2.5",
        )
    except GnaniSTTError as ge:
        logger.error(f"Prisma STT error: {ge}")
        status_code = ge.status_code if ge.status_code and ge.status_code >= 400 else 502
        raise HTTPException(status_code=status_code, detail=f"Speech transcription failed: {ge}")
    except Exception as e:
        logger.error(f"Unexpected STT failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"STT gateway error: {e}",
        )

    transcript_text = stt_result.get("text", "").strip()

    # Step 3: Handle empty transcript
    if not transcript_text:
        logger.warning("Prisma returned an empty transcript.")
        empty_info = ExtractedInsuranceInfo(
            missing_information=["Audio could not be transcribed or speech was inaudible."],
            normalized_english_query="",
        )
        empty_analysis = evaluate_policy_rules(empty_info, [])
        return AudioAnalysisResponse(
            status="success",
            transcription=TranscriptionResult(
                text="",
                model=stt_result.get("model", "prisma-v2.5"),
                request_id=stt_result.get("request_id"),
                latency_sec=stt_result.get("latency_sec"),
            ),
            extracted_information=empty_info,
            retrieved_clauses=[],
            analysis=empty_analysis,
            tts=TTSResult(
                status="skipped",
                model="timbre-v2.5",
                spoken_text=None,
                error="Speech was inaudible or empty; audio synthesis skipped.",
            ),
        )

    # Step 4: Structured Information Extraction via Gemini
    try:
        extracted_info = extract_insurance_info(transcript=transcript_text)
    except GeminiServiceError as gse:
        logger.error(f"Gemini extraction error: {gse}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Information extraction failed: {gse}",
        )
    except Exception as e:
        logger.error(f"Unexpected extraction failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction error: {e}",
        )

    # Step 5: Semantic Retrieval from ChromaDB (Multi-Query Decomposed Retrieval)
    retrieval_queries = list(extracted_info.retrieval_queries or [])
    if not retrieval_queries and extracted_info.normalized_english_query:
        retrieval_queries = [extracted_info.normalized_english_query.strip()]

    if not retrieval_queries:
        cond = extracted_info.diagnosis_or_condition or "hospitalization coverage"
        retrieval_queries = [f"{cond} room rent waiting period"]

    logger.info(f"Retrieving clauses from ChromaDB for {len(retrieval_queries)} decomposed queries: {retrieval_queries}")
    raw_clauses = retrieve_policy_clauses_multi(queries=retrieval_queries, top_k=3)

    retrieved_clause_objs: List[RetrievedClauseInfo] = []
    retrieved_ids: List[str] = []
    for c in raw_clauses:
        retrieved_ids.append(c["clause_id"])
        retrieved_clause_objs.append(
            RetrievedClauseInfo(
                clause_id=c["clause_id"],
                clause_title=c["clause_title"],
                retrieved_text=c["retrieved_text"],
                source_page=c["source_page"],
                distance=c["distance"],
                policy_info=PolicyDocumentInfo(**c["policy_info"]),
            )
        )

    # Prioritize clauses based on user's primary intent
    combined_query_str = " ".join(retrieval_queries).lower()
    if (
        extracted_info.primary_intent == "waiting_period_accident"
        or "accident" in combined_query_str
        or "accident" in transcript_text.lower()
    ):
        retrieved_clause_objs.sort(key=lambda x: 0 if x.clause_id == "STAR-PREMIER-WAIT-002" else 1)
        retrieved_ids = [c.clause_id for c in retrieved_clause_objs]

    # Step 6: Deterministic Policy Rule Engine
    analysis_res = evaluate_policy_rules(
        info=extracted_info,
        retrieved_clause_ids=retrieved_ids,
    )

    # Step 7: Compose Hindi Advisory Text and Synthesize with Gnani Timbre
    hindi_text = compose_hindi_advisory_text(extracted_info, analysis_res)
    tts_result = synthesize_speech(text=hindi_text)

    # Step 8: Return Unified Response
    return AudioAnalysisResponse(
        status="success",
        transcription=TranscriptionResult(
            text=transcript_text,
            model=stt_result.get("model", "prisma-v2.5"),
            request_id=stt_result.get("request_id"),
            latency_sec=stt_result.get("latency_sec"),
        ),
        extracted_information=extracted_info,
        retrieved_clauses=retrieved_clause_objs,
        analysis=analysis_res,
        tts=tts_result,
    )
