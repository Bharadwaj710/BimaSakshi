"""
Test Suite: Final Production-Readiness Audit – 10 Unseen Hindi/Hinglish Scenarios
==================================================================================
Comprehensive end-to-end verification covering:
1. Exact prompt scenario (24-yr old, calculi, ₹30k deposit, benefits inquiry).
2. Deposit with mature tenure (36m) and partial cashless reconciliation (no full refund guarantee).
3. 24-year-old dependent child vs 50-75 yr Premier primary entry age ambiguity.
4. Modern treatment / Robotic surgery (Coverage 14: 50% SI) + room rent excess + deposit.
5. Accident trauma + kidney injury + hospital deposit + emergency ICU safeguard.
6. Declared & accepted PED vs unconfirmed acceptance with 14-month tenure (Code Excl 01).
7. Day care lithotripsy (<24 hr) + portability continuity credit from prior 30-month coverage.
8. Room rent proportionate deduction: differential billing vs uniform billing.
9. Ambiguous generic kidney condition + benefits inquiry (no auto-mapping to calculi).
10. Unindexed/excluded feature inquiry (maternity/cosmetic) alongside hospital deposit.
"""

import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.analysis import ExtractedInsuranceInfo, UnitAmountItem
from services.policy_engine import evaluate_policy_rules
from services.response_service import compose_hindi_advisory_text
from vectorstore import retrieve_policy_clauses_multi


# ==============================================================================
# SCENARIO 1: Exact Prompt Scenario (24yr old, Kidney Calculi, ₹30k Deposit, Benefits)
# ==============================================================================
def test_scenario_1_exact_prompt_kidney_stone_deposit_benefits():
    """
    Scenario 1: 24-year-old user, kidney calculi surgery, Star Health,
    ₹30,000 hospital deposit requested, asks what benefits policy provides.
    """
    info = ExtractedInsuranceInfo(
        age=24,
        diagnosis_or_condition="kidney calculi",
        treatment_type="kidney stone surgery",
        insurer_mentioned="Star Health",
        hospital_deposit=30000.0,
        selected_room_rent_per_day=None,
        sum_insured=None,
        policy_tenure_months=None,
        membership_status=None,
        primary_intent="benefits_inquiry",
        identified_intents=[
            "benefits_inquiry",
            "hospital_deposit_inquiry",
            "waiting_period_specified_disease",
            "age_eligibility_inquiry",
        ],
        retrieval_queries=[
            "Star Health Premier Section B Coverage 1 In-Patient Hospitalization benefits",
            "Star Health Premier Code Excl 02 24 months waiting period kidney calculi",
        ],
        user_question="मुझे किडनी स्टोन सर्जरी करवानी है और अस्पताल ₹30,000 डिपॉजिट मांग रहा है, मेरी पॉलिसी में क्या बेनिफिट्स मिलेंगे?",
    )

    # 1. Unconfirmed values remain None (no fabrication)
    assert info.hospital_deposit == 30000.0
    assert info.selected_room_rent_per_day is None
    assert info.sum_insured is None
    assert info.policy_tenure_months is None
    assert info.membership_status is None

    clauses = retrieve_policy_clauses_multi(info.retrieval_queries, top_k=3)
    clause_ids = [c["clause_id"] for c in clauses]
    assert "STAR-PREMIER-ROOM-001" in clause_ids
    assert "STAR-PREMIER-WAIT-002" in clause_ids

    analysis = evaluate_policy_rules(info, clause_ids)

    # 2. Benefits summary present with evidence
    benefits = [f for f in analysis.findings if "In-Patient Hospitalization Benefits" in f]
    assert len(benefits) > 0
    assert "1% of Sum Insured" in benefits[0]
    assert "Surgeon, Anesthetist" in benefits[0]

    # 3. Hospital deposit explained without full refund guarantee
    deposits = [f for f in analysis.findings if "Hospital Advance Admission Deposit" in f]
    assert len(deposits) > 0
    assert "₹30,000.00" in deposits[0]
    assert "a full refund is never guaranteed" in deposits[0]

    # 4. Age ambiguity for 24-year-old
    ages = [f for f in analysis.findings if "Age Eligibility & Membership Status" in f]
    assert len(ages) > 0
    assert "24" in ages[0]
    assert "dependent child" in ages[0]
    assert "primary insured" in ages[0]

    # 5. Missing fields flagged
    assert any("sum_insured" in m for m in analysis.missing_information)
    assert any("policy_tenure_months" in m for m in analysis.missing_information)

    # 6. Hindi text verification
    hindi = compose_hindi_advisory_text(info, analysis)
    assert "₹30,000" in hindi or "30,000" in hindi
    assert "अग्रिम सुरक्षा राशि" in hindi
    assert "पूर्ण रिफंड की अग्रिम गारंटी नहीं होती" in hindi or "कोई गारंटी नहीं होती" in hindi or "गारंटी नहीं" in hindi
    assert "24 महीने का वेटिंग पीरियड" in hindi


