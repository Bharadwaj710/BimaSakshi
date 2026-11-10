"""
Unit Tests for Gemini Extraction Service & Schemas (Phase 3)
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.analysis import ExtractedInsuranceInfo
from services.gemini_service import extract_insurance_info, GeminiServiceError


def test_extracted_insurance_info_defaults_and_nulls():
    """Verify that unspecified values remain null and are not coerced to 0 or False."""
    info = ExtractedInsuranceInfo()
    assert info.age is None
    assert info.sum_insured is None
    assert info.policy_tenure_months is None
    assert info.selected_room_rent_per_day is None
    assert info.eligible_room_rent_per_day is None
    assert info.associated_medical_expenses is None
    assert info.pharmacy_expenses is None
    assert info.diagnostic_expenses is None
    assert info.co_payment_percentage is None
    assert info.hospital_differential_billing is None
    assert info.declared_ped is None
    assert info.continuity_of_coverage is None
    assert info.normalized_english_query == ""
    assert isinstance(info.missing_information, list)


def test_extracted_insurance_info_valid_population():
    """Verify valid types and round-trip JSON serialization."""
    data = {
        "age": 45,
        "sum_insured": 1000000.0,
        "policy_tenure_months": 18,
        "diagnosis_or_condition": "Kidney Calculi",
        "treatment_type": "Lithotripsy",
        "selected_room_rent_per_day": 12000.0,
        "eligible_room_rent_per_day": 10000.0,
        "estimated_hospital_bill": 80000.0,
        "associated_medical_expenses": 30000.0,
        "pharmacy_expenses": 15000.0,
        "diagnostic_expenses": 10000.0,
        "co_payment_percentage": 10.0,
        "hospital_differential_billing": True,
        "declared_ped": False,
        "continuity_of_coverage": True,
        "normalized_english_query": "Kidney calculi waiting period and room rent proportionate deduction",
        "missing_information": [],
    }
    info = ExtractedInsuranceInfo(**data)
    assert info.age == 45
    assert info.sum_insured == 1000000.0
    assert info.diagnosis_or_condition == "Kidney Calculi"
    assert info.hospital_differential_billing is True
    assert info.declared_ped is False


def test_extract_insurance_info_empty_transcript():
    """Empty transcript should return safe default without calling API."""
    res = extract_insurance_info("")
    assert "empty or inaudible" in res.missing_information[0]
    assert res.normalized_english_query == ""


@patch("services.gemini_service.get_gemini_client")
def test_extract_insurance_info_mocked_success(mock_get_client):
    """Mocked test of successful Gemini structured output extraction."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '''{
        "age": 55,
        "sum_insured": 1000000,
        "policy_start_date": null,
        "policy_tenure_months": 12,
        "diagnosis_or_condition": "Kidney Stones",
        "treatment_type": "Surgical removal",
        "selected_room_rent_per_day": 15000,
        "eligible_room_rent_per_day": null,
        "estimated_hospital_bill": 120000,
        "associated_medical_expenses": 50000,
        "pharmacy_expenses": null,
        "diagnostic_expenses": null,
        "co_payment_percentage": null,
        "hospital_differential_billing": true,
        "declared_ped": null,
        "continuity_of_coverage": null,
        "normalized_english_query": "Waiting period for kidney stones surgery and room rent eligibility",
        "missing_information": ["co_payment_percentage", "pharmacy_expenses"]
    }'''
    mock_client.models.generate_content.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = extract_insurance_info("कुछ हिंदी ट्रांसक्रिप्ट")
    assert result.age == 55
    assert result.sum_insured == 1000000.0
    assert result.selected_room_rent_per_day == 15000.0
    assert result.diagnosis_or_condition == "Kidney Stones"
    assert "Waiting period for kidney stones" in result.normalized_english_query


@patch("services.gemini_service.get_gemini_client")
def test_extract_insurance_info_api_failure(mock_get_client):
    """Verify GeminiServiceError is raised when API fails."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API rate limit")
    mock_get_client.return_value = mock_client

    with pytest.raises(GeminiServiceError) as exc_info:
        extract_insurance_info("Some test transcript")
    assert "Gemini information extraction failed" in str(exc_info.value)

