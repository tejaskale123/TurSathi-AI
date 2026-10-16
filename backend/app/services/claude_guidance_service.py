import json
import logging
from typing import Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models.tur_scan import TurScan
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation
from app.schemas.claude_guidance import ClaudeGuidanceResponse, SprayGuidanceDetails

logger = logging.getLogger("tursathi.services.claude_guidance")


# ── Language Helper Translations ──────────────────────────────────────────────

LOW_CONFIDENCE_DATA: Dict[str, Dict[str, object]] = {
    "en": {
        "explanation": "The image prediction confidence is below 60%. We cannot confirm the disease diagnosis with sufficient certainty to provide chemical spray guidance.",
        "actions": [
            "Please capture another clear photo of the Tur leaf under good daylight.",
            "Inspect the field for additional symptoms on upper and lower leaf surfaces.",
            "Consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer before spraying."
        ]
    },
    "mr": {
        "explanation": "तपासणीची अचूकता ६०% पेक्षा कमी आहे. पुरेशा खात्रीशिवाय औषध फवारणीचे मार्गदर्शन देणे सुरक्षित नाही.",
        "actions": [
            "कृपया चांगल्या सूर्यप्रकाशात तुरीच्या पानाचा नवीन व स्पष्ट फोटो घ्या.",
            "पानाच्या वरच्या व खालच्या बाजूवरील लक्षणांची काळजीपूर्वक पाहणी करा.",
            "कोणतेही कीटकनाशक फवारण्यापूर्वी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी सहायकाचा सल्ला घ्या."
        ]
    },
    "hi": {
        "explanation": "पूर्वानुमान का विश्वास स्तर 60% से कम है। पर्याप्त निश्चितता के बिना रासायनिक छिड़काव सलाह देना सुरक्षित नहीं है।",
        "actions": [
            "कृपया अच्छी रोशनी में अरहर की पत्ती का एक स्पष्ट चित्र दोबारा लें।",
            "पत्ती की ऊपरी और निचली सतह पर अन्य लक्षणों का निरीक्षण करें।",
            "छिड़काव करने से पहले अपने स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से परामर्श लें।"
        ]
    }
}

HEALTHY_DATA: Dict[str, Dict[str, object]] = {
    "en": {
        "explanation": "The Tur leaf appears healthy with no visual symptoms of Leaf Spot, Sterility Mosaic, or Leaf Webber detected.",
        "actions": [
            "Continue regular field monitoring twice a week.",
            "Maintain optimal irrigation and balanced fertilization.",
            "Keep the field clean and weed-free to prevent pest harborage."
        ]
    },
    "mr": {
        "explanation": "तुरीचे पान निरोगी दिसत असून पानावर टिपके, वांझ रोग किंवा पानावरील आळीची कोणतीही लक्षणे आढळलेली नाहीत.",
        "actions": [
            "आठवड्यातून दोनदा शेताची नियमित पाहणी करत राहा.",
            "योग्य पाणी व्यवस्थापन व संतुलित खतमात्रा द्या.",
            "कीड व रोगाचा प्रादुर्भाव टाळण्यासाठी शेत तणमुक्त व स्वच्छ ठेवा."
        ]
    },
    "hi": {
        "explanation": "अरहर की पत्ती स्वस्थ दिखाई दे रही है और इस पर कोई रोग का लक्षण नहीं मिला है।",
        "actions": [
            "सप्ताह में दो बार खेत का नियमित निरीक्षण जारी रखें।",
            "उचित सिंचाई और संतुलित उर्वरक प्रबंधन बनाए रखें।",
            "खरपतवार नियंत्रण रखें ताकि कीटों का प्रसार न हो।"
        ]
    }
}

