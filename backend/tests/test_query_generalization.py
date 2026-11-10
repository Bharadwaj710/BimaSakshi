"""
Comprehensive Query Generalization, Intent-Aware Decomposition & Policy Rule Tests
-----------------------------------------------------------------------------------
Validates BimaSakshi's general-purpose insurance query understanding system:
1. Dynamic multi-intent decomposition and entity preservation.
2. 6 Core Regression Scenarios (Accident, Multi-intent, Missing sum insured, etc.).
3. 13 Unseen Test Variations (Cataract, Joint Replacement, Maternity, Day-Care, High SI Cap, etc.).
4. Multi-query ChromaDB retrieval precision & distance fusion.
"""

import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.analysis import ExtractedInsuranceInfo, UnitAmountItem
from services.policy_engine import evaluate_policy_rules, ROOM_RENT_MAX_CAP
from services.response_service import compose_hindi_advisory_text
from vectorstore import retrieve_policy_clauses_multi, get_collection


# ==============================================================================
# SECTION 1: REGRESSION SCENARIOS (6 CORE SCENARIOS)
# ==============================================================================

def test_regression_1_multi_intent_room_rent_and_kidney_calculi():
    """
    Regression 1: Authentic Hinglish transcript with BOTH room rent & kidney calculi waiting period.
    - Age 52, Sum Insured ₹10L, Tenure 14mo, Room Rent ₹30k/day, Differential Billing True.
    - Evaluates room rent excess (₹30k > ₹10k).
    - Evaluates differential billing proportionate deduction.
    - Evaluates Code Excl 02 24-month waiting period (10mo remaining).
    - Spoken Hindi response addresses BOTH intents.
    """
    info = ExtractedInsuranceInfo(
        age=52,
        sum_insured=1_000_000.0,
        policy_tenure_months=14,
        diagnosis_or_condition="kidney stone",
        treatment_type="surgery",
        selected_room_rent_per_day=30_000.0,
        hospital_differential_billing=True,
        primary_intent="proportionate_deduction",
        identified_intents=["room_rent_eligibility", "proportionate_deduction", "waiting_period_specified_disease"],
        retrieval_queries=[
            "Star Health Premier proportionate deduction room rent differential billing",
            "Star Health Premier Code Excl 02 24 months waiting period kidney stone surgery",
        ],
        units_and_amounts=[
            UnitAmountItem(parameter="age", stated_value="52 years"),
            UnitAmountItem(parameter="sum_insured", stated_value="10,00,000 INR"),
            UnitAmountItem(parameter="policy_tenure", stated_value="14 months"),
            UnitAmountItem(parameter="room_rent", stated_value="30,000 per day"),
        ],
    )
    result = evaluate_policy_rules(info, retrieved_clause_ids=["STAR-PREMIER-ROOM-001", "STAR-PREMIER-WAIT-002"])

    # 1. Calculation checks
    room_calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert room_calc.result == 10000.0
    assert room_calc.illustrative_only is False

    # 2. Warnings must contain both Room Rent excess and Waiting period
    assert any("exceeds your confirmed eligible limit of ₹10,000.00/day by ₹20,000.00/day" in w for w in result.warnings)
    assert any("Hospital follows differential billing and room rent exceeds eligibility" in w for w in result.warnings)
    assert any("24-month waiting period under Code Excl 02" in w for w in result.warnings)
    assert any("10 months remaining" in w for w in result.warnings)

    # 3. Both clauses present
    assert "STAR-PREMIER-ROOM-001" in result.relevant_clause_ids
    assert "STAR-PREMIER-WAIT-002" in result.relevant_clause_ids

    # 4. Spoken Hindi explains BOTH room rent & waiting period
    hindi = compose_hindi_advisory_text(info, result)
    assert "पात्र किराया 10,000 रुपये प्रतिदिन" in hindi
    assert "चुना गया किराया 30,000 रुपये" in hindi
    assert "आनुपातिक कटौती" in hindi
    assert "किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है" in hindi
    assert "14 महीने" in hindi


