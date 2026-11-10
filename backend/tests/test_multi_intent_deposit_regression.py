"""
Test Suite: Multi-Intent, Hospital Deposit, Benefits Inquiry & Age Ambiguity
----------------------------------------------------------------------------
Validates all requirements for real-world scenarios:
1. Preserve every user intent, not just highest-ranked retrieval result.
2. Distinguish hospital deposit, room rent, sum insured, and treatment costs.
3. Extract age, condition, treatment, insurer, deposit amount, and tenure independently.
4. Retrieve relevant policy benefits when user asks what benefits they have.
5. Generate a concise benefits summary alongside applicable exclusions.
6. Explain that advance deposit is not an insurance deduction and cashless/reimbursement must be verified.
7. Include 24-month kidney calculi waiting period and portability qualification.
8. Identify age eligibility ambiguity for a 24-year-old (dependent child vs primary proposer).
9. Explicitly identify missing tenure, sum insured, and membership status.
10. Balanced factual grounding (never claims guaranteed approval or rejection).
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


def test_exact_scenario_24yr_kidney_stone_deposit_benefits():
    """
    EXACT USER PROMPT SCENARIO:
    A 24-year-old user explains in Hindi/Hinglish that they need kidney-stone surgery,
    have Star Health insurance, and the hospital is asking for a ₹30,000 deposit.
    They ask what benefits their policy provides.
    """
    info = ExtractedInsuranceInfo(
        age=24,
        diagnosis_or_condition="kidney calculi",
        treatment_type="kidney stone surgery",
        insurer_mentioned="Star Health",
        hospital_deposit=30000.0,
        selected_room_rent_per_day=None,  # MUST NOT be confused with deposit!
        sum_insured=None,
        policy_tenure_months=None,
        membership_status=None,  # Unconfirmed whether dependent or primary
        primary_intent="benefits_inquiry",
        identified_intents=[
            "benefits_inquiry",
            "hospital_deposit_inquiry",
            "waiting_period_specified_disease",
            "age_eligibility_inquiry",
        ],
        retrieval_queries=[
            "Star Health Premier Section B Coverage 1 In-Patient Hospitalization room rent surgeon OT charges medicines benefits",
            "Star Health Premier Code Excl 02 24 consecutive months continuous coverage waiting period kidney calculi surgery",
        ],
        user_question="मुझे किडनी स्टोन सर्जरी करवानी है और अस्पताल ₹30,000 डिपॉजिट मांग रहा है, मेरी पॉलिसी में क्या बेनिफिट्स मिलेंगे?",
        units_and_amounts=[
            UnitAmountItem(parameter="age", stated_value="24 years"),
            UnitAmountItem(parameter="deposit", stated_value="30,000 INR deposit"),
        ],
    )

    # 1. Verify entity extraction separation
    assert info.hospital_deposit == 30000.0
    assert info.selected_room_rent_per_day is None
    assert info.age == 24
    assert info.sum_insured is None
    assert info.policy_tenure_months is None

    # 2. Multi-query retrieval from ChromaDB
    retrieved_clauses = retrieve_policy_clauses_multi(info.retrieval_queries, top_k=3)
    retrieved_ids = [c["clause_id"] for c in retrieved_clauses]
    assert "STAR-PREMIER-WAIT-002" in retrieved_ids
    assert "STAR-PREMIER-ROOM-001" in retrieved_ids

    # 3. Deterministic Rule Engine Evaluation
    analysis = evaluate_policy_rules(info=info, retrieved_clause_ids=retrieved_ids)

    # Verify findings: Benefits Summary
    benefits_findings = [f for f in analysis.findings if "In-Patient Hospitalization Benefits" in f]
    assert len(benefits_findings) > 0, "Must include In-Patient Hospitalization Benefits summary"
    assert "1% of Sum Insured" in benefits_findings[0]
    assert "Surgeon, Anesthetist" in benefits_findings[0]

    # Verify findings: Hospital Deposit Explanation
    deposit_findings = [f for f in analysis.findings if "Hospital Advance Admission Deposit" in f]
    assert len(deposit_findings) > 0, "Must explain hospital advance admission deposit"
    assert "₹30,000.00" in deposit_findings[0]
    assert "advance security payment" in deposit_findings[0]
    assert "NOT an approved insurance deduction" in deposit_findings[0]

    # Verify warnings: Hospital Deposit Verification
    deposit_warnings = [w for w in analysis.warnings if "Hospital Deposit Verification" in w]
    assert len(deposit_warnings) > 0
    assert "Cashless pre-authorisation" in deposit_warnings[0]

    # Verify warnings: 24-Month Waiting Period under Code Excl 02
    wait_warnings = [w for w in analysis.warnings if "Code Excl 02" in w]
    assert len(wait_warnings) > 0
    assert "24 months" in wait_warnings[0] or "24-month" in wait_warnings[0]

    # Verify findings: Age Eligibility Ambiguity (24 years old)
    age_findings = [f for f in analysis.findings if "Age Eligibility & Membership Status" in f]
    assert len(age_findings) > 0
    assert "24" in age_findings[0]
    assert "dependent child" in age_findings[0]
    assert "primary insured" in age_findings[0]

    # Verify missing information identifies all unconfirmed schedule parameters
    assert any("sum_insured" in m for m in analysis.missing_information)
    assert any("policy_tenure_months" in m for m in analysis.missing_information)
    assert any("membership_status" in m for m in analysis.missing_information)
    assert any("cashless_pre_authorization_status" in m for m in analysis.missing_information)

    # 4. Hindi Advisory Text Composition
    hindi_text = compose_hindi_advisory_text(info, analysis)

    # Verify all components in Hindi advisory:
    assert "इन-पेशेंट हॉस्पिटलाइजेशन" in hindi_text or "हॉस्पिटलाइजेशन" in hindi_text
    assert "₹30,000" in hindi_text or "30,000" in hindi_text
    assert "अग्रिम सुरक्षा राशि" in hindi_text
    assert "बीमा कटौती नहीं है" in hindi_text
    assert "कैशलेस प्री-ऑथराइजेशन" in hindi_text
    assert "24 महीने का वेटिंग पीरियड" in hindi_text
    assert "पोर्टेबिलिटी" in hindi_text
    assert "24 वर्ष" in hindi_text
    assert "आश्रित संतान" in hindi_text or "प्राथमिक पॉलिसीधारक" in hindi_text
    assert "पॉलिसी शेड्यूल" in hindi_text


def test_variation_1_deposit_with_mature_tenure():
    """
    Variation 1: User has completed 36 months of tenure, needs gall bladder stone surgery,
    hospital requests ₹20,000 deposit.
    """
    info = ExtractedInsuranceInfo(
        age=45,
        diagnosis_or_condition="gall bladder calculi",
        treatment_type="cholecystectomy",
        hospital_deposit=20000.0,
        selected_room_rent_per_day=None,
        sum_insured=1000000.0,
        policy_tenure_months=36,
        primary_intent="hospital_deposit_inquiry",
        identified_intents=["hospital_deposit_inquiry", "waiting_period_specified_disease"],
        retrieval_queries=["Star Health Premier Code Excl 02 gall bladder calculi waiting period"],
    )

    analysis = evaluate_policy_rules(info=info, retrieved_clause_ids=["STAR-PREMIER-WAIT-002"])

    # Deposit must be explained as advance security, not insurance deduction
    assert any("Hospital Advance Admission Deposit" in f for f in analysis.findings)
    assert any("₹20,000.00" in f for f in analysis.findings)

    # 36 months satisfies 24 months requirement
    assert any("satisfies the 24-month continuous coverage requirement" in f for f in analysis.findings)

    hindi_text = compose_hindi_advisory_text(info, analysis)
    assert "₹20,000" in hindi_text
    assert "अग्रिम सुरक्षा राशि" in hindi_text
    assert "बीमा कटौती नहीं है" in hindi_text


def test_variation_2_both_deposit_and_room_rent_in_same_input():
    """
    Variation 2: User provides daily room rent (₹15,000) AND hospital asks for deposit (₹50,000).
    System must strictly distinguish both without mixing them up.
    """
    info = ExtractedInsuranceInfo(
        age=50,
        diagnosis_or_condition="kidney stone",
        treatment_type="surgery",
        selected_room_rent_per_day=15000.0,
        hospital_deposit=50000.0,
        sum_insured=1000000.0,
        policy_tenure_months=12,
        hospital_differential_billing=True,
        primary_intent="room_rent_eligibility",
        identified_intents=["room_rent_eligibility", "hospital_deposit_inquiry", "waiting_period_specified_disease"],
    )

    analysis = evaluate_policy_rules(info=info, retrieved_clause_ids=["STAR-PREMIER-ROOM-001", "STAR-PREMIER-WAIT-002"])

    # Room rent: exceeds 1% (₹10,000) by ₹5,000
    assert any("exceeds your confirmed eligible limit of ₹10,000.00/day by ₹5,000.00/day" in w for w in analysis.warnings)

    # Deposit: clearly identified as ₹50,000 advance admission deposit
    assert any("Hospital Advance Admission Deposit (₹50,000.00)" in f for f in analysis.findings)

    hindi_text = compose_hindi_advisory_text(info, analysis)
    assert "10,000 रुपये प्रतिदिन है" in hindi_text
    assert "15,000 रुपये है" in hindi_text
    assert "₹50,000" in hindi_text
    assert "अग्रिम सुरक्षा राशि" in hindi_text


def test_variation_3_young_adult_membership_ambiguity():
    """
    Variation 3: 24-year-old patient with no membership status declared.
    Must request clarification whether dependent child or primary insured.
    """
    info = ExtractedInsuranceInfo(
        age=24,
        diagnosis_or_condition="acute appendicitis",
        treatment_type="appendectomy",
        membership_status=None,
        sum_insured=500000.0,
        policy_tenure_months=6,
        primary_intent="general_claim",
    )

    analysis = evaluate_policy_rules(info=info, retrieved_clause_ids=["STAR-PREMIER-ROOM-001"])

    assert any("Age Eligibility & Membership Status" in f for f in analysis.findings)
    assert any("Membership Status Clarification" in w for w in analysis.warnings)
    assert any("membership_status" in m for m in analysis.missing_information)

    hindi_text = compose_hindi_advisory_text(info, analysis)
    assert "24 वर्ष" in hindi_text
    assert "आश्रित संतान" in hindi_text or "प्राथमिक पॉलिसीधारक" in hindi_text


def test_variation_4_benefits_inquiry_only():
    """
    Variation 4: User explicitly asks what benefits their policy provides for hospital admission.
    """
    info = ExtractedInsuranceInfo(
        age=60,
        diagnosis_or_condition="knee osteoarthritis",
        treatment_type="total knee replacement",
        sum_insured=None,
        policy_tenure_months=None,
        primary_intent="benefits_inquiry",
        identified_intents=["benefits_inquiry", "waiting_period_specified_disease"],
        retrieval_queries=["Star Health Premier Section B Coverage 1 In-Patient Hospitalization room rent surgeon OT charges medicines benefits"],
        user_question="मेरी स्टार हेल्थ प्रीमियर पॉलिसी में अस्पताल में क्या-क्या बेनिफिट्स कवर्ड हैं?",
    )

    analysis = evaluate_policy_rules(info=info, retrieved_clause_ids=["STAR-PREMIER-ROOM-001"])

    # Benefits summary must be present
    assert any("Section B, Coverage 1 In-Patient Hospitalization Benefits" in f for f in analysis.findings)
    assert any("Room, boarding and nursing expenses up to 1%" in f for f in analysis.findings)

    hindi_text = compose_hindi_advisory_text(info, analysis)
    assert "इन-पेशेंट हॉस्पिटलाइजेशन" in hindi_text
    assert "कमरा किराया" in hindi_text
    assert "सर्जन फीस" in hindi_text or "डॉक्टर" in hindi_text


def test_variation_5_deposit_with_continuity_portability():
    """
    Variation 5: User has 10 months in Star Health, but ported from a 3-year prior continuous policy.
    Hospital requests ₹25,000 deposit for lithotripsy.
    """
    info = ExtractedInsuranceInfo(
        age=38,
        diagnosis_or_condition="kidney calculi",
        treatment_type="lithotripsy",
        hospital_deposit=25000.0,
        sum_insured=1000000.0,
        policy_tenure_months=10,
        continuity_of_coverage=True,
        primary_intent="hospital_deposit_inquiry",
        identified_intents=["hospital_deposit_inquiry", "waiting_period_specified_disease", "continuity_and_portability"],
    )

    analysis = evaluate_policy_rules(info=info, retrieved_clause_ids=["STAR-PREMIER-WAIT-002"])

    # Portability credit recognized
    assert any("Portability / Continuity Credit" in f for f in analysis.findings)
    # Deposit identified
    assert any("Hospital Advance Admission Deposit (₹25,000.00)" in f for f in analysis.findings)

    hindi_text = compose_hindi_advisory_text(info, analysis)
    assert "₹25,000" in hindi_text
    assert "अग्रिम सुरक्षा राशि" in hindi_text
    assert "पोर्टेबिलिटी" in hindi_text