LEAF_WEBBER_DATA: Dict[str, Dict[str, object]] = {
    "en": {
        "explanation": "Leaf webber (Grapholita critica Meyr.) is a pest of pigeonpea whose larvae web terminal leaves together and feed inside. Verified chemical spray guidance is currently unavailable for this pest. Do not use unapproved or banned chemicals.",
        "actions": [
            "Inspect terminal shoots and webbed leaf clusters regularly.",
            "Manually collect and destroy folded leaves with larvae in early stages where feasible.",
            "Please consult your local Krishi Vigyan Kendra (KVK) or agricultural officer for currently approved safe management practices."
        ]
    },
    "mr": {
        "explanation": "पाने गुंडाळणारी आळी (Leaf webber / Grapholita critica) ही तुरीवरील कीड असून अळ्या शेंड्याची पाने जाळ्याने एकत्र बांधून आतून खातात. या किडीसाठी प्रमाणित रासायनिक फवारणी मार्गदर्शन सध्या उपलब्ध नाही. अनधिकृत किंवा बंदी घातलेली कीटकनाशके वापरू नका.",
        "actions": [
            "शेंड्याकडील पाने आणि जाळी बांधलेल्या पानांची नियमित पाहणी करा.",
            "सुरुवातीच्या काळात जाळी झालेली पाने आळीसह तोडून नष्ट करा.",
            "सध्याच्या अधिकृत व सुरक्षित कीड नियंत्रण उपायांसाठी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांचा सल्ला घ्या."
        ]
    },
    "hi": {
        "explanation": "लीफ वेबर (Grapholita critica) तूर की एक कीट है जिसकी इल्लियां शीर्ष पत्तियों को आपस में जाले से बांधकर अंदर खाती हैं। इस कीट के लिए सत्यापित रासायनिक छिड़काव मार्गदर्शन वर्तमान में उपलब्ध नहीं है। अनधिकृत या प्रतिबंधित रसायनों का उपयोग न करें।",
        "actions": [
            "शीर्ष पत्तियों और जाले वाले गुच्छों का नियमित निरीक्षण करें।",
            "शुरुआती अवस्था में जाले वाली पत्तियों को इल्ली सहित इकट्ठा कर नष्ट करें।",
            "वर्तमान में स्वीकृत सुरक्षित प्रबंधन उपायों के लिए स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।"
        ]
    }
}


def _get_lang_key(language: str) -> str:
    lang = (language or "en").strip().lower()
    return lang if lang in ("en", "mr", "hi") else "en"


def _is_seed_treatment(rec: Optional[TurDiseaseRecommendation]) -> bool:
    """Returns True if the recommendation is a seed treatment (not a foliar spray)."""
    if not rec:
        return False
    app = (rec.application_method or "").lower()
    return "seed treatment" in app or "seed treat" in app


# Localized important alerts for seed treatment (not a foliar spray)
SEED_TREATMENT_ALERT: Dict[str, str] = {
    "en": "This is a SEED TREATMENT — apply before sowing, not as a foliar spray. Trichoderma viride is a biological agent. Follow the product label instructions.",
    "mr": "हे बियाणे उपचार आहे — पेरणीपूर्वी वापरावे, पान फवारणी नाही. Trichoderma viride एक जैविक बुरशीनाशक आहे. उत्पादनाच्या label वरील सूचनांचे पालन करा.",
    "hi": "यह बीज उपचार है — बुवाई से पहले उपयोग करें, पत्तियों पर छिड़काव नहीं। Trichoderma viride एक जैविक फफूंदनाशक है। उत्पाद के label पर दिए निर्देशों का पालन करें।",
}