def test_regression_2_accident_exception_inquiry():
    """Regression 2: Accident exception waiver under Code Excl 02."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        treatment_type="Emergency surgery required because of a road accident",
        is_accident_related=True,
        accident_causal_relationship="clear",
        policy_tenure_months=6,
    )
    result = evaluate_policy_rules(info)

    assert any("Code Excl 02 Accident Exception" in f for f in result.findings)
    assert not any("waiting period under Code Excl 02" in w for w in result.warnings)
    hindi = compose_hindi_advisory_text(info, result)
    assert "दुर्घटना (accident)" in hindi
    assert "24 महीने का वेटिंग पीरियड लागू नहीं होता" in hindi


def test_regression_3_kidney_stone_only_inquiry():
    """Regression 3: Kidney stone surgery without room rent inquiry."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_specified_disease",
        diagnosis_or_condition="Kidney stone",
        policy_tenure_months=14,
    )
    result = evaluate_policy_rules(info)

    assert any("10 months remaining" in w for w in result.warnings)
    assert not any("exceeds your confirmed eligible limit" in w for w in result.warnings)
    hindi = compose_hindi_advisory_text(info, result)
    assert "किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है" in hindi
    assert "पात्र कमरा किराया" not in hindi


def test_regression_4_room_rent_only_inquiry():
    """Regression 4: Room rent inquiry with confirmed sum insured."""
    info = ExtractedInsuranceInfo(
        primary_intent="room_rent_eligibility",
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15_000.0,
        hospital_differential_billing=True,
    )
    result = evaluate_policy_rules(info)

    calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert calc.result == 10000.0
    assert any("exceeds your confirmed eligible limit of ₹10,000.00/day by ₹5,000.00/day" in w for w in result.warnings)
    hindi = compose_hindi_advisory_text(info, result)
    assert "पात्र किराया 10,000 रुपये" in hindi
    assert "15,000 रुपये" in hindi


def test_regression_5_missing_sum_insured_inquiry():
    """Regression 5: Room rent inquiry where sum insured is absent."""
    info = ExtractedInsuranceInfo(
        primary_intent="room_rent_eligibility",
        sum_insured=None,
        selected_room_rent_per_day=15_000.0,
    )
    result = evaluate_policy_rules(info)

    assert info.sum_insured is None
    calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert calc.illustrative_only is True
    # No personalized warning claiming user exceeded their limit
    assert not any("exceeds your confirmed eligible limit" in w for w in result.warnings)
    assert any("sum_insured" in m for m in result.missing_information)


def test_regression_6_missing_differential_billing_inquiry():
    """Regression 6: Room exceeds limit but differential billing status is unconfirmed."""
    info = ExtractedInsuranceInfo(
        primary_intent="proportionate_deduction",
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=15_000.0,
        hospital_differential_billing=None,
    )
    result = evaluate_policy_rules(info)

    assert any("insufficient_information: Hospital differential-billing status is unconfirmed" in f for f in result.findings)
    assert any("Proportionate deduction is conditional" in w for w in result.warnings)
    assert any("hospital_differential_billing" in m for m in result.missing_information)


# ==============================================================================
# SECTION 2: UNSEEN GENERALIZATION TEST VARIATIONS (13 VARIATIONS)
# ==============================================================================

def test_variation_7_cataract_surgery_inquiry():
    """Variation 7: Cataract surgery under Code Excl 02 (24-month waiting period)."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="cataract",
        treatment_type="phacoemulsification eye surgery",
        policy_tenure_months=8,
        user_question="Is my cataract surgery covered?",
    )
    result = evaluate_policy_rules(info)
    # Diagnosis noted and checked
    assert any("Diagnosis/condition noted: 'cataract'" in f for f in result.findings)


def test_variation_8_joint_replacement_surgery_inquiry():
    """Variation 8: Joint replacement surgery under specified disease exclusion."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="osteoarthritis knee",
        treatment_type="total knee replacement",
        policy_tenure_months=12,
        user_question="Does 24-month waiting period apply to knee replacement?",
    )
    result = evaluate_policy_rules(info)
    assert any("Diagnosis/condition noted: 'osteoarthritis knee'" in f for f in result.findings)


