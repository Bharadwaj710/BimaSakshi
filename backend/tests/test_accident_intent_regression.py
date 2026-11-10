"""
Regression Tests for Accident Exception and Primary Intent Detection
---------------------------------------------------------------------
Tests all 8 required scenarios:
1. Accident-related surgery within 24 months.
2. Kidney stone surgery without an accident.
3. Accident mentioned, but causal relationship unclear.
4. Room-rent-only question.
5. Pre-existing disease question.
6. Accident scenario where the user also asks about room rent.
7. Verify the Hindi response actually answers the primary question.
8. Verify that unrelated room-rent warnings do not override accident findings.
"""

import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.analysis import ExtractedInsuranceInfo
from services.policy_engine import evaluate_policy_rules
from services.response_service import compose_hindi_advisory_text


# --- Scenario 1: Accident-related surgery within 24 months ---
def test_scenario_1_accident_related_surgery_within_24_months():
    """Scenario 1: Treatment required due to an accident within 24 months is exempt from Code Excl 02."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        treatment_type="Emergency surgery required because of a road accident",
        is_accident_related=True,
        accident_causal_relationship="clear",
        policy_tenure_months=6,
    )
    result = evaluate_policy_rules(info)

    # 1. Accident exception is recognized
    assert any("Code Excl 02 Accident Exception" in f for f in result.findings)
    assert any("does NOT apply to claims arising due to an accident" in f for f in result.findings)

    # 2. No ordinary 24-month waiting period warning is generated
    assert not any("18 months remaining" in w for w in result.warnings)
    assert not any("waiting period under Code Excl 02" in w for w in result.warnings)

    # 3. STAR-PREMIER-WAIT-002 is prioritized
    assert "STAR-PREMIER-WAIT-002" in result.relevant_clause_ids

    # 4. Hindi advisory explains accident exception
    hindi_text = compose_hindi_advisory_text(info, result)
    assert "दुर्घटना (accident)" in hindi_text
    assert "24 महीने का वेटिंग पीरियड लागू नहीं होता" in hindi_text
    assert "पूर्णतः मुक्त है" in hindi_text

    # 5. Room rent is NOT discussed
    assert "पात्र कमरा किराया" not in hindi_text
    assert "अस्पताल की बिलिंग पद्धति" not in hindi_text


# --- Scenario 2: Kidney stone surgery without an accident ---
def test_scenario_2_kidney_stone_without_accident():
    """Scenario 2: Planned kidney stone surgery without accident is subject to 24-month waiting period."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_specified_disease",
        diagnosis_or_condition="Kidney stone",
        treatment_type="Calculi removal surgery",
        policy_tenure_months=14,
    )
    result = evaluate_policy_rules(info)

    # Must contain 24-month waiting period warning
    assert any("Code Excl 02" in w for w in result.warnings)
    assert any("10 months remaining" in w for w in result.warnings)
    assert not any("Code Excl 02 Accident Exception" in f for f in result.findings)

    # Hindi advisory explains waiting period for kidney stones
    hindi_text = compose_hindi_advisory_text(info, result)
    assert "किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है" in hindi_text
    assert "14 महीने" in hindi_text


# --- Scenario 3: Accident mentioned, but causal relationship unclear ---
def test_scenario_3_accident_mentioned_causality_unclear():
    """Scenario 3: Accident mentioned but causal link to surgery is unclear -> insufficient_information."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        diagnosis_or_condition="Kidney calculi",
        treatment_type="Planned elective surgery",
        user_question="I had a minor slip last month, does the waiting period apply to my kidney stone surgery?",
        is_accident_related=True,
        accident_causal_relationship="unclear",
        policy_tenure_months=12,
    )
    result = evaluate_policy_rules(info)

    # Must return insufficient_information
    assert any("insufficient_information: An accident was mentioned" in f for f in result.findings)
    assert any("Accident Causal Verification Required" in w for w in result.warnings)
    assert any("accident_causal_documentation" in m for m in result.missing_information)

    # Hindi advisory explains that waiver applies strictly to direct accident claims
    hindi_text = compose_hindi_advisory_text(info, result)
    assert "दुर्घटना का उल्लेख किया गया है" in hindi_text
    assert "सीधा चिकित्सीय संबंध अभी स्पष्ट नहीं है" in hindi_text
    assert "मेडिकल रिपोर्ट बीमा कंपनी से सत्यापित कराएं" in hindi_text


# --- Scenario 4: Room-rent-only question ---
def test_scenario_4_room_rent_only_question():
    """Scenario 4: Room-rent-only question prioritizes room rent and does not mention accidents."""
    info = ExtractedInsuranceInfo(
        primary_intent="room_rent_eligibility",
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
    )
    result = evaluate_policy_rules(info)

    assert any("Confirmed Sum Insured: ₹1,000,000.00" in f for f in result.findings)
    assert any("exceeds your confirmed eligible limit of ₹10,000.00" in w for w in result.warnings)
    assert "STAR-PREMIER-ROOM-001" in result.relevant_clause_ids

    hindi_text = compose_hindi_advisory_text(info, result)
    assert "10,000 रुपये प्रतिदिन है" in hindi_text
    assert "15,000 रुपये है" in hindi_text
    assert "दुर्घटना" not in hindi_text


# --- Scenario 5: Pre-existing disease question ---
def test_scenario_5_pre_existing_disease_question():
    """Scenario 5: Pre-existing disease question evaluates Code Excl 01."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_ped",
        diagnosis_or_condition="Hypertension and Diabetes",
        declared_ped=True,
        policy_tenure_months=10,
    )
    result = evaluate_policy_rules(info)

    assert any("Code Excl 01" in w for w in result.warnings)
    assert any("14 months remaining" in w for w in result.warnings)
    assert "STAR-PREMIER-PED-001" in result.relevant_clause_ids

    hindi_text = compose_hindi_advisory_text(info, result)
    assert "घोषित पूर्व-मौजूदा बीमारी (PED) पर 24 महीने का वेटिंग पीरियड लागू होता है" in hindi_text
    assert "10 महीने" in hindi_text
    assert "दुर्घटना" not in hindi_text


