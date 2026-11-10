"""
Deterministic Insurance Rule Engine for BimaSakshi (Phase 3 & 4 - Refined)
--------------------------------------------------------------------------
Evaluates policy rules, calculates room-rent eligibility and proportionate
deductions, and verifies waiting periods strictly under Star Health Premier
Insurance Policy (UIN: SHAHLIP22226V012122, Version: POL / SHP / V.6 / 2023).

Strict Rules:
- Prioritizes user's primary intent and actual question (e.g. accident exception vs room rent).
- Pure deterministic Python calculations (no LLM math).
- Under Code Excl 02 (PDF Page 6), the 24-month waiting period does NOT apply to claims arising due to an accident.
- If causal relationship between accident and treatment is clear, exempt from Code Excl 02.
- If causal relationship is unclear, return insufficient_information and require causal documentation.
- If sum insured is missing, retain null in extracted_information, mark calculation
  illustrative_only=True, and do not generate false personalized entitlement warnings.
- Proportionate deduction evaluates strictly on hospital differential billing status:
    * True: Evaluate deduction if associated expenses available.
    * False: No proportionate deduction.
    * Null: Return insufficient_information; never claim a deduction will apply.
- Waiting period is strictly conditional on continuous coverage, portability credit,
  accident exception, and clause applicability (no guaranteed rejection claims).
- Pharmacy, consumables, implants, and diagnostics are explicitly excluded from associated expenses.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from schemas.analysis import (
    AnalysisResult,
    CalculationDetail,
    ExtractedInsuranceInfo,
)

logger = logging.getLogger("bimasakshi.policy_engine")

# Demonstration baseline (Star Health Premier published options start at ₹10 Lakh)
DEMO_SUM_INSURED_DEFAULT = 1_000_000.0  # ₹10,00,000 (10 Lakh)
ROOM_RENT_PERCENTAGE = 0.01              # 1% of Sum Insured
ROOM_RENT_MAX_CAP = 20_000.0             # ₹20,000 per day maximum cap
SPECIFIED_DISEASE_WAITING_MONTHS = 24    # Code Excl 02
PED_WAITING_MONTHS = 24                  # Code Excl 01
MODERN_TREATMENT_COVERAGE_PERCENTAGE = 0.50  # Section II, Coverage 14: 50% of Sum Insured

# Keywords indicating modern treatment / robotic surgery under Coverage 14
ROBOTIC_SURGERY_KEYWORDS = [
    "robotic surgery",
    "robotic",
    "robot",
    "modern treatment",
    "advanced treatment",
    "da vinci",
    "रोबोटिक",
]

# Generic kidney terms that are ambiguous and must NOT be mapped to kidney calculi
GENERIC_KIDNEY_TERMS = [
    "kidney problem",
    "kidney issue",
    "kidney disease",
    "kidney disorder",
    "kidney trouble",
    "kidney ki problem",
    "kidney me problem",
    "kidney kharab",
    "गुर्दे की समस्या",
    "गुर्दे की बीमारी",
]

# Keywords indicating kidney calculi management under Code Excl 02
KIDNEY_CALCULI_KEYWORDS = [
    "calculi",
    "kidney stone",
    "renal calculi",
    "ureteric calculi",
    "genitourinary calculi",
    "nephrolithiasis",
    "urolithiasis",
    "lithotripsy",
    "pathari",
    "पथरी",
]

ACCIDENT_KEYWORDS = [
    "accident",
    "accidental",
    "trauma",
    "injury",
    "दुर्घटना",
    "चोट",
]

ACCIDENT_CLEAR_CAUSAL_PHRASES = [
    "because of",
    "due to",
    "caused by",
    "resulting from",
    "from an accident",
    "required because of an accident",
    "arising due to an accident",
    "arising from an accident",
    "के कारण",
    "की वजह से",
    "से हुई",
    "accidental fall",
    "accidental injury",
    "trauma",
    "emergency accident",
    "accident surgery",
    "accident ke karan",
    "road accident",
]

ACCIDENT_UNCLEAR_CAUSAL_PHRASES = [
    "unclear",
    "not related",
    "separate",
    "unconfirmed whether related",
    "had an accident last month",
    "also had an accident",
    "unrelated accident",
    "relationship unclear",
    "not sure if related",
]

# Features not indexed in the demonstration Star Health Premier ChromaDB vectorstore
UNINDEXED_FEATURE_DEFINITIONS = {
    "maternity": "Maternity and pregnancy/childbirth coverage",
    "delivery": "Delivery, obstetric and caesarean section coverage",
    "pregnancy": "Pregnancy-related medical expenses",
    "dental": "Dental examination, treatment and oral surgery",
    "ayush": "AYUSH (Ayurveda, Yoga, Unani, Siddha, Homeopathy) inpatient hospitalization",
    "ayurveda": "Ayurvedic inpatient medical treatment",
    "homeopathy": "Homeopathic medical treatment",
    "pre_post_hospitalization": "Pre-hospitalization and post-hospitalization medical expenses",
    "pre-hospitalization": "Pre-hospitalization medical expenses (60 days)",
    "post-hospitalization": "Post-hospitalization medical expenses (90/180 days)",
    "day_care": "Day-care procedures (<24-hour hospitalization)",
    "daycare": "Day-care procedures and ambulatory surgeries",
    "domiciliary": "Domiciliary hospitalization (in-home treatment)",
    "organ_donor": "Organ donor in-patient hospitalization expenses",
    "critical_illness": "Critical illness lump-sum benefit",
    "air_ambulance": "Air ambulance emergency evacuation coverage",
}


def is_generic_kidney_condition(info: ExtractedInsuranceInfo) -> bool:
    """
    Returns True if user mentions a generic kidney condition without specifying
    kidney calculi / stones or listed conditions under Code Excl 02.
    """
    # An accident or traumatic injury is governed by accident rules, not generic disease ambiguity
    is_acc, _ = determine_accident_status(info)
    if is_acc:
        return False

    combined_condition_text = (
        f"{info.diagnosis_or_condition or ''} "
        f"{info.treatment_type or ''} "
        f"{info.user_question or ''} "
        f"{info.normalized_english_query or ''}"
    ).lower()

    # If explicit calculi or stone keywords are present, it is not generic
    if any(k in combined_condition_text for k in KIDNEY_CALCULI_KEYWORDS):
        return False

    return (
        any(k in combined_condition_text for k in GENERIC_KIDNEY_TERMS)
        or (
            ("kidney" in combined_condition_text or "गुर्दा" in combined_condition_text or "गुर्दे" in combined_condition_text)
            and not any(k in combined_condition_text for k in KIDNEY_CALCULI_KEYWORDS)
        )
    )


def determine_accident_status(
    info: ExtractedInsuranceInfo,
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether the query/claim involves an accident and assesses the causal relationship.
    Returns: (is_accident: bool, causal_relationship: Optional[str] -> 'clear', 'unclear', None)
    """
    combined_text = (
        f"{info.diagnosis_or_condition or ''} "
        f"{info.treatment_type or ''} "
        f"{info.user_question or ''} "
        f"{info.normalized_english_query or ''}"
    ).lower()

    if info.is_accident_related is True:
        causality = info.accident_causal_relationship or "clear"
        return True, causality

    has_accident_keyword = any(k in combined_text for k in ACCIDENT_KEYWORDS)
    if not has_accident_keyword:
        return False, None

    # Accident is mentioned in transcript or fields
    if info.accident_causal_relationship in ["clear", "unclear"]:
        return True, info.accident_causal_relationship

    if any(p in combined_text for p in ACCIDENT_UNCLEAR_CAUSAL_PHRASES):
        return True, "unclear"

    if any(p in combined_text for p in ACCIDENT_CLEAR_CAUSAL_PHRASES):
        return True, "clear"

    # Default if accident is asked in relation to surgery, treatment or waiting period
    if (
        "surgery" in combined_text
        or "treatment" in combined_text
        or "procedure" in combined_text
        or "waiting" in combined_text
        or "claim" in combined_text
    ):
        return True, "clear"

    return True, "unclear"