def test_variation_9_pre_existing_diabetes_inquiry():
    """Variation 9: Declared pre-existing diabetes with 15 months tenure."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_ped",
        diagnosis_or_condition="Type 2 Diabetes Mellitus",
        declared_ped=True,
        policy_tenure_months=15,
    )
    result = evaluate_policy_rules(info)
    assert "STAR-PREMIER-PED-001" in result.relevant_clause_ids
    assert any("Declared pre-existing condition is subject to a 24-month waiting period under Code Excl 01" in w for w in result.warnings)
    assert any("9 months remaining" in w for w in result.warnings)


def test_variation_10_unindexed_maternity_inquiry():
    """Variation 10: Maternity and normal delivery query -> flags insufficient_information."""
    info = ExtractedInsuranceInfo(
        user_question="Does Star Health Premier cover maternity and normal delivery charges?",
        diagnosis_or_condition="maternity pregnancy",
        treatment_type="normal delivery",
        identified_intents=["maternity_coverage"],
    )
    result = evaluate_policy_rules(info)
    assert any("insufficient_information: Maternity and pregnancy/childbirth coverage is not indexed" in f for f in result.findings)
    assert any("unindexed_benefit_clause" in m for m in result.missing_information)
    hindi = compose_hindi_advisory_text(info, result)
    assert "वर्तमान डेमो डेटाबेस में अनुक्रमित नहीं है" in hindi


def test_variation_11_unindexed_daycare_procedure_inquiry():
    """Variation 11: Day-care procedure inquiry -> flags insufficient_information."""
    info = ExtractedInsuranceInfo(
        user_question="Is day_care procedure covered without 24 hours hospitalization?",
        treatment_type="day_care surgery",
    )
    result = evaluate_policy_rules(info)
    assert any("insufficient_information: Day-care procedures" in f for f in result.findings)
    assert any("unindexed_benefit_clause" in m for m in result.missing_information)


def test_variation_12_co_payment_percentage_inquiry():
    """Variation 12: Co-payment percentage declared explicitly."""
    info = ExtractedInsuranceInfo(
        primary_intent="co_payment",
        co_payment_percentage=20.0,
        sum_insured=1_000_000.0,
        selected_room_rent_per_day=8_000.0,
    )
    result = evaluate_policy_rules(info)
    assert any("Applicable co-payment of 20.0% declared" in f for f in result.findings)


def test_variation_13_high_sum_insured_25_lakh_cap_enforcement():
    """
    Variation 13: ₹25 Lakh Sum Insured.
    1% of ₹25L is ₹25,000/day, but policy cap is ₹20,000/day!
    If room rent is ₹22,000/day, it exceeds eligible limit by ₹2,000/day.
    """
    info = ExtractedInsuranceInfo(
        primary_intent="room_rent_eligibility",
        sum_insured=2_500_000.0,
        selected_room_rent_per_day=22_000.0,
    )
    result = evaluate_policy_rules(info)
    calc = next(c for c in result.calculations if c.type == "room_rent_eligibility")
    assert calc.result == ROOM_RENT_MAX_CAP  # Exactly ₹20,000.0 cap!
    assert any("exceeds your confirmed eligible limit of ₹20,000.00/day by ₹2,000.00/day" in w for w in result.warnings)


def test_variation_14_road_accident_trauma_with_mlc():
    """Variation 14: Accidental trauma with explicit causation."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_accident",
        diagnosis_or_condition="Accidental femur fracture resulting from road collision",
        treatment_type="Open reduction internal fixation",
        is_accident_related=True,
        accident_causal_relationship="clear",
        policy_tenure_months=2,
    )
    result = evaluate_policy_rules(info)
    assert any("Code Excl 02 Accident Exception" in f for f in result.findings)
    assert not any("waiting period under Code Excl 02" in w for w in result.warnings)


def test_variation_15_unclear_accident_causality_with_elective_surgery():
    """Variation 15: Minor accident mentioned, but treatment is elective gall bladder surgery."""
    info = ExtractedInsuranceInfo(
        diagnosis_or_condition="Gall bladder cholelithiasis",
        treatment_type="Laparoscopic cholecystectomy",
        user_question="I had an accident last month, can I get my gall bladder removed now?",
        is_accident_related=True,
        accident_causal_relationship="unclear",
        policy_tenure_months=10,
    )
    result = evaluate_policy_rules(info)
    assert any("insufficient_information: An accident was mentioned, but the direct causal relationship" in f for f in result.findings)
    assert any("accident_causal_documentation" in m for m in result.missing_information)