# --- Scenario 6: Accident scenario where user ALSO asks about room rent ---
def test_scenario_6_accident_with_room_rent_query():
    """Scenario 6: User asks about accident exception AND specifies room rent."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        treatment_type="Emergency fracture surgery due to an accident",
        is_accident_related=True,
        accident_causal_relationship="clear",
        policy_tenure_months=4,
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
    )
    result = evaluate_policy_rules(info)

    # 1. Accident exception is recognized
    assert any("Code Excl 02 Accident Exception" in f for f in result.findings)
    # 2. Room rent excess is also recognized
    assert any("exceeds your confirmed eligible limit" in w for w in result.warnings)
    # 3. Both clauses are relevant
    assert "STAR-PREMIER-WAIT-002" in result.relevant_clause_ids
    assert "STAR-PREMIER-ROOM-001" in result.relevant_clause_ids

    # 4. Hindi response answers accident FIRST, and ALSO includes room rent
    hindi_text = compose_hindi_advisory_text(info, result)
    assert "24 महीने का वेटिंग पीरियड लागू नहीं होता" in hindi_text
    assert "कमरे के किराए के संदर्भ में:" in hindi_text
    assert "पात्र किराया 10,000 रुपये प्रतिदिन है" in hindi_text
    assert "चुना गया किराया 15,000 रुपये है" in hindi_text


# --- Scenario 7: Verify Hindi response actually answers primary question ---
def test_scenario_7_hindi_response_strictly_answers_primary_question():
    """Scenario 7: Hindi response directly addresses user question without generic diversion."""
    # Test accident query
    info_accident = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        user_question="Does 24 month waiting period apply to accident surgery?",
        treatment_type="Surgery required because of an accident",
        is_accident_related=True,
        accident_causal_relationship="clear",
    )
    res_accident = evaluate_policy_rules(info_accident)
    hindi_accident = compose_hindi_advisory_text(info_accident, res_accident)

    # Must directly answer the question
    assert "वेटिंग पीरियड लागू नहीं होता" in hindi_accident
    assert "सत्यापित किए जाएंगे" in hindi_accident
    # Must NOT bring up sum insured
    assert "सम इंश्योर्ड की पुष्टि" not in hindi_accident


# --- Scenario 8: Verify unrelated room-rent warnings do not override accident findings ---
def test_scenario_8_room_rent_warnings_do_not_override_accident_findings():
    """Scenario 8: Absence of sum insured does not create false room-rent warnings for accident inquiries."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        treatment_type="Surgery due to an accidental fall",
        is_accident_related=True,
        accident_causal_relationship="clear",
        sum_insured=None,
        selected_room_rent_per_day=None,
    )
    result = evaluate_policy_rules(info)

    # Findings must lead with accident exception
    assert result.findings[0].startswith("Code Excl 02 Accident Exception")

    # Warnings must NOT contain room rent excess or differential billing warnings
    assert not any("room rent" in w.lower() for w in result.warnings)
    assert not any("differential billing" in w.lower() for w in result.warnings)

    # Hindi advisory focuses strictly on accident
    hindi = compose_hindi_advisory_text(info, result)
    assert "दुर्घटना (accident)" in hindi
    assert "वेटिंग पीरियड लागू नहीं होता" in hindi
    assert "सम इंश्योर्ड" not in hindi