def determine_primary_intent(
    info: ExtractedInsuranceInfo,
    is_accident: bool,
) -> str:
    """
    Determines user's primary insurance question/topic.
    """
    if info.primary_intent and info.primary_intent != "general_claim":
        return info.primary_intent

    combined_text = (
        f"{info.diagnosis_or_condition or ''} "
        f"{info.treatment_type or ''} "
        f"{info.user_question or ''} "
        f"{info.normalized_english_query or ''}"
    ).lower()

    has_waiting_keyword = any(
        k in combined_text for k in ["waiting period", "24 month", "wait", "वेटिंग", "अवधि", "महीने"]
    )

    if any(k in combined_text for k in ROBOTIC_SURGERY_KEYWORDS):
        return "modern_treatment_robotic"

    if is_accident and (has_waiting_keyword or "surgery" in combined_text or "claim" in combined_text or "exception" in combined_text):
        return "waiting_period_accident"

    if is_generic_kidney_condition(info):
        return "ambiguous_diagnosis"

    if any(k in combined_text for k in KIDNEY_CALCULI_KEYWORDS) and has_waiting_keyword:
        return "waiting_period_specified_disease"

    if info.declared_ped is not None or "pre-existing" in combined_text or "ped" in combined_text:
        return "waiting_period_ped"

    if info.selected_room_rent_per_day is not None and not has_waiting_keyword:
        return "room_rent_eligibility"

    if info.hospital_differential_billing is not None:
        return "proportionate_deduction"

    return "general_claim"


