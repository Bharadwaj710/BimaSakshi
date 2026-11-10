"""
Regression Tests for Policy Engine V2 (Issues 1-6)
---------------------------------------------------
Validates fixes for:
1. Ambiguous generic kidney problem (insufficient information requested).
2. Explicit kidney calculi (Code Excl 02 evaluated).
3. PED declared but acceptance unconfirmed.
4. PED declared and accepted by insurer.
5. Accident exception (Code Excl 02 waiver).
6. Ordinary waiting-period question without accident (no accidental mentions).
7. Robotic surgery with ₹10 Lakh SI (Coverage 14: 50% = ₹5 Lakh).
8. Robotic surgery with missing SI (illustrative 50% calculation).
9. Room rent with ICU charges (ICU safeguard against proportionate deduction).
10. Combined robotic surgery and room-rent inquiry.
"""

import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.analysis import ExtractedInsuranceInfo
from services.policy_engine import (
    evaluate_policy_rules,
    is_generic_kidney_condition,
    DEMO_SUM_INSURED_DEFAULT,
    MODERN_TREATMENT_COVERAGE_PERCENTAGE,
)
from services.response_service import compose_hindi_advisory_text
from vectorstore import retrieve_policy_clauses


# --- TEST 1: Ambiguous Kidney Problem ---
def test_regression_1_ambiguous_kidney_problem():
    """Issue 1: Generic kidney problem is flagged as ambiguous and requests specific diagnosis."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="kidney ki problem",
        user_question="Mujhe kidney ki problem hai aur doctor ne operation suggest kiya hai.",
        primary_intent="ambiguous_diagnosis",
    )
    assert is_generic_kidney_condition(info) is True

    result = evaluate_policy_rules(info)

    # 1. Must flag insufficient_information for generic kidney condition
    assert any("insufficient_information: Diagnosis stated as generic kidney condition" in f for f in result.findings)
    # 2. Must generate Ambiguous Diagnosis warning
    assert any("Ambiguous Diagnosis" in w for w in result.warnings)
    # 3. Must request specific clinical diagnosis in missing_info
    assert any("specific_clinical_diagnosis" in m for m in result.missing_information)
    # 4. Must NOT evaluate as Code Excl 02 kidney calculi
    assert "STAR-PREMIER-WAIT-002" not in result.relevant_clause_ids
    # 5. Hindi advisory asks for specific diagnosis
    hindi = compose_hindi_advisory_text(info, result)
    assert "किडनी की सामान्य समस्या" in hindi
    assert "सटीक डायग्नोसिस की पुष्टि करें" in hindi


# --- TEST 2: Explicit Kidney Calculi ---
def test_regression_2_explicit_kidney_calculi():
    """Issue 1: Explicit kidney calculi correctly evaluates Code Excl 02."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="kidney stone",
        treatment_type="lithotripsy procedure",
        policy_tenure_months=14,
        primary_intent="waiting_period_specified_disease",
    )
    assert is_generic_kidney_condition(info) is False

    result = evaluate_policy_rules(info)

    assert "STAR-PREMIER-WAIT-002" in result.relevant_clause_ids
    assert any("Code Excl 02" in w for w in result.warnings)
    assert any("10 months remaining" in w for w in result.warnings)
    assert not any("Ambiguous Diagnosis" in w for w in result.warnings)


# --- TEST 3: PED Declared but Acceptance Unconfirmed ---
def test_regression_3_ped_declared_acceptance_unconfirmed():
    """Issue 3: Declared PED without confirmed insurer acceptance flags acceptance condition."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_ped",
        diagnosis_or_condition="Hypertension",
        declared_ped=True,
        ped_accepted_by_insurer=None,
        policy_tenure_months=26,
    )
    result = evaluate_policy_rules(info)

    assert "STAR-PREMIER-PED-001" in result.relevant_clause_ids
    assert any("Insurer Acceptance Unconfirmed" in w for w in result.warnings)
    assert any("Code Excl 01 Acceptance Requirement" in f for f in result.findings)
    assert any("ped_insurer_acceptance" in m for m in result.missing_information)

    hindi = compose_hindi_advisory_text(info, result)
    assert "पॉलिसी शेड्यूल में विधिवत स्वीकृत (accepted)" in hindi


# --- TEST 4: PED Declared and Accepted ---
def test_regression_4_ped_declared_and_accepted():
    """Issue 3: Declared PED with insurer acceptance confirms coverage after 24 months."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_ped",
        diagnosis_or_condition="Type 2 Diabetes",
        declared_ped=True,
        ped_accepted_by_insurer=True,
        policy_tenure_months=26,
    )
    result = evaluate_policy_rules(info)

    assert "STAR-PREMIER-PED-001" in result.relevant_clause_ids
    assert any("Continuous coverage of 26 months satisfies the 24-month PED waiting period" in f for f in result.findings)
    assert not any("Insurer Acceptance Unconfirmed" in w for w in result.warnings)


# --- TEST 5: Accident Exception ---
def test_regression_5_accident_exception():
    """Issue 2: Accident exception correctly waives Code Excl 02 waiting period."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        treatment_type="Emergency fracture fixation surgery required because of a road accident",
        is_accident_related=True,
        accident_causal_relationship="clear",
        policy_tenure_months=5,
    )
    result = evaluate_policy_rules(info)

    assert any("Code Excl 02 Accident Exception" in f for f in result.findings)
    assert not any("waiting period under Code Excl 02" in w for w in result.warnings)

    hindi = compose_hindi_advisory_text(info, result)
    assert "दुर्घटना (accident)" in hindi
    assert "24 महीने का वेटिंग पीरियड लागू नहीं होता" in hindi


# --- TEST 6: Ordinary Waiting-Period Question Without Accident ---
def test_regression_6_ordinary_waiting_period_without_accident():
    """Issue 2: Ordinary waiting period explanation does NOT mention accident."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_specified_disease",
        diagnosis_or_condition="Kidney stone",
        policy_tenure_months=14,
        is_accident_related=False,
    )
    result = evaluate_policy_rules(info)

    # Warning must NOT mention accident
    assert any("10 months remaining" in w for w in result.warnings)
    assert not any("claim resulted from an accident" in w for w in result.warnings)

    hindi = compose_hindi_advisory_text(info, result)
    assert "किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है" in hindi
    assert "दुर्घटना" not in hindi