def _build_fallback_guidance(
    scan: TurScan,
    rec: Optional[TurDiseaseRecommendation],
    language: str,
    warnings: List[str]
) -> ClaudeGuidanceResponse:
    lang_key = _get_lang_key(language)
    conf_pct = int(round((scan.confidence or 0.0) * 100)) if scan.confidence is not None else 0

    if not rec:
        return ClaudeGuidanceResponse(
            status="fallback",
            crop="tur",
            disease_name=scan.disease_name,
            confidence=scan.confidence,
            confidence_percent=conf_pct,
            disease_explanation=f"Detected disease: {scan.disease_name}. Verified spray guidance is currently unavailable for this disease.",
            farmer_action=["Monitor crop condition closely.", "Please consult a qualified agricultural expert before applying any pesticide."],
            spray_guidance_available=False,
            ai_guidance_available=True,
            spray_guidance=None,
            warnings=warnings + ["Verified spray guidance is currently unavailable for this disease."],
            language=lang_key,
        )

    is_seed = _is_seed_treatment(rec)

    verified_details = SprayGuidanceDetails(
        treatment=rec.treatment,
        active_ingredient=rec.active_ingredient,
        recommended_quantity=rec.recommended_quantity,
        water_quantity=rec.water_quantity,
        per_pump_quantity=rec.per_pump_quantity,
        spray_timing=rec.spray_timing,
        application_method=rec.application_method,
        safety_precautions=rec.safety_precautions,
        after_spray_advisory=rec.after_spray_advisory,
    )

    if lang_key == "mr":
        explanation = f"आढळलेला रोग: {rec.disease_name}. {rec.disease_description or ''}"
        if is_seed:
            actions = [
                f"प्रमाणित बियाणे उपचार वापरा: {rec.treatment or 'कृषी सल्लागाराचा सल्ला घ्या'}.",
                f"प्रमाण: {rec.recommended_quantity or 'लेबलनुसार'}.",
                "बियाणे उपचारानंतर सावलीत वाळवा, उन्हात नाही.",
                "उपचारित बियाणे हाताळताना हात धुवा."
            ]
        else:
            actions = [
                f"प्रमाणित उपचार वापरा: {rec.treatment or 'कृषी सल्लागाराचा सल्ला घ्या'}.",
                f"प्रमाण: {rec.recommended_quantity or 'लेबलनुसार'}.",
                "फवारणी करताना योग्य सुरक्षा साधनांचा वापर करा."
            ]
    elif lang_key == "hi":
        explanation = f"पहचाना गया रोग: {rec.disease_name}। {rec.disease_description or ''}"
        if is_seed:
            actions = [
                f"सत्यापित बीज उपचार: {rec.treatment or 'कृषि अधिकारी की सलाह लें'}।",
                f"मात्रा: {rec.recommended_quantity or 'लेबल के अनुसार'}।",
                "बीज उपचार के बाद छाया में सुखाएं, धूप में नहीं।",
                "उपचारित बीज को संभालने के बाद हाथ धोएं।"
            ]
        else:
            actions = [
                f"सत्यापित उपचार: {rec.treatment or 'कृषि अधिकारी की सलाह लें'}।",
                f"मात्रा: {rec.recommended_quantity or 'लेबल के अनुसार'}।",
                "छिड़काव के समय सुरक्षात्मक कपड़े पहनें।"
            ]
    else:
        explanation = f"Detected condition: {rec.disease_name}. {rec.disease_description or ''}"
        if is_seed:
            actions = [
                f"Apply verified seed treatment: {rec.treatment or 'Consult agricultural advisor'}.",
                f"Recommended dose: {rec.recommended_quantity or 'As per product label'}.",
                "After treating seeds, shade-dry for ~2 hours before sowing.",
                "Wash hands after handling treated seeds."
            ]
        else:
            actions = [
                f"Apply verified treatment: {rec.treatment or 'Consult agricultural advisor'}.",
                f"Recommended dose: {rec.recommended_quantity or 'As per product label'}.",
                "Follow all safety precautions during spraying."
            ]

    return ClaudeGuidanceResponse(
        status="fallback",
        crop="tur",
        disease_name=rec.disease_name,
        confidence=scan.confidence,
        confidence_percent=conf_pct,
        disease_explanation=explanation.strip(),
        farmer_action=actions,
        spray_guidance_available=True,
        ai_guidance_available=False,
        spray_guidance=verified_details,
        warnings=warnings,
        language=lang_key,
        important_alert=SEED_TREATMENT_ALERT.get(lang_key) if is_seed else None,
    )