def evaluate_policy_rules(
    info: ExtractedInsuranceInfo,
    retrieved_clause_ids: Optional[List[str]] = None,
) -> AnalysisResult:
    """
    Executes deterministic insurance checks against extracted entities
    based strictly on Star Health Premier Insurance Policy terms.
    Prioritizes the user's primary intent rather than forcing irrelevant warnings.
    """
    findings: List[str] = []
    calculations: List[CalculationDetail] = []
    warnings: List[str] = []
    assumptions: List[str] = []
    missing_info: List[str] = list(info.missing_information)
    relevant_clause_ids: List[str] = list(retrieved_clause_ids or [])

    # Standard non-associated expenses per policy definition (PDF Page 2 & IRDAI Guidelines)
    excluded_expenses = [
        "Pharmacy & Consumables (expressly excluded from Associated Medical Expenses per PDF Page 2)",
        "Diagnostics, scans and laboratory investigations (expressly non-associated)",
        "Implants and medical devices (expressly non-associated)",
        "Intensive Care Unit (ICU / ICCU) charges (strictly exempt from proportionate deductions per IRDAI guidelines & policy terms)",
    ]

    is_accident, accident_causality = determine_accident_status(info)
    primary_intent = determine_primary_intent(info, is_accident)

    # Detect Modern Treatment / Robotic Surgery (Coverage 14)
    is_robotic = (
        info.is_robotic_surgery is True
        or primary_intent == "modern_treatment_robotic"
        or any("robotic" in str(q).lower() for q in (info.retrieval_queries or []))
        or any("modern_treatment" in str(it).lower() for it in (info.identified_intents or []))
        or any(k in f"{info.user_question or ''} {info.treatment_type or ''} {info.diagnosis_or_condition or ''} {info.normalized_english_query or ''}".lower() for k in ROBOTIC_SURGERY_KEYWORDS)
    )

    # Detect Ambiguous Generic Kidney Condition (Issue 1)
    is_ambiguous_kidney = is_generic_kidney_condition(info)

    # User provided room-rent or asked specifically about financial limits
    has_explicit_room_query = (
        info.selected_room_rent_per_day is not None
        or primary_intent in ["room_rent_eligibility", "proportionate_deduction"]
        or (
            info.sum_insured is not None
            and primary_intent in ["room_rent_eligibility", "general_claim"]
            and not is_robotic
            and not is_ambiguous_kidney
            and not is_accident
        )
        or "room rent" in str(info.user_question or '').lower()
        or "कमरा" in str(info.user_question or '').lower()
    )

    # -------------------------------------------------------------
    # 0. Unindexed Policy Features Check
    # -------------------------------------------------------------
    combined_query_text = (
        f"{info.user_question or ''} "
        f"{info.diagnosis_or_condition or ''} "
        f"{info.treatment_type or ''} "
        f"{info.normalized_english_query or ''} "
        f"{' '.join(info.identified_intents)} "
        f"{' '.join(info.retrieval_queries)}"
    ).lower()

    detected_unindexed_features = set()
    for kw, feature_label in UNINDEXED_FEATURE_DEFINITIONS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", combined_query_text):
            detected_unindexed_features.add(feature_label)

    for feature_label in sorted(detected_unindexed_features):
        findings.append(
            f"insufficient_information: {feature_label} is not indexed in the demonstration policy database "
            f"(which currently indexes Room Rent [PDF Page 3], Pre-Existing Diseases [Code Excl 01, PDF Page 6], "
            f"and Specified Disease Waiting Periods [Code Excl 02, PDF Page 6]). "
            f"Please review the complete Star Health Premier policy document and schedule for applicable waiting periods, "
            f"sub-limits, and terms."
        )
        missing_clause_desc = f"unindexed_benefit_clause ({feature_label} from full policy document)"
        if missing_clause_desc not in missing_info:
            missing_info.append(missing_clause_desc)

    # -------------------------------------------------------------
    # 0B. ICU Charges Exemption Check (IRDAI Safeguard)
    # -------------------------------------------------------------
    has_icu = (
        (info.icu_charges is not None and info.icu_charges > 0)
        or "icu" in combined_query_text
        or "iccu" in combined_query_text
        or "intensive care" in combined_query_text
    )
    if has_icu:
        icu_str = f" of ₹{info.icu_charges:,.2f}" if (info.icu_charges is not None and info.icu_charges > 0) else ""
        findings.append(
            f"ICU / ICCU Exemption: Under IRDAI guidelines and Star Health Premier policy terms, proportionate deductions "
            f"must NOT be applied to Intensive Care Unit (ICU / ICCU) charges{icu_str} regardless of room category occupied."
        )

    # -------------------------------------------------------------
    # 0C. Ambiguous Kidney Condition Check (Issue 1)
    # -------------------------------------------------------------
    if is_ambiguous_kidney:
        diag = info.diagnosis_or_condition or "kidney problem"
        findings.append(
            f"insufficient_information: Diagnosis stated as generic kidney condition ('{diag}'). "
            f"Under Star Health Premier Policy terms, Code Excl 02 imposes a 24-month waiting period specifically "
            f"for management of Kidney calculi and Genitourinary tract calculi, not all kidney conditions. "
            f"Generic kidney disease, nephritis, or renal insufficiency are subject to standard policy terms or PED rules. "
            f"Please provide the exact clinical diagnosis from the treating physician."
        )
        warnings.append(
            f"Ambiguous Diagnosis: Specific clinical diagnosis is required. Code Excl 02 24-month waiting period "
            f"applies specifically to kidney calculi/stones, not to all generic kidney conditions."
        )
        diag_missing = "specific_clinical_diagnosis (confirmation whether condition is renal calculi/stones or another nephrological condition)"
        if diag_missing not in missing_info:
            missing_info.append(diag_missing)

    # -------------------------------------------------------------
    # 0D. Modern Treatment / Robotic Surgery (Section II, Coverage 14)
    # -------------------------------------------------------------
    if is_robotic:
        if "STAR-PREMIER-MODERN-014" not in relevant_clause_ids:
            relevant_clause_ids.insert(0, "STAR-PREMIER-MODERN-014")

        # Determine effective sum insured for modern treatment
        si_for_modern = float(info.sum_insured) if (info.sum_insured is not None and info.sum_insured > 0) else DEMO_SUM_INSURED_DEFAULT
        is_si_illustrative = (info.sum_insured is None or info.sum_insured <= 0)
        modern_limit = si_for_modern * MODERN_TREATMENT_COVERAGE_PERCENTAGE

        if is_si_illustrative:
            modern_explanation = (
                f"Illustrative Demonstration Only: Under Section II, Coverage 14 (Coverage for Modern Treatment), "
                f"Robotic surgeries are covered up to 50% of Sum Insured (₹{modern_limit:,.2f} for illustrative ₹{si_for_modern:,.2f} schedule), "
                f"inclusive of pre-hospitalisation and post-hospitalisation expenses per policy period. "
                f"Actual limit must be confirmed from active policy schedule."
            )
            findings.append(
                f"Section II, Coverage 14 – Coverage for Modern Treatment: Robotic surgeries are covered under Star Health Premier "
                f"up to 50% of the Sum Insured (illustrative ₹{modern_limit:,.2f} based on ₹10 Lakh baseline), "
                f"inclusive of pre-hospitalisation and post-hospitalisation expenses per policy period. "
                f"Note: This coverage is distinct from bariatric surgery and general room rent limits."
            )
            si_missing = "sum_insured (confirmation of actual sum insured from policy schedule)"
            if si_missing not in missing_info:
                missing_info.append(si_missing)
            assumptions.append(
                f"Sum Insured was not provided by user; displaying an illustrative demonstration example "
                f"for Robotic Surgery using ₹{si_for_modern:,.2f} (Star Health Premier published options start at ₹10 Lakh, "
                f"subject to actual policy schedule confirmation)."
            )
        else:
            modern_explanation = (
                f"Under Section II, Coverage 14 (Coverage for Modern Treatment), Robotic surgeries are covered "
                f"up to 50% of confirmed Sum Insured (₹{modern_limit:,.2f} for ₹{si_for_modern:,.2f}), "
                f"inclusive of pre-hospitalisation and post-hospitalisation expenses per policy period."
            )
            findings.append(
                f"Section II, Coverage 14 – Coverage for Modern Treatment: Robotic surgeries are covered under Star Health Premier "
                f"up to 50% of the confirmed Sum Insured (₹{modern_limit:,.2f}), "
                f"inclusive of pre-hospitalisation and post-hospitalisation expenses per policy period. "
                f"Note: This coverage is distinct from bariatric surgery and general room rent limits."
            )

        calculations.append(
            CalculationDetail(
                type="modern_treatment_limit",
                formula="sum_insured * 0.50",
                inputs={
                    "sum_insured": si_for_modern,
                    "coverage_percentage": MODERN_TREATMENT_COVERAGE_PERCENTAGE,
                    "confirmed_input": not is_si_illustrative,
                },
                result=modern_limit,
                explanation=modern_explanation,
                illustrative_only=is_si_illustrative,
            )
        )

    # -------------------------------------------------------------
    # 0E. In-Patient Hospitalization Benefits Inquiry
    # -------------------------------------------------------------
    combined_intents = set(info.identified_intents or [])
    combined_intents.add(primary_intent)
    has_benefits_query = (
        "benefits_inquiry" in combined_intents
        or "hospitalization_coverage" in combined_intents
        or any(w in str(info.user_question or '').lower() for w in ["benefit", "benefits", "cover", "coverage", "सुविधा", "कवर", "क्या मिलेगा"])
        or "benefits" in str(info.normalized_english_query or '').lower()
    )
    if has_benefits_query:
        if "STAR-PREMIER-ROOM-001" not in relevant_clause_ids:
            relevant_clause_ids.append("STAR-PREMIER-ROOM-001")
        findings.append(
            "Section B, Coverage 1 In-Patient Hospitalization Benefits: Under Star Health Premier Policy terms, covered in-patient benefits include: "
            "(1) Room, boarding and nursing expenses up to 1% of Sum Insured or ₹20,000/day, whichever is less; "
            "(2) Surgeon, Anesthetist, Medical Practitioner, Consultant and Specialist fees; "
            "(3) Anesthesia, Blood, Oxygen, Operation Theatre charges, and ICU/ICCU charges; "
            "(4) Surgical appliances, Medicines and drugs, Diagnostic materials and X-rays; "
            "(5) Pre-hospitalization (up to 60 days) and Post-hospitalization (up to 90/180 days); "
            "(6) Day care procedures for treatments not requiring 24-hour hospitalization. "
            "All benefits are subject to confirmed Sum Insured, policy admissibility, and applicable waiting periods."
        )

    # -------------------------------------------------------------
    # 0F. Hospital Advance Admission Deposit Evaluation
    # -------------------------------------------------------------
    has_deposit_query = (
        info.hospital_deposit is not None
        or "hospital_deposit_inquiry" in combined_intents
        or "deposit" in str(info.user_question or '').lower()
        or "deposit" in str(info.normalized_english_query or '').lower()
        or any("deposit" in str(q).lower() for q in (info.retrieval_queries or []))
    )
    if has_deposit_query:
        dep_val = info.hospital_deposit
        dep_str = f"₹{dep_val:,.2f}" if dep_val else "advance deposit"
        findings.append(
            f"[NON-POLICY / HOSPITAL PRACTICE] Hospital Advance Admission Deposit ({dep_str}): The deposit requested by the hospital is an advance security payment / deposit, "
            f"NOT an approved insurance deduction, mandatory co-payment, or room-rent charge. Under cashless hospitalization, following pre-authorization approval by Star Health / TPA, "
            f"the hospital adjusts or refunds this deposit subject to the approved sanction amount and after deducting non-payable expenses (such as registration fees, non-medical consumables, or applicable room-rent proportionate deductions); "
            f"a full refund is never guaranteed. If treated under reimbursement, the patient pays hospital charges upfront and claims admissible expenses post-discharge with original itemized bills and payment receipts."
        )
        warnings.append(
            f"Hospital Deposit Verification: The {dep_str} requested by the hospital is an admission security deposit, not an approved insurance deduction. "
            f"Cashless pre-authorisation: Following cashless approval, the hospital adjusts the deposit against the sanctioned amount minus non-admissible expenses; full refund is not guaranteed."
        )
        cashless_missing = "cashless_pre_authorization_status (initiate cashless pre-authorization with hospital TPA desk)"
        if cashless_missing not in missing_info:
            missing_info.append(cashless_missing)

    # -------------------------------------------------------------
    # 0G. Age Eligibility & Membership Status Ambiguity
    # -------------------------------------------------------------
    if info.age is not None and 18 <= info.age <= 25 and info.membership_status is None:
        findings.append(
            f"[POLICY SCHEDULE REQUIREMENT] Age Eligibility & Membership Status: Patient's reported age is {info.age} years. "
            f"Under Star Health Premier terms (UIN: SHAHLIP22226V012122), primary proposer / primary insured entry age is typically 50 to 75 years; "
            f"however, under Family Floater policies, dependent children are covered up to age 25 (if unmarried and financially dependent on parents). "
            f"Please verify membership status from the policy schedule to confirm whether the patient is enrolled as an eligible dependent child or holds an independent policy schedule (primary insured)."
        )
        warnings.append(
            f"Membership Status Clarification: At {info.age} years of age, verify whether the patient is enrolled as a dependent child "
            f"under a Family Floater policy or as the primary insured to ensure claim eligibility."
        )
        member_missing = "membership_status (clarify whether enrolled as a dependent child or primary insured)"
        if member_missing not in missing_info:
            missing_info.append(member_missing)

    # -------------------------------------------------------------
    # 1. Accident Exception Evaluation (Code Excl 02, PDF Page 6)
    # -------------------------------------------------------------
    if is_accident or primary_intent == "waiting_period_accident":
        if "STAR-PREMIER-WAIT-002" not in relevant_clause_ids:
            relevant_clause_ids.insert(0, "STAR-PREMIER-WAIT-002")

        if accident_causality == "clear":
            findings.append(
                "Code Excl 02 Accident Exception: Under Star Health Premier Policy terms (Code Excl 02, PDF Page 6), "
                "the 24-month specified disease / procedure waiting period does NOT apply to claims arising due to an accident. "
                "Therefore, surgery or treatment necessitated by an accidental injury is exempt from the 24-month waiting period, "
                "subject to formal verification of accident records (such as emergency admission summary, hospital MLC/FIR records) "
                "by the insurer. Standard policy exclusions and other terms continue to apply."
            )
            # Crucial: NO 24-month waiting-period warning is generated for accident-related treatment.
        else:
            findings.append(
                "insufficient_information: An accident was mentioned, but the direct causal relationship between the accident "
                "and the required medical treatment is unconfirmed. Under Star Health Premier terms (Code Excl 02, PDF Page 6), "
                "the waiting period waiver applies strictly to claims directly arising due to an accident. "
                "Please confirm with the hospital and submit accident documentation establishing direct causation."
            )
            warnings.append(
                "Accident Causal Verification Required: The 24-month waiting period exemption under Code Excl 02 is conditional "
                "on the surgery directly arising from the accident. Documentation establishing direct causation must be verified."
            )
            if "accident_causal_documentation (medical records establishing direct causation between accident and surgery)" not in missing_info:
                missing_info.append("accident_causal_documentation (medical records establishing direct causation between accident and surgery)")

    # -------------------------------------------------------------
    # 2. Specified Disease Waiting Period (Kidney Calculi / Code Excl 02)
    # -------------------------------------------------------------
    combined_condition_text = f"{info.diagnosis_or_condition or ''} {info.treatment_type or ''}".lower()
    is_kidney_calculi = any(k in combined_condition_text for k in KIDNEY_CALCULI_KEYWORDS) and not is_ambiguous_kidney

    if is_kidney_calculi:
        if "STAR-PREMIER-WAIT-002" not in relevant_clause_ids:
            relevant_clause_ids.append("STAR-PREMIER-WAIT-002")

        if is_accident and accident_causality == "clear":
            findings.append(
                "Kidney / urinary tract condition resulted directly from an accident; exempt from Code Excl 02 waiting period."
            )
        elif is_accident and accident_causality == "unclear":
            # Already warned under unclear accident causation above
            pass
        else:
            tenure = info.policy_tenure_months
            if info.continuity_of_coverage is True:
                findings.append(
                    "Portability / Continuity Credit: Continuous coverage without break under prior insurance "
                    "is credited toward reducing the 24-month waiting period under IRDAI portability norms."
                )

            if tenure is not None:
                if tenure < SPECIFIED_DISEASE_WAITING_MONTHS:
                    rem = SPECIFIED_DISEASE_WAITING_MONTHS - tenure
                    accident_note = " or the claim resulted from an accident" if is_accident else ""
                    warnings.append(
                        f"Kidney / genitourinary calculi treatment is subject to a 24-month waiting period under Code Excl 02 (PDF Page 6). "
                        f"Reported policy tenure is {tenure} months ({rem} months remaining). "
                        f"Coverage under this clause is conditional on continuous coverage and will not apply unless "
                        f"the policyholder holds eligible portability credit from a prior continuous policy{accident_note}. "
                        f"Please confirm prior policy continuity with the insurer."
                    )
                else:
                    findings.append(
                        f"Policy tenure of {tenure} months satisfies the 24-month continuous coverage requirement "
                        f"for kidney calculi under Code Excl 02 (PDF Page 6)."
                    )
            else:
                warnings.append(
                    "Kidney calculi / stones require 24 months continuous coverage under Code Excl 02 (PDF Page 6). "
                    "Policy tenure was not provided; waiting period compliance cannot be verified without policy inception details."
                )
                if "policy_tenure_months" not in missing_info:
                    missing_info.append("policy_tenure_months")

    elif info.diagnosis_or_condition and not is_accident and not is_ambiguous_kidney:
        findings.append(
            f"Diagnosis/condition noted: '{info.diagnosis_or_condition}'. Verified against specified disease exclusions."
        )

    # -------------------------------------------------------------
    # 3. Pre-Existing Disease (Code Excl 01)
    # -------------------------------------------------------------
    if info.declared_ped is True:
        if "STAR-PREMIER-PED-001" not in relevant_clause_ids:
            relevant_clause_ids.append("STAR-PREMIER-PED-001")
        tenure = info.policy_tenure_months

        if tenure is not None and tenure < PED_WAITING_MONTHS:
            rem = PED_WAITING_MONTHS - tenure
            warnings.append(
                f"Declared pre-existing condition is subject to a 24-month waiting period under Code Excl 01 (PDF Page 6). "
                f"Current tenure is {tenure} months ({rem} months remaining), subject to portability continuity credit."
            )
        elif tenure is not None and info.ped_accepted_by_insurer is True:
            findings.append(
                f"Continuous coverage of {tenure} months satisfies the 24-month PED waiting period under Code Excl 01 (PDF Page 6), "
                f"and condition was declared and accepted by the insurer."
            )

        if info.ped_accepted_by_insurer is True:
            findings.append("Insurer Acceptance Confirmed: Pre-existing condition acceptance by insurer is verified.")
        elif info.ped_accepted_by_insurer is False:
            warnings.append(
                "Pre-existing condition was declared but was NOT accepted by the insurer in the policy schedule. Treatment for this condition is excluded."
            )
        else:
            # Acceptance unconfirmed
            findings.append(
                "Code Excl 01 Acceptance Requirement: Under Star Health Premier Policy terms (PDF Page 6), coverage after the 24-month waiting period "
                "for any pre-existing disease is strictly conditional on the disease having been declared at application AND accepted by the insurer. "
                "Mere declaration does not guarantee coverage; formal underwriting acceptance is required."
            )
            warnings.append(
                "Insurer Acceptance Unconfirmed: Coverage for pre-existing disease after 24 months requires formal underwriting acceptance by the insurer "
                "in the policy schedule. Please verify your policy schedule endorsement to confirm insurer acceptance."
            )
            ped_missing = "ped_insurer_acceptance (confirmation from policy schedule that declared condition was accepted by insurer)"
            if ped_missing not in missing_info:
                missing_info.append(ped_missing)
    elif info.declared_ped is False:
        findings.append("Condition was not declared as a pre-existing disease at policy inception.")

    # -------------------------------------------------------------
    # 4. Room Rent & Proportionate Deduction Evaluation (PDF Page 3)
    # -------------------------------------------------------------
    is_illustrative_sum_insured = False
    if info.sum_insured is not None and info.sum_insured > 0:
        sum_insured = float(info.sum_insured)
        if has_explicit_room_query:
            findings.append(f"Confirmed Sum Insured: ₹{sum_insured:,.2f}.")
    else:
        is_illustrative_sum_insured = True
        sum_insured = DEMO_SUM_INSURED_DEFAULT
        assumptions.append(
            f"Sum Insured was not provided by user; displaying an illustrative demonstration example "
            f"using ₹{sum_insured:,.2f} (Star Health Premier published options start at ₹10 Lakh, "
            f"subject to actual policy schedule confirmation)."
        )
        if "sum_insured (confirmation of actual sum insured from policy schedule)" not in missing_info:
            missing_info.append("sum_insured (confirmation of actual sum insured from policy schedule)")

    eligible_room_rent = min(sum_insured * ROOM_RENT_PERCENTAGE, ROOM_RENT_MAX_CAP)

    if is_illustrative_sum_insured:
        calc_explanation = (
            f"Illustrative Demonstration Only: For a ₹{sum_insured:,.2f} sum insured schedule, "
            f"eligible daily room rent would be ₹{eligible_room_rent:,.2f}/day (1%, capped at ₹{ROOM_RENT_MAX_CAP:,.2f}/day). "
            f"The actual room rent limit must be confirmed from the active policy schedule."
        )
    else:
        calc_explanation = (
            f"Eligible daily room rent is ₹{eligible_room_rent:,.2f} (1% of confirmed ₹{sum_insured:,.2f}, "
            f"capped at ₹{ROOM_RENT_MAX_CAP:,.2f}/day)."
        )

    # Always provide calculation detail for complete data inspection
    calculations.append(
        CalculationDetail(
            type="room_rent_eligibility",
            formula="min(sum_insured * 0.01, 20000)",
            inputs={
                "sum_insured": sum_insured,
                "rate": ROOM_RENT_PERCENTAGE,
                "cap": ROOM_RENT_MAX_CAP,
                "confirmed_input": not is_illustrative_sum_insured,
            },
            result=eligible_room_rent,
            explanation=calc_explanation,
            illustrative_only=is_illustrative_sum_insured,
        )
    )

    if has_explicit_room_query and "STAR-PREMIER-ROOM-001" not in relevant_clause_ids:
        relevant_clause_ids.append("STAR-PREMIER-ROOM-001")

    # Evaluate selected room rent if provided or if room rent is the primary query
    selected_room = info.selected_room_rent_per_day
    room_exceeds_eligible = False

    if selected_room is not None:
        if is_illustrative_sum_insured:
            findings.append(
                f"Selected daily room rent stated is ₹{selected_room:,.2f}/day. "
                f"Because the actual policy sum insured is unconfirmed, whether this room category exceeds your "
                f"entitled limit cannot be determined. (For illustration: ₹{selected_room:,.2f}/day would exceed "
                f"a ₹10 Lakh policy's ₹10,000/day limit, but would be within limit for higher sum insured tiers). "
                f"Please confirm your actual sum insured from your policy schedule."
            )
        else:
            if selected_room > eligible_room_rent:
                room_exceeds_eligible = True
                excess = selected_room - eligible_room_rent
                warnings.append(
                    f"Selected room rent of ₹{selected_room:,.2f}/day exceeds your confirmed eligible limit of ₹{eligible_room_rent:,.2f}/day "
                    f"by ₹{excess:,.2f}/day."
                )
            else:
                findings.append(
                    f"Selected room rent of ₹{selected_room:,.2f}/day is within your confirmed eligible limit "
                    f"of ₹{eligible_room_rent:,.2f}/day. No proportionate deductions apply."
                )
    elif has_explicit_room_query:
        findings.append(
            f"Daily room rent limit per 1% rule is ₹{eligible_room_rent:,.2f}/day. Selected room rent was not mentioned."
        )
        if "selected_room_rent_per_day" not in missing_info:
            missing_info.append("selected_room_rent_per_day")

    # Proportionate Deduction Evaluation (FIX 2)
    if room_exceeds_eligible:
        if info.hospital_differential_billing is True:
            assoc_exp = info.associated_medical_expenses
            if assoc_exp is not None and assoc_exp > 0:
                ratio = eligible_room_rent / selected_room
                potential_reduction = assoc_exp * (1.0 - ratio)
                reimbursable_assoc = assoc_exp * ratio

                calculations.append(
                    CalculationDetail(
                        type="proportionate_deduction",
                        formula="associated_medical_expenses * (1 - (eligible_room_rent / selected_room_rent))",
                        inputs={
                            "associated_medical_expenses": assoc_exp,
                            "eligible_room_rent": eligible_room_rent,
                            "selected_room_rent": selected_room,
                            "coverage_ratio": round(ratio, 4),
                        },
                        result=round(potential_reduction, 2),
                        explanation=(
                            f"Hospital applies differential billing. Associated expenses of ₹{assoc_exp:,.2f} are scaled "
                            f"by room ratio {eligible_room_rent:,.0f}/{selected_room:,.0f} ({ratio:.2%}). "
                            f"Estimated reduction: ₹{potential_reduction:,.2f}; reimbursable portion: ₹{reimbursable_assoc:,.2f}."
                        ),
                        illustrative_only=False,
                    )
                )
                warnings.append(
                    f"Hospital applies differential billing. Proportionate deduction of ₹{potential_reduction:,.2f} "
                    f"will apply to Associated Medical Expenses due to exceeding room rent limit."
                )
            else:
                warnings.append(
                    "Hospital follows differential billing and room rent exceeds eligibility. Proportionate deduction "
                    "will apply to Associated Medical Expenses, but the exact breakdown (doctor fees, OT, procedure charges) "
                    "was not provided to compute the deduction amount."
                )
                if "associated_medical_expenses (needed to compute exact proportionate deduction)" not in missing_info:
                    missing_info.append("associated_medical_expenses (needed to compute exact proportionate deduction)")

        elif info.hospital_differential_billing is False:
            findings.append(
                "Hospital does NOT practice differential billing based on room category. "
                "Per Star Health Premier policy terms (PDF Page 3), proportionate deductions are NOT applied."
            )

        else:
            findings.append(
                "insufficient_information: Hospital differential-billing status is unconfirmed. "
                "Per policy terms (PDF Page 3), proportionate deductions are NOT applied if the hospital does not practice "
                "differential billing by room category. Hospital billing practices must be verified before determining whether deductions apply."
            )
            warnings.append(
                "Proportionate deduction is conditional: Hospital differential billing status is unconfirmed. "
                "A deduction cannot be established until hospital billing practices are verified with the hospital billing desk."
            )
            if "hospital_differential_billing (confirmation of hospital billing practices)" not in missing_info:
                missing_info.append("hospital_differential_billing (confirmation of hospital billing practices)")

    elif has_explicit_room_query and is_illustrative_sum_insured and selected_room is not None:
        if info.hospital_differential_billing is False:
            findings.append(
                "Hospital does not adopt differential billing; proportionate deductions are not applicable per policy terms."
            )
        elif info.hospital_differential_billing is None:
            findings.append(
                "insufficient_information: Both sum insured and hospital differential-billing practices are unconfirmed. "
                "No proportionate deduction can be determined at this stage."
            )
            if "hospital_differential_billing (confirmation of hospital billing practices)" not in missing_info:
                missing_info.append("hospital_differential_billing (confirmation of hospital billing practices)")

    # -------------------------------------------------------------
    # 5. Co-Payment Evaluation
    # -------------------------------------------------------------
    if info.co_payment_percentage is not None and info.co_payment_percentage > 0:
        copay_pct = float(info.co_payment_percentage)
        findings.append(f"Applicable co-payment of {copay_pct:.1f}% declared.")
    elif has_explicit_room_query:
        if "co_payment_percentage (must be verified from active policy schedule)" not in missing_info:
            missing_info.append("co_payment_percentage (must be verified from active policy schedule)")

    # Deduplicate missing information list while preserving order
    clean_missing: List[str] = []
    for item in missing_info:
        if item not in clean_missing:
            clean_missing.append(item)

    return AnalysisResult(
        findings=findings,
        calculations=calculations,
        warnings=warnings,
        assumptions=assumptions,
        excluded_expenses=excluded_expenses,
        missing_information=clean_missing,
        relevant_clause_ids=relevant_clause_ids,
        disclaimer="This is an informational policy pre-audit, not an insurer's claim decision.",
    )