# --- TEST 7: Robotic Surgery with ₹10 Lakh SI ---
def test_regression_7_robotic_surgery_10_lakh_si():
    """Issue 4: Robotic surgery with ₹10 Lakh SI evaluates Coverage 14 up to ₹5 Lakh (50%)."""
    info = ExtractedInsuranceInfo(
        user_question="Star Health Premier policy robotic surgery special coverage amount",
        treatment_type="Robotic prostatectomy surgery",
        sum_insured=1_000_000.0,
        primary_intent="modern_treatment_robotic",
        is_robotic_surgery=True,
    )
    result = evaluate_policy_rules(info)

    # 1. STAR-PREMIER-MODERN-014 prioritized
    assert "STAR-PREMIER-MODERN-014" in result.relevant_clause_ids
    assert result.relevant_clause_ids[0] == "STAR-PREMIER-MODERN-014"

    # 2. Modern treatment limit calculation
    calc = next(c for c in result.calculations if c.type == "modern_treatment_limit")
    assert calc.result == 500_000.0  # 50% of ₹10,00,000
    assert calc.illustrative_only is False

    # 3. Section II Coverage 14 finding
    assert any("Section II, Coverage 14 – Coverage for Modern Treatment" in f for f in result.findings)

    # 4. No generic room-rent excess warning
    assert not any("exceeds your confirmed eligible limit" in w for w in result.warnings)

    # 5. Hindi advisory explains 50% robotic coverage
    hindi = compose_hindi_advisory_text(info, result)
    assert "Coverage 14" in hindi
    assert "रोबोटिक सर्जरी" in hindi
    assert "50%" in hindi
    assert "500,000" in hindi or "5 लाख" in hindi


# --- TEST 8: Robotic Surgery with Missing SI ---
def test_regression_8_robotic_surgery_missing_si():
    """Issue 4: Robotic surgery with missing SI uses illustrative 50% of ₹10 Lakh default."""
    info = ExtractedInsuranceInfo(
        user_question="What is the coverage for robotic surgery?",
        treatment_type="Robotic knee arthroplasty",
        sum_insured=None,
        primary_intent="modern_treatment_robotic",
        is_robotic_surgery=True,
    )
    result = evaluate_policy_rules(info)

    calc = next(c for c in result.calculations if c.type == "modern_treatment_limit")
    assert calc.result == 500_000.0
    assert calc.illustrative_only is True
    assert any("sum_insured" in m for m in result.missing_information)

    hindi = compose_hindi_advisory_text(info, result)
    assert "रोबोटिक सर्जरी" in hindi
    assert "50%" in hindi


# --- TEST 9: Room Rent with ICU Charges ---
def test_regression_9_room_rent_with_icu_charges():
    """Issue 5: ICU charges are protected from proportionate deduction."""
    info = ExtractedInsuranceInfo(
        primary_intent="proportionate_deduction",
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=30_000.0,
        hospital_differential_billing=True,
        icu_charges=50_000.0,
        user_question="Room rent ₹30,000 and ICU charges ₹50,000",
    )
    result = evaluate_policy_rules(info)

    # 1. ICU Exemption finding
    assert any("ICU / ICCU Exemption" in f for f in result.findings)
    # 2. Excluded expenses list contains ICU charges
    assert any("Intensive Care Unit (ICU / ICCU) charges" in e for e in result.excluded_expenses)

    hindi = compose_hindi_advisory_text(info, result)
    assert "आईसीयू (ICU) शुल्क पर कोई आनुपातिक कटौती लागू नहीं होगी" in hindi


# --- TEST 10: Combined Robotic Surgery and Room-Rent Question ---
def test_regression_10_combined_robotic_surgery_and_room_rent():
    """Issue 6: Combined robotic surgery and room-rent query evaluates both without cross-interference."""
    info = ExtractedInsuranceInfo(
        treatment_type="Robotic prostatectomy",
        selected_room_rent_per_day=30_000.0,
        sum_insured=1_000_000.0,
        hospital_differential_billing=True,
        primary_intent="modern_treatment_robotic",
        identified_intents=["modern_treatment_robotic", "room_rent_eligibility", "proportionate_deduction"],
        is_robotic_surgery=True,
    )
    result = evaluate_policy_rules(info)

    # 1. Both clauses present
    assert "STAR-PREMIER-MODERN-014" in result.relevant_clause_ids
    assert "STAR-PREMIER-ROOM-001" in result.relevant_clause_ids

    # 2. Both calculations present
    types = [c.type for c in result.calculations]
    assert "modern_treatment_limit" in types
    assert "room_rent_eligibility" in types

    # 3. Room rent excess warning present
    assert any("exceeds your confirmed eligible limit of ₹10,000.00/day by ₹20,000.00/day" in w for w in result.warnings)

    # 4. Spoken Hindi explains BOTH
    hindi = compose_hindi_advisory_text(info, result)
    assert "रोबोटिक सर्जरी" in hindi
    assert "कमरे के किराए" in hindi
    assert "30,000" in hindi