# ==============================================================================
# SCENARIO 2: Mature Tenure (36m) + Gall Bladder Calculi + ₹20k Deposit
# ==============================================================================
def test_scenario_2_mature_tenure_deposit_reconciliation():
    """
    Scenario 2: 55-year-old, 36 months tenure, gall bladder calculi,
    hospital asks ₹20,000 deposit. Waiting period is satisfied.
    """
    info = ExtractedInsuranceInfo(
        age=55,
        diagnosis_or_condition="gall bladder calculi",
        treatment_type="cholecystectomy",
        insurer_mentioned="Star Health",
        hospital_deposit=20000.0,
        selected_room_rent_per_day=None,
        sum_insured=1000000.0,
        policy_tenure_months=36,
        membership_status="primary_insured",
        primary_intent="hospital_deposit_inquiry",
        identified_intents=["hospital_deposit_inquiry", "waiting_period_specified_disease"],
        retrieval_queries=["Star Health Premier Code Excl 02 gall bladder calculi waiting period"],
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-WAIT-002"])

    # 36 months satisfies 24-month waiting period
    assert any("satisfies the 24-month continuous coverage requirement" in f for f in analysis.findings)
    assert not any("Waiting period active" in w for w in analysis.warnings)

    # Deposit finding confirms advance deposit and no guarantee of full refund
    dep_findings = [f for f in analysis.findings if "Hospital Advance Admission Deposit" in f]
    assert len(dep_findings) > 0
    assert "₹20,000.00" in dep_findings[0]
    assert "a full refund is never guaranteed" in dep_findings[0]

    hindi = compose_hindi_advisory_text(info, analysis)
    assert "₹20,000" in hindi or "20,000" in hindi
    assert "अग्रिम सुरक्षा राशि" in hindi


# ==============================================================================
# SCENARIO 3: 21-Year-Old Dependent Child vs Premier Proposer Entry Age
# ==============================================================================
def test_scenario_3_young_adult_dependent_child_eligibility():
    """
    Scenario 3: 21-year-old university student, bilateral inguinal hernia surgery,
    covered under father's Star Premier policy.
    """
    info = ExtractedInsuranceInfo(
        age=21,
        diagnosis_or_condition="bilateral inguinal hernia",
        treatment_type="hernioplasty",
        insurer_mentioned="Star Health",
        hospital_deposit=None,
        selected_room_rent_per_day=None,
        sum_insured=None,
        policy_tenure_months=None,
        membership_status=None,
        primary_intent="age_eligibility_inquiry",
        identified_intents=["age_eligibility_inquiry", "waiting_period_specified_disease"],
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-WAIT-002"])

    # Age rule triggers for 21-year-old
    age_findings = [f for f in analysis.findings if "Age Eligibility & Membership Status" in f]
    assert len(age_findings) > 0
    assert "21" in age_findings[0]
    assert "50 to 75 years" in age_findings[0]
    assert "dependent children are covered up to age 25" in age_findings[0]

    # Missing information demands membership status and sum insured
    assert any("membership_status" in m for m in analysis.missing_information)
    assert any("sum_insured" in m for m in analysis.missing_information)


# ==============================================================================
# SCENARIO 4: Modern Treatment (Coverage 14) + Room Rent Excess + Deposit
# ==============================================================================
def test_scenario_4_modern_robotic_treatment_differential_billing_deposit():
    """
    Scenario 4: 62-year-old, robotic partial nephrectomy, ₹10 Lakh sum insured,
    room rent ₹25,000/day (differential billing), hospital deposit ₹50,000.
    """
    info = ExtractedInsuranceInfo(
        age=62,
        diagnosis_or_condition="renal mass",
        treatment_type="robotic partial nephrectomy",
        is_robotic_surgery=True,
        selected_room_rent_per_day=25000.0,
        hospital_deposit=50000.0,
        sum_insured=1000000.0,
        policy_tenure_months=30,
        hospital_differential_billing=True,
        primary_intent="room_rent_eligibility",
        identified_intents=["room_rent_eligibility", "hospital_deposit_inquiry"],
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-ROOM-001", "STAR-PREMIER-MODERN-014"])

    # Modern Treatment Coverage 14: 50% limit of ₹10 Lakh = ₹5,00,000
    modern_calcs = [c for c in analysis.calculations if c.type == "modern_treatment_limit"]
    assert len(modern_calcs) > 0
    assert modern_calcs[0].result == 500000.0
    assert modern_calcs[0].illustrative_only is False

    # Room rent limit is 1% of 10L = 10,000; 25,000 exceeds by 15,000
    assert any("exceeds your confirmed eligible limit of ₹10,000.00/day by ₹15,000.00/day" in w for w in analysis.warnings)

    # Proportionate deduction applies under differential billing
    assert any("Proportionate deduction will apply" in w for w in analysis.warnings)

    # Hospital deposit is ₹50,000 and distinctly preserved
    assert any("Hospital Advance Admission Deposit (₹50,000.00)" in f for f in analysis.findings)

    hindi = compose_hindi_advisory_text(info, analysis)
    assert "₹50,000" in hindi or "50,000" in hindi
    assert "रोबोटिक" in hindi or "मॉडर्न ट्रीटमेंट" in hindi or "Coverage 14" in hindi


# ==============================================================================
# SCENARIO 5: Accident Trauma + Emergency Surgery + ICU + Deposit
# ==============================================================================
def test_scenario_5_accident_trauma_emergency_icu_deposit():
    """
    Scenario 5: 42-year-old motorcycle collision trauma, emergency kidney laceration repair,
    ₹40,000 deposit requested, ICU charges ₹45,000.
    """
    info = ExtractedInsuranceInfo(
        age=42,
        diagnosis_or_condition="traumatic kidney laceration",
        treatment_type="emergency nephrorrhaphy",
        is_accident=True,
        accident_caused_treatment=True,
        hospital_deposit=40000.0,
        selected_room_rent_per_day=None,
        icu_charges=45000.0,
        sum_insured=1500000.0,
        policy_tenure_months=6,  # Normally would be within 24m waiting period
        primary_intent="waiting_period_accident",
        identified_intents=["waiting_period_accident", "hospital_deposit_inquiry"],
        user_question="मोटरसाइकिल एक्सीडेंट के कारण इमरजेंसी सर्जरी और ICU में भर्ती होना पड़ा, अस्पताल ₹40,000 डिपॉजिट मांग रहा है",
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-WAIT-002", "STAR-PREMIER-ROOM-001"])

    # 1. Accident exception triggers: exempt from 24-month waiting period
    assert any("does NOT apply to claims arising due to an accident" in f for f in analysis.findings)
    assert not any("Waiting period active" in w for w in analysis.warnings)

    # 2. ICU safeguard: no proportionate deduction on ICU charges
    assert any("ICU / ICCU Exemption" in f for f in analysis.findings)

    # 3. Hospital deposit explained without guarantee of full refund
    assert any("Hospital Advance Admission Deposit (₹40,000.00)" in f for f in analysis.findings)

    hindi = compose_hindi_advisory_text(info, analysis)
    assert "दुर्घटना (accident)" in hindi
    assert "वेटिंग पीरियड लागू नहीं होता" in hindi
    assert "आईसीयू (ICU)" in hindi


# ==============================================================================
# SCENARIO 6: Declared Pre-Existing Disease (Code Excl 01) with 14 Months Tenure
# ==============================================================================
def test_scenario_6_declared_ped_waiting_period_unmatured():
    """
    Scenario 6: 52-year-old, pre-existing chronic renal disorder declared at application,
    tenure 14 months (<24 months), insurer acceptance unconfirmed.
    """
    info = ExtractedInsuranceInfo(
        age=52,
        diagnosis_or_condition="chronic renal disorder",
        treatment_type="medical management",
        sum_insured=1000000.0,
        policy_tenure_months=14,
        declared_ped=True,
        ped_accepted_by_insurer=None,  # Unconfirmed
        primary_intent="waiting_period_ped",
        identified_intents=["waiting_period_ped"],
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-PED-001"])

    # Code Excl 01 24-month PED waiting period applies
    assert any("Code Excl 01" in w for w in analysis.warnings)
    assert any("14 months" in w and "24-month waiting period" in w for w in analysis.warnings)

    # Insurer acceptance warning
    assert any("Insurer Acceptance Unconfirmed" in w for w in analysis.warnings)

    # Strictly distinguishes Code Excl 01 (PED) from Code Excl 02 (Specified disease)
    assert not any("Code Excl 02" in w for w in analysis.warnings)

    hindi = compose_hindi_advisory_text(info, analysis)
    assert "Code Excl 01" in hindi
    assert "24 महीने" in hindi
    assert "स्वीकृत" in hindi or "स्वीकृति" in hindi


# ==============================================================================
# SCENARIO 7: Day Care Lithotripsy (<24 hrs) + Portability Continuity Credit
# ==============================================================================
def test_scenario_7_daycare_procedure_portability_credit():
    """
    Scenario 7: 48-year-old, lithotripsy ESWL (day care procedure, discharged same day),
    10 months in Star Health but ported after 30 months continuous coverage with previous insurer.
    """
    info = ExtractedInsuranceInfo(
        age=48,
        diagnosis_or_condition="renal calculi",
        treatment_type="lithotripsy ESWL",
        policy_tenure_months=10,
        continuity_of_coverage=True,
        primary_intent="waiting_period_specified_disease",
        identified_intents=["waiting_period_specified_disease", "benefits_inquiry"],
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-WAIT-002", "STAR-PREMIER-ROOM-001"])

    # Portability credit finding
    assert any("Portability / Continuity Credit" in f for f in analysis.findings)

    # Waiting period warning mentions portability qualification
    assert any("portability" in w.lower() for w in analysis.warnings)

    # In-patient benefits include day care procedures
    assert any("Day care procedures for treatments not requiring 24-hour hospitalization" in f for f in analysis.findings)

    hindi = compose_hindi_advisory_text(info, analysis)
    assert "पोर्टेबिलिटी" in hindi


# ==============================================================================
# SCENARIO 8: Proportionate Deduction: Differential Billing vs Uniform Billing
# ==============================================================================
def test_scenario_8_differential_vs_uniform_billing():
    """
    Scenario 8: Comparing differential billing vs uniform billing:
    Sum insured ₹10 Lakh, room rent ₹20,000/day (1% limit is ₹10,000/day).
    """
    # Case A: Differential billing TRUE
    info_diff = ExtractedInsuranceInfo(
        age=56,
        diagnosis_or_condition="kidney stones",
        selected_room_rent_per_day=20000.0,
        sum_insured=1000000.0,
        hospital_differential_billing=True,
        primary_intent="room_rent_eligibility",
        identified_intents=["room_rent_eligibility"],
    )
    analysis_diff = evaluate_policy_rules(info_diff, ["STAR-PREMIER-ROOM-001"])
    assert any("Proportionate deduction will apply" in w for w in analysis_diff.warnings)

    # Case B: Differential billing FALSE (hospital does not adopt differential billing)
    info_uniform = ExtractedInsuranceInfo(
        age=56,
        diagnosis_or_condition="kidney stones",
        selected_room_rent_per_day=20000.0,
        sum_insured=1000000.0,
        hospital_differential_billing=False,
        primary_intent="room_rent_eligibility",
        identified_intents=["room_rent_eligibility"],
    )
    analysis_uniform = evaluate_policy_rules(info_uniform, ["STAR-PREMIER-ROOM-001"])
    # Under uniform billing, proportionate deduction is NOT applied per PDF Page 3
    assert any("Hospital does NOT practice differential billing" in f for f in analysis_uniform.findings)
    assert not any("Proportionate deduction will apply" in w for w in analysis_uniform.warnings)


# ==============================================================================
# SCENARIO 9: Ambiguous Generic Kidney Diagnosis + Benefits Inquiry
# ==============================================================================
def test_scenario_9_ambiguous_generic_kidney_condition():
    """
    Scenario 9: User reports generic "kidney problem" without specifying calculi,
    and asks about hospital benefits. Must NOT auto-map to Code Excl 02.
    """
    info = ExtractedInsuranceInfo(
        age=50,
        diagnosis_or_condition="kidney problem",
        insurer_mentioned="Star Health",
        hospital_deposit=None,
        selected_room_rent_per_day=None,
        sum_insured=None,
        policy_tenure_months=None,
        primary_intent="benefits_inquiry",
        identified_intents=["benefits_inquiry"],
        user_question="मुझे किडनी की प्रॉब्लम है, डॉक्टर ने एडमिट होने को कहा है, क्या बेनिफिट्स मिलेंगे?",
    )

    analysis = evaluate_policy_rules(info, ["STAR-PREMIER-ROOM-001"])

    # 1. Ambiguous kidney warning raised
    assert any("Ambiguous Diagnosis" in w for w in analysis.warnings)
    assert any("clinical diagnosis" in w.lower() for w in analysis.warnings)

    # 2. General in-patient benefits outlined
    assert any("In-Patient Hospitalization Benefits" in f for f in analysis.findings)

    # 3. Missing information includes specific diagnosis
    assert any("specific_clinical_diagnosis" in m for m in analysis.missing_information)

    # 4. Hindi response asks for specific diagnosis
    hindi = compose_hindi_advisory_text(info, analysis)
    assert "किडनी की सामान्य समस्या" in hindi
    assert "सटीक डायग्नोसिस" in hindi


# ==============================================================================
# SCENARIO 10: Unindexed/Excluded Feature (Maternity/Cosmetic) + Hospital Deposit
# ==============================================================================
def test_scenario_10_unindexed_maternity_with_deposit():
    """
    Scenario 10: User inquires about maternity coverage (not covered in Star Health Premier)
    and asks why hospital is requesting a ₹25,000 deposit.
    """
    info = ExtractedInsuranceInfo(
        age=28,
        diagnosis_or_condition="maternity delivery",
        treatment_type="caesarean section",
        hospital_deposit=25000.0,
        selected_room_rent_per_day=None,
        sum_insured=None,
        primary_intent="hospital_deposit_inquiry",
        identified_intents=["hospital_deposit_inquiry"],
        user_question="क्या डिलीवरी का खर्च स्टार हेल्थ में कवर्ड है और अस्पताल ₹25,000 डिपॉजिट क्यों मांग रहा है?",
    )

    analysis = evaluate_policy_rules(info, [])

    # 1. System does NOT hallucinate maternity coverage
    assert not any("Maternity benefit approved" in f for f in analysis.findings)

    # 2. Deposit is clearly explained as hospital advance practice
    deposit_findings = [f for f in analysis.findings if "Hospital Advance Admission Deposit" in f]
    assert len(deposit_findings) > 0
    assert "₹25,000.00" in deposit_findings[0]
    assert "advance security payment / deposit" in deposit_findings[0]
    assert "a full refund is never guaranteed" in deposit_findings[0]

    # 3. Missing schedule details flagged
    assert any("sum_insured" in m for m in analysis.missing_information)

    hindi = compose_hindi_advisory_text(info, analysis)
    assert "₹25,000" in hindi or "25,000" in hindi
    assert "अग्रिम सुरक्षा राशि" in hindi
