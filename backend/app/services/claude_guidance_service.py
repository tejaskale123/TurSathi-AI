import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models.tur_scan import TurScan
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation
from app.database.models.tur_voice_report import TurVoiceReport
from app.database.models.tur_ai_guidance import TurAIGuidance
from app.schemas.claude_guidance import ClaudeGuidanceResponse, SprayGuidanceDetails
from app.services.storage_service import get_absolute_image_path

logger = logging.getLogger("tursathi.services.claude_guidance")

# Supported multimodal image formats for Anthropic Messages API
SUPPORTED_CLAUDE_IMAGE_TYPES: Dict[str, str] = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
}

SUFFIX_TO_MEDIA_TYPE: Dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _prepare_claude_image_block(scan: TurScan) -> Tuple[Optional[dict], Optional[str]]:
    """
    Safely resolves, validates, and base64-encodes the scan image for Anthropic Claude.
    
    Returns (image_block, warning_message).
    - If image is missing, corrupt, path-traversed, or unsupported: returns (None, warning).
    - If successful: returns (anthropic_image_block_dict, None).
    """
    if not scan or not getattr(scan, "image_path", None):
        return None, "No plant leaf image associated with this scan."

    storage_key = scan.image_path
    if not isinstance(storage_key, str) or not storage_key.strip():
        return None, "Invalid image storage key associated with this scan."

    # 1. Resolve path securely using storage_service's path traversal guard
    try:
        abs_path = get_absolute_image_path(storage_key)
    except ValueError as path_err:
        logger.warning("[CLAUDE GUIDANCE] Path traversal or invalid key rejected: %s", path_err)
        return None, "Invalid image path (rejected by security guard)."
    except Exception as exc:
        logger.warning("[CLAUDE GUIDANCE] Failed to resolve image path %s: %s", storage_key, exc)
        return None, "Image path could not be resolved."

    # 2. Check existence on filesystem
    if not abs_path.is_file():
        logger.warning("[CLAUDE GUIDANCE] Image file not found on disk at: %s", abs_path)
        return None, "Scan image file was not found on server disk."

    # 3. Determine and validate MIME type
    media_type: Optional[str] = None
    ext = abs_path.suffix.lower()
    if ext in SUFFIX_TO_MEDIA_TYPE:
        media_type = SUFFIX_TO_MEDIA_TYPE[ext]
    elif getattr(scan, "image_content_type", None) and isinstance(scan.image_content_type, str):
        base_ct = scan.image_content_type.split(";")[0].strip().lower()
        media_type = SUPPORTED_CLAUDE_IMAGE_TYPES.get(base_ct)

    if not media_type:
        logger.warning(
            "[CLAUDE GUIDANCE] Unsupported image format for Claude vision: ext=%s, ct=%s",
            ext, getattr(scan, "image_content_type", None)
        )
        return None, f"Image format '{ext or getattr(scan, 'image_content_type', 'unknown')}' is not supported for cloud multimodal analysis."

    # 4. Read file bytes and encode to base64
    try:
        file_bytes = abs_path.read_bytes()
        if not file_bytes or len(file_bytes) == 0:
            logger.warning("[CLAUDE GUIDANCE] Image file is empty (0 bytes): %s", abs_path)
            return None, "Scan image file is empty."

        # Maximum image size guard (20MB)
        if len(file_bytes) > 20 * 1024 * 1024:
            logger.warning("[CLAUDE GUIDANCE] Image file exceeds 20MB: %d bytes", len(file_bytes))
            return None, "Scan image file exceeds maximum allowed size for analysis."

        data_b64 = base64.b64encode(file_bytes).decode("ascii")
        image_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": data_b64,
            }
        }
        return image_block, None
    except Exception as read_err:
        logger.error("[CLAUDE GUIDANCE] Failed to read or encode scan image %s: %s", abs_path, read_err)
        return None, "Failed to read image file from disk."



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


