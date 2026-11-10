"""
Unit Tests for Deterministic Policy Rule Engine (Phase 3 - Refined)
--------------------------------------------------------------------
Covers all 10 required rule-engine and advisory scenarios:
1. Missing sum insured.
2. Explicit ₹10 lakh sum insured.
3. Illustrative-only room-rent calculation.
4. No personalised warning from assumed inputs.
5. Differential billing true.
6. Differential billing false.
7. Differential billing unknown.
8. Consistency between JSON warnings and Hindi spoken advisory.
9. Waiting-period assessment with portability credit.
10. Accident exception.
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


# --- 1. Missing Sum Insured ---

def test_missing_sum_insured_retains_null_and_flags_missing():
    """1. Missing sum insured: retains null in extracted_info and flags missing confirmation."""
    info = ExtractedInsuranceInfo(
        sum_insured=None,
        selected_room_rent_per_day=15000.0,
    )
    result = evaluate_policy_rules(info)
    assert info.sum_insured is None
    assert any("sum_insured" in m for m in result.missing_information)


# --- 2. Explicit ₹10 Lakh Sum Insured ---

def test_explicit_10_lakh_sum_insured():
    """2. Explicit ₹10 Lakh sum insured sets confirmed entitlement of ₹10,000/day."""
    info = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
    )
    result = evaluate_policy_rules(info)
    calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert calc.result == 10000.0
    assert calc.illustrative_only is False
    assert any("Confirmed Sum Insured: ₹1,000,000.00" in f for f in result.findings)
    assert any("exceeds your confirmed eligible limit" in w for w in result.warnings)


# --- 3. Illustrative-Only Room-Rent Calculation ---

def test_illustrative_only_room_rent_calculation():
    """3. Assumed baseline is marked illustrative_only=True and labeled illustrative in explanation."""
    info = ExtractedInsuranceInfo(
        sum_insured=None,
        selected_room_rent_per_day=15000.0,
    )
    result = evaluate_policy_rules(info)
    calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert calc.illustrative_only is True
    assert calc.result == 10000.0
    assert "Illustrative Demonstration Only" in calc.explanation


# --- 4. No Personalised Warning from Assumed Inputs ---

def test_no_personalised_warning_from_assumed_inputs():
    """4. No personalised room-rent excess warning is generated when sum insured is unconfirmed."""
    info = ExtractedInsuranceInfo(
        sum_insured=None,
        selected_room_rent_per_day=15000.0,
    )
    result = evaluate_policy_rules(info)
    # Must NOT generate a personalised warning that user's room exceeds eligibility
    assert not any("exceeds your confirmed eligible limit" in w for w in result.warnings)
    # Must clearly state that actual entitlement is unconfirmed
    assert any("Because the actual policy sum insured is unconfirmed" in f for f in result.findings)


# --- 5. Differential Billing True ---

def test_differential_billing_true():
    """5. Differential billing true: evaluates proportionate deduction when associated expenses present."""
    info = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
        associated_medical_expenses=60000.0,
        hospital_differential_billing=True,
    )
    result = evaluate_policy_rules(info)
    prop_calc = next((c for c in result.calculations if c.type == "proportionate_deduction"), None)
    assert prop_calc is not None
    # 60,000 * (1 - 10,000/15,000) = 20,000
    assert prop_calc.result == 20000.0
    assert any("Proportionate deduction of ₹20,000.00 will apply" in w for w in result.warnings)


# --- 6. Differential Billing False ---

def test_differential_billing_false():
    """6. Differential billing false: proportionate deduction is NOT applied."""
    info = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=18000.0,
        associated_medical_expenses=60000.0,
        hospital_differential_billing=False,
    )
    result = evaluate_policy_rules(info)
    assert not any(c.type == "proportionate_deduction" for c in result.calculations)
    assert any("proportionate deductions are NOT applied" in f for f in result.findings)


# --- 7. Differential Billing Unknown (Null) ---

def test_differential_billing_unknown():
    """7. Differential billing null: returns insufficient_information; never says deduction will apply."""
    info = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
        associated_medical_expenses=60000.0,
        hospital_differential_billing=None,
    )
    result = evaluate_policy_rules(info)
    # Must NOT calculate a definitive proportionate deduction
    assert not any(c.type == "proportionate_deduction" for c in result.calculations)
    # Must return insufficient_information
    assert any("insufficient_information: Hospital differential-billing status is unconfirmed" in f for f in result.findings)
    # Must NOT claim deduction will apply
    assert not any("will apply to Associated Medical Expenses" in w for w in result.warnings)
    assert any("Proportionate deduction is conditional" in w for w in result.warnings)


# --- 8. Consistency Between JSON Warnings and Hindi Spoken Advisory ---

def test_consistency_between_json_warnings_and_hindi_spoken_advisory():
    """8. Hindi advisory must communicate the exact same conclusion as JSON warnings."""
    # Scenario A: Differential billing unknown -> Advisory must NOT claim deduction will apply
    info_unknown = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
        hospital_differential_billing=None,
    )
    res_unknown = evaluate_policy_rules(info_unknown)
    advisory_unknown = compose_hindi_advisory_text(info_unknown, res_unknown)
    assert "आनुपातिक कटौती लागू नहीं होगी" in advisory_unknown
    assert "लागू होगी" not in advisory_unknown.split("यदि अस्पताल")[0]  # No unconditional claim

    # Scenario B: Differential billing confirmed True -> Advisory mentions deduction
    info_true = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
        associated_medical_expenses=60000.0,
        hospital_differential_billing=True,
    )
    res_true = evaluate_policy_rules(info_true)
    advisory_true = compose_hindi_advisory_text(info_true, res_true)
    assert "20,000 रुपये की आनुपातिक कटौती लागू होगी" in advisory_true


# --- 9. Waiting-Period Assessment with Portability Credit ---

def test_waiting_period_assessment_with_portability_credit():
    """9. Portability credit: continuous prior coverage is recognized toward Code Excl 02."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="Kidney calculi",
        policy_tenure_months=14,
        continuity_of_coverage=True,
    )
    result = evaluate_policy_rules(info)
    assert any("Portability / Continuity Credit" in f for f in result.findings)
    # Wording must be conditional, not guaranteed claim rejection
    assert any("Coverage under this clause is conditional" in w for w in result.warnings)
    assert not any("Claim will be rejected" in w for w in result.warnings)