def generate_claude_guidance(
    db: Session,
    scan: TurScan,
    language: str = "en"
) -> ClaudeGuidanceResponse:
    """
    Generates AI guidance for a Tur scan using Claude Sonnet 4.5.
    Enforces confidence validation (>= 60%) and database verification rules.
    Falls back gracefully if Claude API key is missing or call fails.
    """
    lang_key = _get_lang_key(language)
    conf_val = scan.confidence or 0.0
    conf_pct = int(round(conf_val * 100)) if scan.confidence is not None else 0

    # 1. Check Confidence Safety (< 60%)
    if conf_val < 0.60:
        logger.info("[CLAUDE GUIDANCE] Scan #%d confidence (%.2f) < 0.60. Returning low confidence response.", scan.id, conf_val)
        low_data = LOW_CONFIDENCE_DATA[lang_key]
        return ClaudeGuidanceResponse(
            status="low_confidence",
            crop="tur",
            disease_name=scan.disease_name,
            confidence=scan.confidence,
            confidence_percent=conf_pct,
            disease_explanation=str(low_data["explanation"]),
            farmer_action=list(low_data["actions"]),
            spray_guidance_available=False,
            ai_guidance_available=True,
            spray_guidance=None,
            warnings=["Low confidence prediction (<60%). Spray guidance disabled for safety."],
            language=lang_key,
        )

    disease_clean = (scan.disease_name or "").strip()

    # 2. Check Healthy Safety
    if disease_clean.lower() == "healthy":
        logger.info("[CLAUDE GUIDANCE] Scan #%d is Healthy. Returning healthy guidance without chemical spray recommendations.", scan.id)
        healthy_data = HEALTHY_DATA[lang_key]
        return ClaudeGuidanceResponse(
            status="success",
            crop="tur",
            disease_name="Healthy",
            confidence=scan.confidence,
            confidence_percent=conf_pct,
            disease_explanation=str(healthy_data["explanation"]),
            farmer_action=list(healthy_data["actions"]),
            spray_guidance_available=False,
            ai_guidance_available=True,
            spray_guidance=None,
            warnings=[],
            language=lang_key,
        )

    # 2b. Check Leaf Webber Safety — Pesticide guidance disabled (banned historical chemicals / no verified doses)
    if "webber" in disease_clean.lower():
        logger.info("[CLAUDE GUIDANCE] Scan #%d is Leaf Webber. Spray guidance disabled for safety.", scan.id)
        logger.info(
            "[GUIDANCE_SERVICE_DIAGNOSTIC] scan_id=%d disease=%s raw_confidence=%.6f guidance_status=%s spray_available=%s",
            scan.id, disease_clean, scan.confidence or 0.0, "unverified", False
        )
        webber_data = LEAF_WEBBER_DATA[lang_key]
        return ClaudeGuidanceResponse(
            status="unverified",
            crop="tur",
            disease_name="Leaf_webber",
            confidence=scan.confidence,
            confidence_percent=conf_pct,
            disease_explanation=str(webber_data["explanation"]),
            farmer_action=list(webber_data["actions"]),
            spray_guidance_available=False,
            ai_guidance_available=True,
            spray_guidance=None,
            warnings=["Verified spray guidance is currently unavailable for Leaf Webber. Chemical recommendations disabled for safety."],
            language=lang_key,
        )

    # 3. Retrieve Verified Recommendation Record from Database
    query = select(TurDiseaseRecommendation).where(
        TurDiseaseRecommendation.crop == "tur",
        func.lower(TurDiseaseRecommendation.disease_name) == disease_clean.lower(),
        TurDiseaseRecommendation.is_active == True,
    )
    rec = db.scalar(query)

    if not rec:
        logger.warning("[CLAUDE GUIDANCE] No active recommendation in database for disease: %s", disease_clean)
        return _build_fallback_guidance(
            scan=scan,
            rec=None,
            language=lang_key,
            warnings=[f"No verified recommendation in database for disease: {disease_clean}"]
        )

    calculated_pump_qty = rec.per_pump_quantity
    if not calculated_pump_qty and rec.recommended_quantity:
        if rec.disease_name.lower() == "leaf_spot" and "2.5 g/l" in rec.recommended_quantity.lower():
            calculated_pump_qty = "37.5 g"
        elif rec.disease_name.lower() == "sterilic_mosaic":
            calculated_pump_qty = "15 ml"

    verified_details = SprayGuidanceDetails(
        treatment=rec.treatment,
        active_ingredient=rec.active_ingredient,
        recommended_quantity=rec.recommended_quantity,
        water_quantity=rec.water_quantity,  # Preserved as NULL if None
        per_pump_quantity=calculated_pump_qty,  # Preserved as NULL if None
        spray_timing=rec.spray_timing,
        application_method=rec.application_method,
        safety_precautions=rec.safety_precautions,
        after_spray_advisory=rec.after_spray_advisory,
    )

    # 4. Check Anthropic API Key
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key or not api_key.strip():
        logger.info("[CLAUDE GUIDANCE] ANTHROPIC_API_KEY not configured. Returning verified database fallback.")
        return _build_fallback_guidance(
            scan=scan,
            rec=rec,
            language=lang_key,
            warnings=["ANTHROPIC_API_KEY is not configured in backend environment."]
        )

    # 5. Call Anthropic Claude API
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key.strip())

        system_prompt = (
            "You are a translation and explanation layer for Tur (pigeonpea) crop health.\n"
            "Your task is ONLY to simplify and translate the provided verified recommendation data into the requested language.\n\n"
            "STRICT RULES:\n"
            "1. ALL farmer-facing explanatory text MUST be entirely in the requested target_language. DO NOT mix English sentences into Marathi or Hindi text. However, technical product names, chemical names (e.g., Mancozeb 75 WP, Fenazaquin 10 EC), units (e.g., 2.5 g/L), and verified quantities MUST remain unchanged in their original technical format.\n"
            "2. NEVER treat 'confidence' as disease severity (e.g. 67% confidence does NOT mean 'mild' or 'early stage'). Confidence is only the AI's detection certainty. State confidence separately and clearly.\n"
            "3. NEVER infer disease cause (e.g. do not say 'fungal') or biological severity unless explicitly present in the trusted data.\n"
            "4. NEVER invent, calculate, or add pesticide dosage, water quantity, pump quantity, spray techniques (e.g. nozzle, pressure), intervals, or claims (e.g. '100% effective').\n"
            "5. NEVER make guidance sound more certain than the trusted data (e.g. no 'Definitely' or 'Guaranteed').\n"
            "6. In 'disease_explanation', provide a short conservative explanation of the detection. ONLY IF supported by the trusted context, add a short explanation of 'Why this spray' (e.g., if transmitted by mites, explain the spray helps control the mite associated with the disease). Do not make unsupported claims.\n"
            "7. 'farmer_action' must be a short, practical summary using ONLY the verified treatment, quantity, timing, application method, safety, and after-spray advisory. Do not add extra agricultural instructions. ALWAYS include this exact safe mixing warning as the final point: If English: 'Before mixing more than one product, check the product label or verified agricultural recommendation.' If Marathi: 'एकापेक्षा जास्त औषधे एकत्र मिसळण्यापूर्वी उत्पादनाच्या label वरील सूचना किंवा अधिकृत कृषी शिफारस तपासा.' If Hindi: 'एक से अधिक दवाओं को मिलाने से पहले उत्पाद के label या आधिकारिक कृषि सिफारिश की जांच करें।'\n"
            "8. Return ONLY a valid JSON object matching this exact structure with no markdown codeblocks:\n"
            "{\n"
            '  "disease_explanation": "Short conservative explanation in target language (includes confidence and optional verified why-this-spray)",\n'
            '  "farmer_action": ["Action step 1 in target language", "Action step 2 in target language"]\n'
            "}\n"
        )

        user_input_payload = {
            "crop": "tur",
            "disease_name": rec.disease_name,
            "detection_confidence": f"{conf_pct}%",
            "disease_description": rec.disease_description,
            "treatment": rec.treatment,
            "active_ingredient": rec.active_ingredient,
            "recommended_quantity": rec.recommended_quantity,
            "water_quantity": rec.water_quantity,
            "per_pump_quantity": rec.per_pump_quantity,
            "spray_timing": rec.spray_timing,
            "application_method": rec.application_method,
            "safety_precautions": rec.safety_precautions,
            "after_spray_advisory": rec.after_spray_advisory,
            "target_language": lang_key
        }

        user_prompt = (
            f"Here is the verified crop disease data:\n"
            f"{json.dumps(user_input_payload, indent=2)}\n\n"
            f"Generate the disease_explanation and farmer_action in language code '{lang_key}'."
        )

        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        # Clean codeblock wrappers if any
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[-1]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

        parsed_claude = json.loads(clean_text)
        disease_explanation = parsed_claude.get("disease_explanation")
        farmer_action = parsed_claude.get("farmer_action")

        if not disease_explanation or not isinstance(farmer_action, list):
            raise ValueError("Invalid JSON schema returned by Claude")

        is_seed_treat = _is_seed_treatment(rec)

        return ClaudeGuidanceResponse(
            status="success",
            crop="tur",
            disease_name=rec.disease_name,
            confidence=scan.confidence,
            confidence_percent=conf_pct,
            disease_explanation=str(disease_explanation),
            farmer_action=[str(a) for a in farmer_action],
            spray_guidance_available=True,
            ai_guidance_available=True,
            spray_guidance=verified_details,
            warnings=[],
            language=lang_key,
            important_alert=SEED_TREATMENT_ALERT.get(lang_key) if is_seed_treat else None,
        )

    except Exception as exc:
        logger.error("[CLAUDE GUIDANCE] Exception during Claude API call: %s", exc)
        return _build_fallback_guidance(
            scan=scan,
            rec=rec,
            language=lang_key,
            warnings=[f"Claude API failed: fallback to verified database guidance."]
        )