def test_variation_16_unindexed_pre_post_hospitalization_inquiry():
    """Variation 16: Pre and post-hospitalization inquiry -> flags insufficient_information."""
    info = ExtractedInsuranceInfo(
        user_question="Are pre-hospitalization and post-hospitalization bills reimbursed?",
        identified_intents=["pre_post_hospitalization"],
    )
    result = evaluate_policy_rules(info)
    assert any("insufficient_information: Pre-hospitalization and post-hospitalization medical expenses is not indexed" in f for f in result.findings)


def test_variation_17_unindexed_dental_treatment_inquiry():
    """Variation 17: Dental treatment inquiry -> flags insufficient_information."""
    info = ExtractedInsuranceInfo(
        user_question="Is dental root canal surgery covered?",
        treatment_type="dental extraction",
        identified_intents=["dental_coverage"],
    )
    result = evaluate_policy_rules(info)
    assert any("insufficient_information: Dental examination, treatment and oral surgery is not indexed" in f for f in result.findings)


def test_variation_18_unindexed_ayush_inpatient_inquiry():
    """Variation 18: AYUSH hospitalization inquiry -> flags insufficient_information."""
    info = ExtractedInsuranceInfo(
        user_question="Does the policy cover ayurveda treatment in an ayush hospital?",
        treatment_type="ayurvedic therapy",
        identified_intents=["ayush_coverage"],
    )
    result = evaluate_policy_rules(info)
    assert any("insufficient_information: AYUSH" in f for f in result.findings)


def test_variation_19_continuity_credit_under_portability():
    """Variation 19: Continuity of coverage portability credit."""
    info = ExtractedInsuranceInfo(
        primary_intent="waiting_period_specified_disease",
        diagnosis_or_condition="Kidney stone",
        continuity_of_coverage=True,
        policy_tenure_months=14,
    )
    result = evaluate_policy_rules(info)
    assert any("Portability / Continuity Credit" in f for f in result.findings)


# ==============================================================================
# SECTION 3: CHROMADB RETRIEVAL DISTANCE PRECISION (DECOMPOSED VS MONOLITHIC)
# ==============================================================================

def test_chromadb_multi_query_retrieval_distance_improvement():
    """
    Validates that decomposing multi-intent questions into targeted queries
    significantly improves retrieval distance compared to a monolithic query.
    """
    collection = get_collection()

    # Monolithic concatenated query
    monolithic_query = (
        "Star Health Premier Code Excl 02 24 months waiting period kidney calculi surgery "
        "proportionate deduction room rent differential billing"
    )
    mono_res = collection.query(query_texts=[monolithic_query], n_results=3)
    mono_ids = mono_res["ids"][0]
    mono_distances = dict(zip(mono_ids, mono_res["distances"][0]))

    # Decomposed queries
    decomposed_room_query = (
        "Star Health Premier Room Rent and Associated Medical Expenses Limit 1 percent sum insured "
        "proportionate deduction differential billing"
    )
    decomposed_wait_query = (
        "Star Health Premier Code Excl 02 24 consecutive months continuous coverage waiting period "
        "kidney calculi surgery"
    )

    room_res = collection.query(query_texts=[decomposed_room_query], n_results=1)
    wait_res = collection.query(query_texts=[decomposed_wait_query], n_results=1)

    decomp_room_dist = room_res["distances"][0][0]
    decomp_wait_dist = wait_res["distances"][0][0]

    # Decomposed query achieves substantially better (lower) distance for room rent clause
    assert decomp_room_dist < mono_distances["STAR-PREMIER-ROOM-001"]

    # Multi-query fusion retrieves both clauses with minimum distance
    multi_results = retrieve_policy_clauses_multi(
        queries=[decomposed_room_query, decomposed_wait_query],
        top_k=2,
    )
    retrieved_clause_ids = [r["clause_id"] for r in multi_results]
    assert "STAR-PREMIER-ROOM-001" in retrieved_clause_ids
    assert "STAR-PREMIER-WAIT-002" in retrieved_clause_ids