# --- 10. Accident Exception ---

def test_waiting_period_accident_exception():
    """10. Accident exception: 24-month waiting period does not apply to accidental injury."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="Kidney trauma from an accidental fall",
        treatment_type="Emergency accident surgery",
        policy_tenure_months=6,
    )
    result = evaluate_policy_rules(info)
    assert any("Accident Exception" in f for f in result.findings)
    assert any("does NOT apply to claims arising due to an accident" in f for f in result.findings)
    assert not any("18 months remaining" in w for w in result.warnings)


# --- Additional Preserved Policy Engine Tests ---

def test_room_rent_eligibility_cap_20000():
    """Sum insured = 25 Lakh (1% = 25,000) -> Capped at ₹20,000/day per policy."""
    info = ExtractedInsuranceInfo(
        sum_insured=2_500_000.0,
        selected_room_rent_per_day=22000.0,
    )
    result = evaluate_policy_rules(info)
    calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert calc.result == 20000.0
    assert any("exceeds your confirmed eligible limit of ₹20,000.00" in w for w in result.warnings)


def test_pharmacy_and_diagnostic_exclusion():
    """Pharmacy, consumables, diagnostics, and implants are excluded from associated expenses."""
    info = ExtractedInsuranceInfo(
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15000.0,
        associated_medical_expenses=50000.0,
        pharmacy_expenses=20000.0,
        diagnostic_expenses=10000.0,
        hospital_differential_billing=True,
    )
    result = evaluate_policy_rules(info)
    assert any("Pharmacy & Consumables" in e for e in result.excluded_expenses)
    assert any("Diagnostics" in e for e in result.excluded_expenses)
    prop_calc = next(c for c in result.calculations if c.type == "proportionate_deduction")
    assert prop_calc.inputs["associated_medical_expenses"] == 50000.0


def test_unknown_copayment_never_inferred_from_age():
    """Age 65 without stated co-pay must NOT infer a co-payment percentage."""
    info = ExtractedInsuranceInfo(
        age=65,
        sum_insured=1_000_000.0,
        co_payment_percentage=None,
    )
    result = evaluate_policy_rules(info)
    assert any("co_payment_percentage" in m for m in result.missing_information)
    assert not any(c.type == "copayment" for c in result.calculations)


def test_invalid_negative_or_zero_values_handled_safely():
    """Zero or negative room rent handled safely without crash or divide-by-zero."""
    info = ExtractedInsuranceInfo(
        sum_insured=0.0,
        selected_room_rent_per_day=0.0,
        associated_medical_expenses=0.0,
    )
    result = evaluate_policy_rules(info)
    assert result is not None
    assert len(result.calculations) > 0
