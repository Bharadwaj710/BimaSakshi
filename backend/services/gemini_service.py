"""
Gemini Information Extraction Service
-------------------------------------
Extracts structured insurance entities from Hindi/Hinglish transcripts
and normalizes the query into English for ChromaDB semantic retrieval.
Uses the official Google Gen AI SDK (google-genai).
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from schemas.analysis import ExtractedInsuranceInfo

logger = logging.getLogger("bimasakshi.gemini_service")

# Configurable model with fallback
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class GeminiServiceError(Exception):
    """Custom exception for Gemini extraction failures."""
    pass


def get_gemini_client() -> genai.Client:
    """Initializes and returns the Google Gen AI client with v1beta endpoint."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise GeminiServiceError("GEMINI_API_KEY is not configured in .env.")

    return genai.Client(
        api_key=api_key.strip(),
        http_options=types.HttpOptions(api_version="v1beta"),
    )


EXTRACTION_SYSTEM_PROMPT = """You are a senior health insurance medical intake auditor and expert query understanding engine for BimaSakshi.
Your task is to analyze transcripts of patient speech in Hindi, Hinglish, or English, extract structured facts with extreme precision, dynamically understand all distinct insurance intents, and decompose queries into focused retrieval queries.

CRITICAL INSTRUCTIONS:

1. ENTITY EXTRACTION & NUMERICAL PRESERVATION:
   - Extract ONLY what the speaker explicitly stated.
   - Preserve exact numeric quantities, financial values, and stated units:
     * age: integer patient age in years (or null).
     * sum_insured: numeric INR value (e.g. "10,00,000" or "10 lakh" -> 1000000.0).
     * policy_tenure_months: integer months completed (e.g. "14 month", "14 महीने", "1.5 years" -> 18).
     * selected_room_rent_per_day: numeric daily room rent in INR (e.g. "30,000 per day" -> 30000.0). MUST be a daily room rate.
     * hospital_deposit: numeric advance admission / security deposit in INR requested by the hospital (e.g. "30,000 deposit maang raha hai", "advance deposit 30000", "hospital ne 30000 deposit manga" -> 30000.0).
       CRITICAL: NEVER map an advance admission/security deposit to 'selected_room_rent_per_day' or 'estimated_hospital_bill'! They are completely distinct concepts.
     * membership_status: 'primary_insured' (if adult policyholder), 'dependent_child' (if child/dependent under floater), or null if unconfirmed.
     * hospital_differential_billing: Set to True if transcript indicates hospital bills differently across room categories (e.g. "हॉस्पिटल डिफरेंट रूम कैटेगरीज़ के हिसाब से बिल करता है" or "different room charges apply"); Set to False if hospital bills uniformly; Set to null if unmentioned or unknown.
     * diagnosis_or_condition: primary medical condition, illness, or diagnosis stated (or null).
     * treatment_type: surgery or medical procedure type mentioned (or null).
     * insurer_mentioned: insurer name if stated (e.g. "Star Health").
     * product_mentioned: plan/product name if stated (e.g. "Star Health Premier").
     * units_and_amounts: list of items preserving all stated numerical quantities with their units, with parameter and stated_value (e.g. parameter="age", stated_value="24 years"; parameter="deposit", stated_value="30,000 INR deposit"; parameter="sum_insured", stated_value="10,00,000 INR"; parameter="policy_tenure", stated_value="14 months"; parameter="room_rent", stated_value="30,000/day INR").
   - Unknown or unmentioned fields MUST remain null. NEVER invent or assume values.

2. DYNAMIC INTENT DETECTION:
   - Dynamically identify ALL distinct insurance questions or topics present in the transcript and store them in 'identified_intents'.
   - Do NOT force every transcript into a rigid single intent. Transcripts frequently contain multiple distinct questions or concerns.
   - Examples of possible intents (open-ended, general-purpose):
     * 'benefits_inquiry': User asks what benefits, coverages, or hospital expenses their policy provides (e.g. "kya benefits milenge", "policy me kya kya cover hoga", "kya benefits hai").
     * 'hospital_deposit_inquiry': User asks about or mentions an advance security/admission deposit demanded by the hospital (e.g. "30,000 deposit manga hai", "deposit ka kya rule hai").
     * 'age_eligibility_inquiry': User mentions age where policy eligibility or dependent status needs clarification (e.g. 24-year-old child dependent vs primary proposer).
     * 'modern_treatment_robotic': Robotic surgeries, modern / advanced treatments (Section II Coverage 14, 50% sum insured limit). Do NOT confuse robotic surgery with bariatric surgery!
     * 'ambiguous_diagnosis': Generic condition without specific clinical diagnosis (e.g., "kidney ki problem" or "kidney problem" without mentioning calculi/stones/nephrolithiasis).
     * 'room_rent_eligibility': Daily room rent limits, room category capping, 1% sum insured rules.
     * 'proportionate_deduction': Ratable reduction on associated medical expenses due to differential billing.
     * 'waiting_period_specified_disease': 24-month waiting periods for specified illnesses/surgeries (e.g. kidney calculi/stones, hernia, cataracts, joint replacements).
     * 'waiting_period_ped': Pre-existing disease exclusions (Code Excl 01) and waiting periods (requires declaration AND insurer acceptance).
     * 'waiting_period_accident': Exception to waiting periods for accidental trauma or emergency injuries.
     * 'sum_insured_limits': Total coverage limits, sum insured sufficiency.
     * 'co_payment': Mandatory or voluntary co-payment percentage obligations.
     * 'pre_post_hospitalization': Coverage for expenses 60 days prior and 90/180 days post discharge.
     * 'day_care_procedures': Surgeries/procedures requiring less than 24 hours hospitalization.
     * 'excluded_expenses': Non-payable items (pharmacy consumables, gloves, administrative charges).
     * 'continuity_and_portability': Portability credit from prior continuous policies.
     * 'claim_procedure_and_documents': Hospital admission, cashless authorization, TPA documents.
   - Set 'primary_intent' to the most prominent or first identified intent.

3. DYNAMIC QUERY DECOMPOSITION:
   - For EACH distinct intent in 'identified_intents', generate a separate, high-signal, targeted English search query in 'retrieval_queries'.
   - DO NOT concatenate multiple distinct topics into one noisy, diluted query.
   - Include specific policy terminology, clause titles, or section identifiers where applicable:
     * For benefits inquiry / in-patient hospitalization: "Star Health Premier Section B Coverage 1 In-Patient Hospitalization room rent surgeon OT charges medicines benefits"
     * For modern treatment / robotic surgery: "Star Health Premier Section II Coverage 14 Coverage for Modern Treatment robotic surgery 50 percent sum insured limit"
     * For room rent & proportionate deduction: "Star Health Premier Room Rent and Associated Medical Expenses Limit 1 percent sum insured proportionate deduction differential billing"
     * For specified disease / kidney calculi: "Star Health Premier Code Excl 02 24 consecutive months continuous coverage waiting period kidney calculi surgery"
     * For accident waiting period waiver: "Star Health Premier Code Excl 02 waiting period accident exception 24 months surgery"
     * For pre-existing diseases: "Star Health Premier Code Excl 01 pre-existing disease 24 months waiting period declaration acceptance"
     * For other topics (co-pay, pre-post, day-care): generate precise English queries referencing Star Health Premier policy terms.
   - Populate 'normalized_english_query' with the primary query or join of queries.

4. DIAGNOSIS PRECISION (KIDNEY & PED):
   - If user states a generic kidney problem ("kidney ki problem", "kidney problem", "kidney issue") WITHOUT explicit calculi/stones/pathari:
     * Keep diagnosis_or_condition as "kidney problem" (do NOT assume or invent calculi/stones).
     * Set primary_intent to "ambiguous_diagnosis".
   - If user explicitly states kidney stone, renal calculi, or pathari:
     * Set diagnosis_or_condition to "kidney calculi" and intent to "waiting_period_specified_disease".
   - For pre-existing conditions:
     * Set declared_ped to True if disclosed.
     * Set ped_accepted_by_insurer to True ONLY if explicit acceptance in policy schedule is stated; otherwise leave null.

5. ACCIDENT STATUS & CAUSALITY:
   - 'is_accident_related': True if surgery/treatment is necessitated by an accident; False if explicitly non-accident; null if unmentioned.
   - 'accident_causal_relationship':
     * 'clear': if speaker explicitly states treatment is required directly because of an accident.
     * 'unclear': if accident is mentioned, but the direct causal link to the planned surgery is ambiguous, separate, or unconfirmed.
     * null: if no accident is mentioned.

6. STRICT FACTUAL GROUNDING:
   - NEVER assume a disease is pre-existing (PED) merely because of patient age.
   - DO NOT assume co-payment or deductions without explicit user statement.
   - Populate 'missing_information' with an explicit list of critical variables absent from the speech.
"""


