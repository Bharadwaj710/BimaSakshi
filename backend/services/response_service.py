"""
Gnani Timbre v2.5 TTS & Hindi Audio Advisory Service
----------------------------------------------------
Synthesizes personalized Hindi policy guidance based on deterministic rule-engine findings
using Gnani AI's Timbre v2.5 REST API (Voice: Nalini).
"""

import base64
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

from schemas.analysis import AnalysisResult, ExtractedInsuranceInfo, TTSResult

logger = logging.getLogger("bimasakshi.response_service")

DEFAULT_TTS_ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"
DEFAULT_VOICE = "Nalini"
DEFAULT_MODEL = "timbre-v2.5"
DEFAULT_LANGUAGE = "hi-IN"


def get_gnani_api_key() -> str:
    """Retrieves GNANI_API_KEY from environment."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)

    key = (
        os.getenv("GNANI_API_KEY")
        or os.getenv("GNANI_API_KEY_ID")
        or os.getenv("VACHANA_API_KEY")
    )
    if not key or key.strip() in ("", "your_gnani_api_key_here"):
        raise ValueError("GNANI_API_KEY is not configured in .env.")
    return key.strip()


def compose_hindi_advisory_text(
    info: ExtractedInsuranceInfo,
    analysis: AnalysisResult,
) -> str:
    """
    Constructs a context-specific Hindi explanation based on rule-engine findings.
    Prioritizes the user's actual question and primary intent (e.g. accident exception vs room rent).
    Avoids fixed generic canned responses. Never guarantees approval or rejection.
    Strictly aligns with JSON analysis findings and warnings.
    """
    parts = []

    # Detect Accident Findings
    has_accident_exemption = any("does NOT apply to claims arising due to an accident" in f for f in analysis.findings)
    has_accident_unclear = any("insufficient_information: An accident was mentioned" in f for f in analysis.findings)
    is_accident_intent = (
        info.primary_intent == "waiting_period_accident"
        or has_accident_exemption
        or has_accident_unclear
    )

    # Detect Modern Treatment / Robotic Surgery (Coverage 14)
    is_robotic_surgery = (
        any("Coverage 14" in f for f in analysis.findings)
        or any(c.type == "modern_treatment_limit" for c in analysis.calculations)
        or info.primary_intent == "modern_treatment_robotic"
    )

    # Detect Ambiguous Generic Kidney Diagnosis
    is_ambiguous_kidney = (
        any("Ambiguous Diagnosis" in w for w in analysis.warnings)
        or any("generic kidney" in f.lower() for f in analysis.findings)
        or info.primary_intent == "ambiguous_diagnosis"
    )

    # Detect Benefits, Deposit, and Age Ambiguity Findings
    has_benefits_finding = any("In-Patient Hospitalization Benefits" in f for f in analysis.findings)
    has_deposit_finding = any("Hospital Advance Admission Deposit" in f for f in analysis.findings)
    has_age_ambiguity = any("Age Eligibility & Membership Status" in f for f in analysis.findings)

    # Detect ICU Safeguard
    has_icu_finding = any("ICU / ICCU Exemption" in f for f in analysis.findings)

    # Detect Room Rent relevance strictly
    has_room_query = (
        info.selected_room_rent_per_day is not None
        or info.primary_intent in ["room_rent_eligibility", "proportionate_deduction"]
        or any("exceeds your confirmed eligible limit" in w for w in analysis.warnings)
        or (
            info.sum_insured is not None
            and info.primary_intent in ["room_rent_eligibility", "general_claim"]
            and not is_robotic_surgery
            and not is_ambiguous_kidney
            and not is_accident_intent
        )
    )

    eligible_calc = next((c for c in analysis.calculations if c.type == "room_rent_eligibility"), None)
    prop_calc = next((c for c in analysis.calculations if c.type == "proportionate_deduction"), None)
    is_illustrative = eligible_calc.illustrative_only if eligible_calc else (info.sum_insured is None)
    eligible_amt = int(eligible_calc.result) if (eligible_calc and eligible_calc.result) else 10000
    selected_amt = int(info.selected_room_rent_per_day) if info.selected_room_rent_per_day else None

    # Helper to construct room rent text
    def append_room_rent_text(prefix: str = ""):
        if is_illustrative:
            lead = f"{prefix}आपकी पॉलिसी के सम इंश्योर्ड की पुष्टि आवश्यक है। उदाहरण के लिए, दस लाख रुपये की पॉलिसी पर पात्र कमरा किराया {eligible_amt:,} रुपये प्रतिदिन होता है।"
            parts.append(lead.strip())
            if selected_amt:
                parts.append(
                    f"आपके द्वारा बताया गया कमरा किराया {selected_amt:,} रुपये है; वास्तविक पात्रता पॉलिसी शेड्यूल से जांच लें।"
                )
        else:
            if selected_amt and selected_amt > eligible_amt:
                lead = f"{prefix}आपकी स्टार हेल्थ पॉलिसी के अनुसार कमरे का पात्र किराया {eligible_amt:,} रुपये प्रतिदिन है, जबकि अस्पताल में चुना गया किराया {selected_amt:,} रुपये है।"
                parts.append(lead.strip())
                if info.hospital_differential_billing is True:
                    if prop_calc and prop_calc.result:
                        deduction_amt = int(prop_calc.result)
                        parts.append(
                            f"अस्पताल में अलग बिलिंग दरें होने के कारण डॉक्टर और ऑपरेशन खर्चों पर लगभग {deduction_amt:,} रुपये की "
                            f"आनुपातिक कटौती लागू होगी।"
                        )
                    else:
                        parts.append(
                            "अस्पताल में अलग बिलिंग दरें लागू होने पर संबंधित खर्चों पर आनुपातिक कटौती लागू होगी।"
                        )
                elif info.hospital_differential_billing is False:
                    parts.append(
                        "चूंकि अस्पताल में कमरा-वार अलग दरें लागू नहीं हैं, इसलिए आनुपातिक कटौती लागू नहीं होगी।"
                    )
                else:
                    parts.append(
                        "अस्पताल की बिलिंग पद्धति की पुष्टि आवश्यक है; यदि अस्पताल में कमरा-वार अलग दरें नहीं हैं, तो आनुपातिक कटौती लागू नहीं होगी।"
                    )
            elif selected_amt and selected_amt <= eligible_amt:
                lead = f"{prefix}आपके कमरे का किराया {selected_amt:,} रुपये प्रतिदिन पात्र सीमा {eligible_amt:,} रुपये के भीतर है। कमरे के किराए पर कोई कटौती नहीं होगी।"
                parts.append(lead.strip())
            else:
                lead = f"{prefix}आपकी पॉलिसी के तहत कमरे का पात्र किराया {eligible_amt:,} रुपये प्रतिदिन है।"
                parts.append(lead.strip())

    # -------------------------------------------------------------
    # CASE 1: Modern Treatment / Robotic Surgery (Coverage 14)
    # -------------------------------------------------------------
    if is_robotic_surgery:
        modern_calc = next((c for c in analysis.calculations if c.type == "modern_treatment_limit"), None)
        modern_limit_amt = int(modern_calc.result) if (modern_calc and modern_calc.result) else 500000
        is_illustrative_modern = modern_calc.illustrative_only if modern_calc else (info.sum_insured is None)

        if is_illustrative_modern:
            parts.append(
                f"स्टार हेल्थ प्रीमियर पॉलिसी (Section II, Coverage 14 – Modern Treatment) के तहत रोबोटिक सर्जरी पर विशेष कवरेज मिलता है। "
                f"इसके तहत सम इंश्योर्ड का 50% (उदाहरण के लिए दस लाख रुपये की पॉलिसी पर अधिकतम ₹{modern_limit_amt:,}) तक का खर्च कवर होता है, "
                f"जिसमें अस्पताल में भर्ती से पहले और बाद के खर्च भी शामिल हैं। वास्तविक सीमा आपकी पॉलिसी के सम इंश्योर्ड पर निर्भर करेगी।"
            )
        else:
            parts.append(
                f"स्टार हेल्थ प्रीमियर पॉलिसी (Section II, Coverage 14 – Modern Treatment) के तहत रोबोटिक सर्जरी पर विशेष कवरेज उपलब्ध है। "
                f"आपकी ₹{int(info.sum_insured):,} की पॉलिसी के अनुसार, रोबोटिक सर्जरी के लिए सम इंश्योर्ड का 50% यानी अधिकतम ₹{modern_limit_amt:,} "
                f"कवर किया जाएगा, जिसमें प्री और पोस्ट हॉस्पिटलाइजेशन खर्च भी शामिल हैं।"
            )

        if has_room_query:
            append_room_rent_text(prefix="कमरे के किराए के संदर्भ में: ")

    # -------------------------------------------------------------
    # CASE 2: Ambiguous Generic Kidney Diagnosis (Issue 1)
    # -------------------------------------------------------------
    elif is_ambiguous_kidney:
        parts.append(
            "आपने केवल किडनी की सामान्य समस्या का उल्लेख किया है, लेकिन सटीक बीमारी (जैसे पथरी या अन्य बीमारी) स्पष्ट नहीं है। "
            "स्टार हेल्थ प्रीमियर पॉलिसी के अनुसार 24 महीने का विशेष वेटिंग पीरियड केवल किडनी की पथरी (calculi) पर लागू होता है, सभी किडनी बीमारियों पर नहीं। "
            "कृपया अपने डॉक्टर या अस्पताल से सटीक डायग्नोसिस की पुष्टि करें ताकि सही नियमों और वेटिंग पीरियड की जांच की जा सके।"
        )
        if has_room_query:
            append_room_rent_text(prefix="कमरे के किराए के संदर्भ में: ")

    # -------------------------------------------------------------
    # CASE 3: Accident-Related Waiting Period Query (PRIMARY FOCUS)
    # -------------------------------------------------------------
    elif is_accident_intent:
        if has_accident_exemption:
            parts.append(
                "स्टार हेल्थ प्रीमियर पॉलिसी (Code Excl 02, पेज 6) के अनुसार, दुर्घटना (accident) के कारण आवश्यक होने वाले उपचार या सर्जरी पर 24 महीने का वेटिंग पीरियड लागू नहीं होता है। "
                "अतः यदि सर्जरी दुर्घटना के कारण आवश्यक हुई है, तो यह वेटिंग पीरियड से पूर्णतः मुक्त है। इसके लिए अस्पताल के आपातकालीन व दुर्घटना चिकित्सा रिकॉर्ड बीमा कंपनी द्वारा सत्यापित किए जाएंगे।"
            )
        elif has_accident_unclear:
            parts.append(
                "दुर्घटना का उल्लेख किया गया है, लेकिन सर्जरी और दुर्घटना के बीच सीधा चिकित्सीय संबंध अभी स्पष्ट नहीं है। "
                "स्टार हेल्थ प्रीमियर पॉलिसी के अनुसार वेटिंग पीरियड की छूट केवल दुर्घटना के कारण सीधे उत्पन्न दावों पर लागू होती है; "
                "कृपया दुर्घटना संबंधी मेडिकल रिपोर्ट बीमा कंपनी से सत्यापित कराएं।"
            )

        if has_room_query:
            append_room_rent_text(prefix="कमरे के किराए के संदर्भ में: ")

    # -------------------------------------------------------------
    # CASE 4: Specified Disease / Kidney Calculi Waiting Period (Issue 2 - No Accident Mention)
    # -------------------------------------------------------------
    elif info.primary_intent == "waiting_period_specified_disease" and not has_room_query and not (has_benefits_finding or has_deposit_finding):
        if info.policy_tenure_months is not None:
            parts.append(
                f"किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है। वर्तमान पॉलिसी अवधि {info.policy_tenure_months} महीने है; "
                f"कवरेज पूर्व पॉलिसी की निरंतरता व पोर्टेबिलिटी क्रेडिट पर निर्भर करेगा।"
            )
        else:
            parts.append(
                "किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है; कृपया पॉलिसी शुरू होने की तिथि की जांच करें।"
            )

    # -------------------------------------------------------------
    # CASE 4B: Multi-Intent Benefits Inquiry / Hospital Deposit / Specified Disease
    # -------------------------------------------------------------
    elif (has_benefits_finding or has_deposit_finding) and not is_accident_intent and not is_ambiguous_kidney:
        if has_benefits_finding:
            parts.append(
                "स्टार हेल्थ प्रीमियर पॉलिसी के तहत इन-पेशेंट हॉस्पिटलाइजेशन में कमरा किराया (सम इंश्योर्ड का 1%), डॉक्टर व सर्जन फीस, ऑपरेशन थिएटर, दवाएं और आईसीयू खर्च कवर होते हैं।"
            )

        if has_deposit_finding:
            dep_amt = int(info.hospital_deposit) if info.hospital_deposit else 30000
            parts.append(
                f"अस्पताल द्वारा मांगा गया ₹{dep_amt:,} का डिपॉजिट एक अग्रिम सुरक्षा राशि (admission deposit) है, यह बीमा कटौती नहीं है। "
                f"कैशलेस प्री-ऑथराइजेशन स्वीकृत होने पर बीमा कंपनी की स्वीकृत राशि व गैर-भुगतान योग्य मदों (जैसे रजिस्ट्रेशन या कंज्यूमेबल्स) की कटौती के अनुसार ही अस्पताल इसे समायोजित या आंशिक/पूर्ण रिफंड करता है; पूर्ण रिफंड की अग्रिम गारंटी नहीं होती। अन्यथा रीइंबर्समेंट के लिए भुगतान रसीद सुरक्षित रखें।"
            )

        has_waiting_warning = any("Code Excl 02" in w for w in analysis.warnings)
        if has_waiting_warning:
            if info.policy_tenure_months is not None:
                parts.append(
                    f"किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है। वर्तमान पॉलिसी अवधि {info.policy_tenure_months} महीने है; "
                    f"कवरेज पूर्व पॉलिसी की निरंतरता व पोर्टेबिलिटी क्रेडिट पर निर्भर करेगा।"
                )
            else:
                parts.append(
                    "किडनी की पथरी (calculi) की सर्जरी पर कोड एक्सक्लूजन 02 के तहत 24 महीने का वेटिंग पीरियड लागू होता है; यदि आपके पास पूर्व निरंतर बीमा का पोर्टेबिलिटी क्रेडिट है, तो यह वेटिंग पीरियड कम हो सकता है।"
                )

        if has_age_ambiguity:
            age_val = info.age or 24
            parts.append(
                f"आपकी आयु {age_val} वर्ष है; फैमिली फ्लोटर में 25 वर्ष तक आश्रित संतान के रूप में या स्वयं प्राथमिक पॉलिसीधारक के रूप में सदस्यता स्थिति और वास्तविक सम इंश्योर्ड की पुष्टि पॉलिसी शेड्यूल से आवश्यक है।"
            )

        if has_room_query:
            append_room_rent_text(prefix="कमरे के किराए के संदर्भ में: ")

        parts.append("कृपया अस्पताल के टीपीए डेस्क से कैशलेस प्री-ऑथराइजेशन प्रक्रिया शुरू कराएं और पॉलिसी शेड्यूल सत्यापित करें।")

    # -------------------------------------------------------------
    # CASE 5: Pre-Existing Disease (Code Excl 01 - Issue 3)
    # -------------------------------------------------------------
    elif info.primary_intent == "waiting_period_ped" and not has_room_query:
        has_acceptance_unconfirmed = any("Insurer Acceptance Unconfirmed" in w for w in analysis.warnings)
        tenure_str = f" वर्तमान पॉलिसी अवधि {info.policy_tenure_months} महीने है।" if info.policy_tenure_months is not None else ""
        if has_acceptance_unconfirmed:
            parts.append(
                f"स्टार हेल्थ प्रीमियर पॉलिसी (Code Excl 01, पेज 6) के अनुसार घोषित पूर्व-मौजूदा बीमारी (PED) पर 24 महीने का वेटिंग पीरियड लागू होता है।{tenure_str} "
                f"ध्यान दें कि 24 महीने बाद भी कवरेज केवल तभी मिलता है जब बीमारी आवेदन के समय घोषित की गई हो और बीमा कंपनी द्वारा पॉलिसी शेड्यूल में विधिवत स्वीकृत (accepted) की गई हो। "
                f"केवल घोषणा करने मात्र से कवरेज की गारंटी नहीं होती; कृपया पॉलिसी शेड्यूल एंडोर्समेंट में स्वीकृति की पुष्टि करें।"
            )
        elif info.ped_accepted_by_insurer is True:
            if info.policy_tenure_months is not None and info.policy_tenure_months < 24:
                parts.append(
                    f"घोषित पूर्व-मौजूदा बीमारी (जो बीमा कंपनी द्वारा स्वीकृत है) पर 24 महीने का वेटिंग पीरियड लागू होता है। वर्तमान पॉलिसी अवधि {info.policy_tenure_months} महीने है।"
                )
            else:
                parts.append(
                    "आपकी घोषित पूर्व-मौजूदा बीमारी बीमा कंपनी द्वारा स्वीकृत है और 24 महीने की पॉलिसी अवधि पूरी होने के कारण यह कवर्ड है।"
                )
        else:
            parts.append(
                "घोषित पूर्व-मौजूदा बीमारी पर 24 महीने का वेटिंग पीरियड लागू होता है; पॉलिसी प्रपोजल फॉर्म में घोषणा और बीमाकर्ता की स्वीकृति की पुष्टि आवश्यक है।"
            )

    # -------------------------------------------------------------
    # CASE 6: Room Rent / General Planned Hospitalization Claim
    # -------------------------------------------------------------
    else:
        if has_room_query:
            append_room_rent_text()

        # Mention waiting period if applicable
        has_waiting_warning = any("Code Excl 02" in w for w in analysis.warnings)
        if has_waiting_warning:
            if info.policy_tenure_months is not None:
                parts.append(
                    f"किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है। वर्तमान पॉलिसी अवधि {info.policy_tenure_months} महीने है; "
                    f"कवरेज पूर्व पॉलिसी की पोर्टेबिलिटी निरंतरता पर निर्भर करेगा।"
                )
            else:
                parts.append(
                    "किडनी की पथरी के उपचार पर 24 महीने का वेटिंग पीरियड लागू होता है; कृपया पॉलिसी शुरू होने की तिथि की जांच करें।"
                )

        if any("hospital_differential_billing" in m for m in analysis.missing_information):
            parts.append("अस्पताल की बिलिंग पद्धति की पुष्टि करना आवश्यक है।")

        if has_age_ambiguity and not any("सदस्यता स्थिति" in p for p in parts):
            age_val = info.age or 24
            parts.append(
                f"आपकी आयु {age_val} वर्ष है; कृपया पॉलिसी शेड्यूल से आश्रित संतान या प्राथमिक पॉलिसीधारक सदस्यता स्थिति की पुष्टि करें।"
            )

    # Mention Hospital Deposit if present and not yet mentioned
    if has_deposit_finding and not any("डिपॉजिट" in p for p in parts):
        dep_amt = int(info.hospital_deposit) if info.hospital_deposit else 30000
        parts.append(
            f"अस्पताल द्वारा मांगा गया ₹{dep_amt:,} का डिपॉजिट एक अग्रिम सुरक्षा राशि (admission deposit) है, यह बीमा कटौती नहीं है। "
            f"कैशलेस स्वीकृति के बाद स्वीकृत राशि व गैर-भुगतान योग्य मदों की कटौती के अनुसार अस्पताल इसे समायोजित करता है; पूर्ण रिफंड की अग्रिम गारंटी नहीं होती।"
        )

    # Mention ICU Safeguard
    if has_icu_finding:
        parts.append("आईआरडीएआई और पॉलिसी नियमों के अनुसार आईसीयू (ICU) शुल्क पर कोई आनुपातिक कटौती लागू नहीं होगी।")

    # Mention unindexed benefits if flagged
    has_unindexed = any("is not indexed in the demonstration policy database" in f for f in analysis.findings)
    if has_unindexed:
        parts.append(
            "पूछी गई विशेष चिकित्सा सुविधा वर्तमान डेमो डेटाबेस में अनुक्रमित नहीं है; कृपया पूर्ण पॉलिसी नियमों से इसकी पुष्टि करें।"
        )

    # Standard Closing
    parts.append(
        "कृपया अस्पताल के इंश्योरेंस डेस्क या बीमा कंपनी से बिल जमा करने से पहले अंतिम पुष्टि अवश्य करें।"
    )

    return " ".join(parts)


def synthesize_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
    timeout_sec: float = 30.0,
) -> TTSResult:
    """
    Submits Hindi text to Gnani Timbre v2.5 and returns base64-encoded WAV audio.
    Fails gracefully without crashing if TTS endpoint encounters an error.
    """
    tts_endpoint = os.getenv("GNANI_TTS_ENDPOINT", DEFAULT_TTS_ENDPOINT)

    try:
        api_key = get_gnani_api_key()
    except Exception as e:
        logger.error(f"Cannot synthesize speech: {e}")
        return TTSResult(
            status="failed",
            model=model,
            spoken_text=text,
            error=f"Credentials error: {e}",
        )

    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": api_key,
    }

    payload = {
        "text": text,
        "voice": voice,
        "model": model,
        "language": language,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    start_time = time.perf_counter()
    try:
        logger.info(f"Submitting TTS synthesis request to Timbre v2.5 ({voice}, {len(text)} chars)...")
        response = requests.post(
            tts_endpoint,
            headers=headers,
            json=payload,
            timeout=timeout_sec,
        )
    except requests.exceptions.Timeout:
        latency = time.perf_counter() - start_time
        logger.warning(f"Timbre TTS request timed out after {latency:.2f}s")
        return TTSResult(
            status="failed",
            model=model,
            spoken_text=text,
            error=f"Timbre TTS timed out after {latency:.2f}s",
        )
    except Exception as e:
        logger.warning(f"Timbre TTS connection error: {e}")
        return TTSResult(
            status="failed",
            model=model,
            spoken_text=text,
            error=f"Timbre TTS connection failed: {e}",
        )

    latency = round(time.perf_counter() - start_time, 2)

    if response.status_code == 200:
        raw_bytes = response.content
        audio_bytes: Optional[bytes] = None

        if raw_bytes.startswith(b"RIFF") or "audio" in response.headers.get("Content-Type", ""):
            audio_bytes = raw_bytes
        else:
            try:
                resp_json = response.json()
                for key in ("audio_content", "audio", "data", "audio_data"):
                    if key in resp_json and isinstance(resp_json[key], str):
                        audio_bytes = base64.b64decode(resp_json[key])
                        break
            except Exception:
                pass

        if audio_bytes and len(audio_bytes) > 0:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"Timbre TTS synthesis succeeded in {latency}s ({len(audio_bytes):,} bytes).")
            return TTSResult(
                status="success",
                model=model,
                audio_base64=b64_audio,
                mime_type="audio/wav",
                spoken_text=text,
            )

    logger.warning(f"Timbre TTS returned HTTP {response.status_code}: {response.text[:200]}")
    return TTSResult(
        status="failed",
        model=model,
        spoken_text=text,
        error=f"Timbre HTTP {response.status_code}: {response.text[:200]}",
    )