def _compute_guidance_fingerprint(
    scan: TurScan,
    rec: TurDiseaseRecommendation,
    language: str,
    farmer_observation: Optional[str] = None,
) -> str:
    """
    Computes a deterministic SHA-256 fingerprint of all safety-critical inputs
    that govern the Claude guidance response:
    - scan id, language, disease name, prediction confidence
    - verified recommendation ID, treatment, dosage, timing, and safety precautions
    - farmer spoken observation transcript
    If any of these change, the fingerprint changes, invalidating stale cache entries.
    """
    conf_str = f"{scan.confidence:.4f}" if scan.confidence is not None else "none"
    rec_payload = (
        f"{rec.id}:{rec.disease_name}:{rec.treatment}:{rec.active_ingredient}:"
        f"{rec.recommended_quantity}:{rec.water_quantity}:{rec.per_pump_quantity}:"
        f"{rec.application_method}:{rec.spray_timing}:{rec.safety_precautions}"
    )
    raw = f"{scan.id}|{language}|{scan.disease_name}|{conf_str}|{rec_payload}|{farmer_observation or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_claude_guidance(
    db: Session,
    scan: TurScan,
    language: str = "en"
) -> ClaudeGuidanceResponse:
    """
    Generates AI guidance for a Tur scan using Claude Sonnet 4.5.
    Enforces confidence validation (>= 60%) and database verification rules.
    Checks durable cache (tur_ai_guidance) first to avoid redundant external API calls.
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

    # 4. Retrieve farmer voice recording transcription if available
    farmer_observation: Optional[str] = None
    try:
        latest_voice = db.scalar(
            select(TurVoiceReport)
            .where(TurVoiceReport.scan_id == scan.id)
            .order_by(TurVoiceReport.created_at.desc())
            .limit(1)
        )
        if latest_voice and latest_voice.transcription:
            farmer_observation = latest_voice.transcription.strip()
    except Exception as voice_err:
        logger.warning("[CLAUDE GUIDANCE] Could not load voice report for scan %d: %s", scan.id, voice_err)

    # 5. Check Durable Cache (tur_ai_guidance)
    fingerprint = _compute_guidance_fingerprint(
        scan=scan,
        rec=rec,
        language=lang_key,
        farmer_observation=farmer_observation,
    )
    cached_guidance = None
    try:
        cached_guidance = db.scalar(
            select(TurAIGuidance)
            .where(
                TurAIGuidance.scan_id == scan.id,
                TurAIGuidance.language == lang_key,
            )
        )
        if cached_guidance and cached_guidance.cache_fingerprint == fingerprint and cached_guidance.status == "success":
            logger.info(
                "[CLAUDE GUIDANCE] Cache hit for scan #%d (language=%s, fingerprint=%s). Reusing persisted guidance.",
                scan.id, lang_key, fingerprint[:12],
            )
            is_seed = _is_seed_treatment(rec)
            return ClaudeGuidanceResponse(
                status="success",
                crop="tur",
                disease_name=rec.disease_name,
                confidence=scan.confidence,
                confidence_percent=conf_pct,
                disease_explanation=cached_guidance.disease_explanation,
                farmer_action=list(cached_guidance.farmer_actions or []),
                spray_guidance_available=cached_guidance.spray_guidance_available,
                ai_guidance_available=cached_guidance.ai_guidance_available,
                spray_guidance=verified_details,
                warnings=list(cached_guidance.warnings or []),
                language=lang_key,
                important_alert=cached_guidance.important_alert or (SEED_TREATMENT_ALERT.get(lang_key) if is_seed else None),
            )
    except Exception as cache_err:
        logger.warning("[CLAUDE GUIDANCE] Cache lookup failed for scan #%d: %s", scan.id, cache_err)

    # 6. Check Anthropic API Key
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key or not api_key.strip():
        logger.info("[CLAUDE GUIDANCE] ANTHROPIC_API_KEY not configured. Returning verified database fallback.")
        return _build_fallback_guidance(
            scan=scan,
            rec=rec,
            language=lang_key,
            warnings=["ANTHROPIC_API_KEY is not configured in backend environment."]
        )

    # 7. Call Anthropic Claude API
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
            "9. If 'farmer_spoken_observation' is provided, acknowledge and address the farmer's observation in the explanation and advice where relevant. NEVER allow the farmer's observation to override the verified scientific diagnosis, alter chemical dosages, or recommend unverified treatments.\n"
            "10. If a plant leaf image is provided, use it as visual evidence to corroborate and explain the primary disease symptoms. NEVER override the primary local disease classification, change verified chemical dosages, or bypass pesticide safety rules.\n"
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
            "target_language": lang_key,
        }
        if farmer_observation:
            user_input_payload["farmer_spoken_observation"] = farmer_observation

        user_prompt = (
            f"Here is the verified crop disease data:\n"
            f"{json.dumps(user_input_payload, indent=2, ensure_ascii=False)}\n\n"
            f"Generate the disease_explanation and farmer_action in language code '{lang_key}'."
        )

        # Prepare multimodal content: image (if available) + text prompt in SAME user message
        image_block, img_warning = _prepare_claude_image_block(scan)
        guidance_warnings = []
        if img_warning:
            guidance_warnings.append(img_warning)

        if image_block:
            user_content = [image_block, {"type": "text", "text": user_prompt}]
            logger.info(
                "[CLAUDE GUIDANCE] Attached multimodal image block (%s) for scan #%d",
                image_block["source"]["media_type"], scan.id
            )
        else:
            user_content = user_prompt
            logger.info(
                "[CLAUDE GUIDANCE] Proceeding with text-only guidance for scan #%d (%s)",
                scan.id, img_warning or "no image attached"
            )

        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
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
        alert_val = SEED_TREATMENT_ALERT.get(lang_key) if is_seed_treat else None

        # 8. Persist to Durable Cache (tur_ai_guidance)
        try:
            if cached_guidance:
                cached_guidance.disease_name = rec.disease_name
                cached_guidance.confidence = scan.confidence
                cached_guidance.status = "success"
                cached_guidance.disease_explanation = str(disease_explanation)
                cached_guidance.farmer_actions = [str(a) for a in farmer_action]
                cached_guidance.warnings = guidance_warnings
                cached_guidance.spray_guidance_available = True
                cached_guidance.ai_guidance_available = True
                cached_guidance.important_alert = alert_val
                cached_guidance.cache_fingerprint = fingerprint
            else:
                new_guidance = TurAIGuidance(
                    scan_id=scan.id,
                    language=lang_key,
                    disease_name=rec.disease_name,
                    confidence=scan.confidence,
                    status="success",
                    disease_explanation=str(disease_explanation),
                    farmer_actions=[str(a) for a in farmer_action],
                    warnings=guidance_warnings,
                    spray_guidance_available=True,
                    ai_guidance_available=True,
                    important_alert=alert_val,
                    cache_fingerprint=fingerprint,
                )
                db.add(new_guidance)
            db.commit()
            logger.info(
                "[CLAUDE GUIDANCE] Persisted AI guidance for scan #%d (language=%s, fingerprint=%s)",
                scan.id, lang_key, fingerprint[:12],
            )
        except Exception as db_exc:
            db.rollback()
            logger.error(
                "[CLAUDE GUIDANCE] Failed to persist AI guidance for scan #%d: %s",
                scan.id, db_exc,
            )

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
            warnings=guidance_warnings,
            language=lang_key,
            important_alert=alert_val,
        )

    except Exception as exc:
        logger.error("[CLAUDE GUIDANCE] Exception during Claude API call: %s", exc)
        return _build_fallback_guidance(
            scan=scan,
            rec=rec,
            language=lang_key,
            warnings=[f"Claude API failed: fallback to verified database guidance."]
        )