def extract_insurance_info(
    transcript: str,
    model_override: Optional[str] = None,
) -> ExtractedInsuranceInfo:
    """
    Extracts structured insurance entities from a speech transcript.

    Args:
        transcript: User's spoken transcript (Hindi, Hinglish, or English).
        model_override: Optional model name to override default.

    Returns:
        ExtractedInsuranceInfo: Validated Pydantic model.

    Raises:
        GeminiServiceError: On API or validation failure.
    """
    if not transcript or not transcript.strip():
        logger.warning("Empty transcript provided to Gemini extraction.")
        return ExtractedInsuranceInfo(
            missing_information=["Full statement is empty or inaudible."],
            normalized_english_query="",
        )

    model_name = model_override or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    client = get_gemini_client()

    prompt = f"Patient Spoken Transcript:\n\"\"\"{transcript.strip()}\"\"\"\n\nExtract all insurance entities into the defined structured schema."

    config = types.GenerateContentConfig(
        system_instruction=EXTRACTION_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=ExtractedInsuranceInfo,
        temperature=0.0,
    )

    try:
        logger.info(f"Submitting transcript to Gemini extraction ({model_name})...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )
    except Exception as e:
        logger.error(f"Gemini API request failed: {e}")
        raise GeminiServiceError(f"Gemini information extraction failed: {e}") from e

    if not response or not response.text:
        raise GeminiServiceError("Gemini returned an empty response.")

    try:
        extracted = ExtractedInsuranceInfo.model_validate_json(response.text)

        # Post-process for consistency
        if extracted.retrieval_queries and not extracted.normalized_english_query:
            extracted.normalized_english_query = " | ".join(extracted.retrieval_queries)
        elif not extracted.retrieval_queries and extracted.normalized_english_query:
            extracted.retrieval_queries = [extracted.normalized_english_query.strip()]

        if extracted.identified_intents and (extracted.primary_intent == "general_claim" or not extracted.primary_intent):
            extracted.primary_intent = extracted.identified_intents[0]

        logger.info(
            f"Extraction successful: condition='{extracted.diagnosis_or_condition}', "
            f"intents={extracted.identified_intents}, queries={len(extracted.retrieval_queries)}, "
            f"room_rent={extracted.selected_room_rent_per_day}"
        )
        return extracted
    except Exception as ve:
        logger.error(f"Pydantic schema validation error on Gemini output: {ve}")
        raise GeminiServiceError(f"Failed to validate extracted information against schema: {ve}") from ve

