"""
Integration Tests for POST /api/analyze-audio Pipeline (Phase 3)
Mocked external integrations to verify API robustness, error handling, and response structure.
"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from schemas.analysis import ExtractedInsuranceInfo, TTSResult
from services.gnani_service import GnaniSTTError
from services.gemini_service import GeminiServiceError


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


# Dummy 1-second WAV bytes
DUMMY_WAV = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


def test_api_missing_audio_payload(client):
    """1. Missing audio file should return 422 Unprocessable Entity."""
    response = client.post("/api/analyze-audio")
    assert response.status_code == 422


def test_api_empty_audio_bytes(client):
    """2. Empty audio file (0 bytes) should return 400 Bad Request."""
    files = {"audio": ("empty.wav", b"", "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 400
    assert "empty (0 bytes)" in response.json()["detail"]


@patch("main.transcribe_audio")
def test_api_prisma_failure(mock_transcribe, client):
    """3. Prisma STT failure raises 502 with error details."""
    mock_transcribe.side_effect = GnaniSTTError("Prisma Gateway Timeout", status_code=504)
    files = {"audio": ("test.wav", DUMMY_WAV, "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 504
    assert "Speech transcription failed" in response.json()["detail"]


@patch("main.transcribe_audio")
def test_api_empty_transcript(mock_transcribe, client):
    """4. Empty transcript handled gracefully without crash; TTS skipped."""
    mock_transcribe.return_value = {
        "text": "",
        "model": "prisma-v2.5",
        "request_id": "req-empty-123",
        "latency_sec": 0.25,
        "metadata": {},
    }
    files = {"audio": ("silence.wav", DUMMY_WAV, "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["transcription"]["text"] == ""
    assert data["tts"]["status"] == "skipped"
    assert "inaudible" in data["extracted_information"]["missing_information"][0]


@patch("main.transcribe_audio")
@patch("main.extract_insurance_info")
def test_api_gemini_failure(mock_extract, mock_transcribe, client):
    """5. Gemini API failure raises 502 Bad Gateway."""
    mock_transcribe.return_value = {
        "text": "मेरी तबीयत खराब है",
        "model": "prisma-v2.5",
        "request_id": "req-1",
        "latency_sec": 0.3,
    }
    mock_extract.side_effect = GeminiServiceError("Gemini quota exceeded")

    files = {"audio": ("test.wav", DUMMY_WAV, "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 502
    assert "Information extraction failed" in response.json()["detail"]


@patch("main.transcribe_audio")
@patch("main.extract_insurance_info")
@patch("main.synthesize_speech")
def test_api_valid_extraction_and_retrieval(mock_tts, mock_extract, mock_transcribe, client):
    """7 & 8. Valid extraction, retrieval, and rule engine output verification."""
    mock_transcribe.return_value = {
        "text": "मुझे मोतियाबिंद की सर्जरी करवानी है और कमरे का किराया 12000 रुपये है।",
        "model": "prisma-v2.5",
        "request_id": "req-ok-777",
        "latency_sec": 0.45,
    }
    mock_extract.return_value = ExtractedInsuranceInfo(
        diagnosis_or_condition="Cataract",
        selected_room_rent_per_day=12000.0,
        normalized_english_query="Cataract surgery room rent limit",
        missing_information=["sum_insured"],
    )
    mock_tts.return_value = TTSResult(
        status="success",
        model="timbre-v2.5",
        audio_base64="UklGRiQAAABXQVZFZm10...",
        mime_type="audio/wav",
        spoken_text="आपकी स्टार हेल्थ पॉलिसी के अनुसार...",
    )

    files = {"audio": ("query.wav", DUMMY_WAV, "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["transcription"]["text"] == "मुझे मोतियाबिंद की सर्जरी करवानी है और कमरे का किराया 12000 रुपये है।"
    assert data["extracted_information"]["selected_room_rent_per_day"] == 12000.0
    assert len(data["retrieved_clauses"]) > 0
    assert len(data["analysis"]["calculations"]) > 0
    assert data["tts"]["status"] == "success"


@patch("main.transcribe_audio")
@patch("main.extract_insurance_info")
@patch("main.synthesize_speech")
def test_api_timbre_failure_gracefully_handled(mock_tts, mock_extract, mock_transcribe, client):
    """9. Timbre TTS failure returns valid analysis with TTS error status without crashing API."""
    mock_transcribe.return_value = {
        "text": "कमरे का किराया 15000 है",
        "model": "prisma-v2.5",
        "request_id": "req-9",
        "latency_sec": 0.35,
    }
    mock_extract.return_value = ExtractedInsuranceInfo(
        selected_room_rent_per_day=15000.0,
        normalized_english_query="room rent limit and proportionate deduction",
    )
    # Timbre fails with error status
    mock_tts.return_value = TTSResult(
        status="failed",
        model="timbre-v2.5",
        audio_base64=None,
        spoken_text="कुछ हिंदी टेक्स्ट",
        error="Timbre HTTP 429: Rate limit exceeded",
    )

    files = {"audio": ("test.wav", DUMMY_WAV, "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    # Analysis is complete and valid
    assert len(data["analysis"]["calculations"]) > 0
    # TTS explicitly reported failed without failing the entire API response
    assert data["tts"]["status"] == "failed"
    assert "Rate limit exceeded" in data["tts"]["error"]


@patch("main.transcribe_audio")
@patch("main.extract_insurance_info")
@patch("main.synthesize_speech")
def test_api_full_workflow_mocked(mock_tts, mock_extract, mock_transcribe, client):
    """10. Full mocked workflow covering room rent excess + calculi waiting period."""
    mock_transcribe.return_value = {
        "text": "मेरी उम्र 52 वर्ष है। मुझे किडनी की पथरी की सर्जरी करवानी है। कमरे का किराया 15000 रुपये है।",
        "model": "prisma-v2.5",
        "request_id": "req-full-10",
        "latency_sec": 0.4,
    }
    mock_extract.return_value = ExtractedInsuranceInfo(
        age=52,
        sum_insured=1000000.0,
        diagnosis_or_condition="Kidney Calculi",
        treatment_type="Surgery",
        selected_room_rent_per_day=15000.0,
        policy_tenure_months=14,
        associated_medical_expenses=60000.0,
        hospital_differential_billing=True,
        normalized_english_query="Kidney calculi waiting period Code Excl 02 and room rent limit",
        missing_information=[],
    )
    mock_tts.return_value = TTSResult(
        status="success",
        model="timbre-v2.5",
        audio_base64="AAAA...",
        mime_type="audio/wav",
        spoken_text="पॉलिसी सलाह...",
    )

    files = {"audio": ("full.wav", DUMMY_WAV, "audio/wav")}
    response = client.post("/api/analyze-audio", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "STAR-PREMIER-ROOM-001" in data["analysis"]["relevant_clause_ids"]
    assert "STAR-PREMIER-WAIT-002" in data["analysis"]["relevant_clause_ids"]
    assert any("proportionate deduction" in w.lower() for w in data["analysis"]["warnings"])
    assert any("24-month waiting period" in w for w in data["analysis"]["warnings"])

