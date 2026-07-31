import json
import logging
from typing import List, Optional

from groq import Groq
from pydantic import BaseModel, Field

from lablens.config import get_settings

log = logging.getLogger(__name__)


class LLMBiomarker(BaseModel):
    name: str = Field(default="unknown")
    display_name: str = Field(default="Unknown")
    value: float = Field(default=0.0)
    unit: str = Field(default="")
    ref_low: Optional[float] = Field(default=None)
    ref_high: Optional[float] = Field(default=None)
    category: str = Field(default="general")


class LLMExtraction(BaseModel):
    is_valid_report: bool = Field(default=True)
    error_message: str = Field(default="")
    biomarkers: List[LLMBiomarker] = Field(default_factory=list)
    diet_suggestions: str = Field(default="")
    doctor_recommendation: str = Field(default="")


SYSTEM_PROMPT = """You are a medical lab report analysis AI. You ONLY respond with valid JSON. No markdown, no explanation, just JSON.

Your JSON response must have exactly these top-level keys:
- "is_valid_report": boolean (true if the text is a medical lab report, false if it is a resume, letter, or non-medical document)
- "error_message": string (explain why the document is invalid if is_valid_report is false, otherwise empty string "")
- "biomarkers": array of objects, each with: "name" (snake_case), "display_name" (human readable), "value" (number), "unit" (string), "ref_low" (number or null), "ref_high" (number or null), "category" (one of: blood_sugar, lipid, liver, kidney, cbc, thyroid, vitamins, general)
- "diet_suggestions": string with dietary advice based on abnormal results (what to eat, what to avoid)
- "doctor_recommendation": string recommending which type of doctor to see based on results

Example response for a valid report:
{"is_valid_report": true, "error_message": "", "biomarkers": [{"name": "fasting_glucose", "display_name": "Fasting Glucose", "value": 145.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 100.0, "category": "blood_sugar"}], "diet_suggestions": "Reduce sugar intake...", "doctor_recommendation": "Consult an Endocrinologist..."}

Example response for an invalid document:
{"is_valid_report": false, "error_message": "This document appears to be a resume, not a medical lab report. Please upload a valid lab report.", "biomarkers": [], "diet_suggestions": "", "doctor_recommendation": ""}"""


def extract_from_llm(text: str) -> LLMExtraction:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("Groq API key not configured")

    client = Groq(api_key=settings.groq_api_key)

    user_prompt = f"Analyze this text and respond with JSON only:\n\n{text[:6000]}"

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    content = response.choices[0].message.content
    log.info("LLM raw response: %s", content[:500])

    data = json.loads(content)

    # Defensive: if the LLM nests data under a wrapper key, unwrap it
    if "is_valid_report" not in data:
        # Try common wrapper patterns
        for key in ("result", "response", "data", "report"):
            if key in data and isinstance(data[key], dict):
                data = data[key]
                break

    return LLMExtraction.model_validate(data)

