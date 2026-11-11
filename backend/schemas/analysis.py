"""
Pydantic Schemas for Audio Claim Analysis (Phase 3)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class UnitAmountItem(BaseModel):
    """Preserves an explicit numeric quantity or financial amount with its stated unit."""
    parameter: str = Field(description="Name of parameter, e.g. age, sum_insured, tenure, room_rent")
    stated_value: str = Field(description="Preserved value and unit, e.g. '52 years', '10,00,000 INR', '14 months', '30,000 per day'")


class ExtractedInsuranceInfo(BaseModel):
    """
    Structured extraction of patient, hospital, and policy details from user audio.
    Distinguishes strictly between null (unknown/unmentioned) and 0 / False.
    """
    age: Optional[int] = Field(
        default=None,
        description="Patient age in years, or null if unmentioned",
    )
    sum_insured: Optional[float] = Field(
        default=None,
        description="Policy sum insured amount in INR, or null if not explicitly supplied",
    )
    policy_start_date: Optional[str] = Field(
        default=None,
        description="Policy inception/start date if stated (e.g. YYYY-MM-DD), or null",
    )
    policy_tenure_months: Optional[int] = Field(
        default=None,
        description="Number of continuous coverage months completed, or null",
    )
    diagnosis_or_condition: Optional[str] = Field(
        default=None,
        description="Primary medical condition or diagnosis stated, or null",
    )
    treatment_type: Optional[str] = Field(
        default=None,
        description="Specific surgery or treatment type mentioned, or null",
    )
    selected_room_rent_per_day: Optional[float] = Field(
        default=None,
        description="Hospital daily room rent chosen/billed in INR, or null",
    )
    hospital_deposit: Optional[float] = Field(
        default=None,
        description="Advance admission or security deposit requested by the hospital in INR (strictly distinct from room rent or total bill), or null",
    )
    membership_status: Optional[str] = Field(
        default=None,
        description="Membership/enrolment status under policy: 'primary_insured', 'dependent_child', 'spouse', or null if unconfirmed",
    )
    eligible_room_rent_per_day: Optional[float] = Field(
        default=None,
        description="Eligible room rent if explicitly declared by the user, or null",
    )
    estimated_hospital_bill: Optional[float] = Field(
        default=None,
        description="Total estimated or billed hospital charges in INR, or null",
    )
    associated_medical_expenses: Optional[float] = Field(
        default=None,
        description="Doctor, OT, and procedure charges that vary by room rent, or null",
    )
    pharmacy_expenses: Optional[float] = Field(
        default=None,
        description="Pharmacy and consumable charges in INR (non-associated), or null",
    )
    diagnostic_expenses: Optional[float] = Field(
        default=None,
        description="Diagnostic scan / test charges in INR (non-associated), or null",
    )
    co_payment_percentage: Optional[float] = Field(
        default=None,
        description="Explicitly confirmed co-payment percentage (0-100), or null",
    )
    hospital_differential_billing: Optional[bool] = Field(
        default=None,
        description="True if hospital practices room-category differential billing, False if uniform, null if unknown",
    )
    declared_ped: Optional[bool] = Field(
        default=None,
        description="True if condition was declared in proposal form at inception, null if unknown",
    )
    ped_accepted_by_insurer: Optional[bool] = Field(
        default=None,
        description="True if insurer explicitly accepted declared PED in policy schedule/endorsement, False if rejected, null if unconfirmed",
    )
    icu_charges: Optional[float] = Field(
        default=None,
        description="ICU/ICCU charges in INR (strictly exempt from proportionate deductions per IRDAI), or null",
    )
    is_robotic_surgery: Optional[bool] = Field(
        default=None,
        description="True if procedure involves robotic surgery under Coverage 14 Modern Treatment, null if not mentioned",
    )
    continuity_of_coverage: Optional[bool] = Field(
        default=None,
        description="True if continuous coverage/portability without break is confirmed, null if unknown",
    )
    primary_intent: str = Field(
        default="general_claim",
        description=(
            "Primary question or intent of the user. Dynamically identified from speech "
            "(e.g., 'room_rent_eligibility', 'proportionate_deduction', 'waiting_period_specified_disease', "
            "'waiting_period_ped', 'waiting_period_accident', 'pre_post_hospitalization', 'co_payment', etc.)"
        ),
    )
    identified_intents: List[str] = Field(
        default_factory=list,
        description="List of all distinct insurance topics/intents dynamically identified in the speech",
    )
    retrieval_queries: List[str] = Field(
        default_factory=list,
        description="Decomposed, targeted English retrieval queries generated for each identified intent",
    )
    insurer_mentioned: Optional[str] = Field(
        default=None,
        description="Name of insurer explicitly stated in speech, or null if unmentioned",
    )
    product_mentioned: Optional[str] = Field(
        default=None,
        description="Name of insurance product explicitly stated in speech, or null if unmentioned",
    )
    units_and_amounts: List[UnitAmountItem] = Field(
        default_factory=list,
        description="Preserved explicit quantities, financial amounts, and their stated units",
    )
    is_accident_related: Optional[bool] = Field(
        default=None,
        description="True if the medical treatment/surgery is stated to arise from an accident; False if explicitly not; null if unmentioned",
    )
    accident_causal_relationship: Optional[str] = Field(
        default=None,
        description=(
            "Causal relationship between accident and treatment: "
            "'clear' (treatment is directly due to the accident), "
            "'unclear' (accident is mentioned, but relationship to treatment is uncertain or unverified), "
            "null (no accident mentioned)"
        ),
    )
    user_question: Optional[str] = Field(
        default=None,
        description="Explicit question or topic asked by the user, if any",
    )
    normalized_english_query: str = Field(
        default="",
        description="Normalized English search query for ChromaDB semantic retrieval",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="List of critical claim or policy variables not provided in user audio",
    )


class TranscriptionResult(BaseModel):
    text: str = Field(..., description="Actual transcript from Gnani Prisma")
    model: str = Field(default="prisma-v2.5", description="Prisma model identifier")
    request_id: Optional[str] = Field(default=None, description="Gnani request correlation ID")
    latency_sec: Optional[float] = Field(default=None, description="STT response latency in seconds")


class PolicyDocumentInfo(BaseModel):
    insurer: str
    product_name: str
    uin: str
    document_version: str
    section_code: str
    pdf_url: str


class RetrievedClauseInfo(BaseModel):
    clause_id: str
    clause_title: str
    retrieved_text: str
    source_page: str
    distance: float
    policy_info: PolicyDocumentInfo


class CalculationDetail(BaseModel):
    type: str = Field(..., description="Calculation category, e.g. room_rent_eligibility, proportionate_deduction")
    formula: str = Field(..., description="Mathematical formula applied")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Numerical inputs used")
    result: Optional[float] = Field(default=None, description="Calculated value")
    explanation: str = Field(..., description="Clear, plain-English explanation of rule outcome")
    illustrative_only: bool = Field(default=False, description="True if calculation is based on an assumed demonstration value rather than confirmed user policy input")


class AnalysisResult(BaseModel):
    findings: List[str] = Field(default_factory=list, description="Key policy findings from rule engine")
    calculations: List[CalculationDetail] = Field(default_factory=list, description="Deterministic financial deductions and eligibility calculations")
    warnings: List[str] = Field(default_factory=list, description="Discrepancies, deductions, or exclusions requiring attention")
    assumptions: List[str] = Field(default_factory=list, description="Demonstration defaults or assumed conditions applied")
    excluded_expenses: List[str] = Field(default_factory=list, description="Expenses excluded from proportionate deduction (pharmacy, diagnostics, implants)")
    missing_information: List[str] = Field(default_factory=list, description="Parameters absent that prevent definitive evaluation")
    relevant_clause_ids: List[str] = Field(default_factory=list, description="Referenced policy clause IDs")
    checklist: List[str] = Field(
        default_factory=list,
        description="Actionable pre-admission checklist items for hospital desk and TPA reconciliation",
    )
    disclaimer: str = Field(
        default="This is an informational policy pre-audit, not an insurer's claim decision.",
        description="Regulatory disclaimer",
    )


class TTSResult(BaseModel):
    status: str = Field(..., description="Status of TTS synthesis ('success', 'failed', 'skipped')")
    model: str = Field(default="timbre-v2.5", description="Timbre model identifier")
    audio_base64: Optional[str] = Field(default=None, description="Base64-encoded WAV audio data")
    mime_type: Optional[str] = Field(default="audio/wav", description="MIME type of synthesized audio")
    spoken_text: Optional[str] = Field(default=None, description="Hindi text submitted for synthesis")
    error: Optional[str] = Field(default=None, description="Error message if TTS failed")


class AudioAnalysisResponse(BaseModel):
    status: str = Field(..., description="'success' or 'error'")
    transcription: TranscriptionResult
    extracted_information: ExtractedInsuranceInfo
    retrieved_clauses: List[RetrievedClauseInfo]
    analysis: AnalysisResult
    tts: TTSResult

