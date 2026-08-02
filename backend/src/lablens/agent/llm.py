import json
import logging
from typing import List, Optional, Union

from groq import Groq
from pydantic import BaseModel, Field, field_validator

from lablens.config import get_settings

log = logging.getLogger(__name__)


class LLMBiomarker(BaseModel):
    name: str = Field(default="unknown")
    display_name: str = Field(default="Unknown")
    value: Optional[Union[float, str]] = Field(default=None)
    unit: str = Field(default="")
    ref_low: Optional[float] = Field(default=None)
    ref_high: Optional[float] = Field(default=None)
    ref_text: str = Field(default="")  # For qualitative references like "Negative", "Pale Yellow"
    category: str = Field(default="general")
    status: str = Field(default="normal")  # normal, abnormal, high, low, critical_high, critical_low

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return v  # Keep as string for qualitative values like "Negative"
        return v


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
- "biomarkers": array of objects for EVERY test result found in the report. Each object has:
  - "name": snake_case identifier (e.g. "fasting_glucose", "urine_ph", "urine_protein")
  - "display_name": human readable name (e.g. "Urine pH", "Protein")
  - "value": the result value — use a NUMBER if the result is numeric (e.g. 145, 7.2, 1.015), or a STRING if the result is qualitative (e.g. "Negative", "Normal", "Light Yellow", "Positive", "1+", "Trace")
  - "unit": the unit of measurement (e.g. "mg/dL", "" for qualitative)
  - "ref_low": number or null (lower bound of reference range, null if qualitative)
  - "ref_high": number or null (upper bound of reference range, null if qualitative)
  - "ref_text": string with the expected/reference value for qualitative tests (e.g. "Negative", "Pale Yellow", "Normal"). Empty string for numeric tests.
  - "category": one of: blood_sugar, lipid, liver, kidney, cbc, thyroid, vitamins, urine, general
  - "status": one of: "normal" (value is within reference range or matches expected), "abnormal" (value is outside range or unexpected), "critical" (dangerously abnormal)
- "diet_suggestions": string with dietary advice based on abnormal results
- "doctor_recommendation": string recommending which type of doctor to see

IMPORTANT: Extract ALL tests from the report, including qualitative tests like urine analysis (color, pH, protein, glucose, ketones, blood, etc.), not just numeric blood tests.

Example with both numeric and qualitative results:
{"is_valid_report": true, "error_message": "", "biomarkers": [{"name": "fasting_glucose", "display_name": "Fasting Glucose", "value": 145.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 100.0, "ref_text": "", "category": "blood_sugar", "status": "abnormal"}, {"name": "urine_protein", "display_name": "Protein", "value": "Negative", "unit": "", "ref_low": null, "ref_high": null, "ref_text": "Negative", "category": "urine", "status": "normal"}, {"name": "urine_color", "display_name": "Colour", "value": "Light Yellow", "unit": "", "ref_low": null, "ref_high": null, "ref_text": "Pale Yellow", "category": "urine", "status": "normal"}], "diet_suggestions": "Reduce sugar intake...", "doctor_recommendation": "Consult an Endocrinologist..."}

Example response for an invalid document:
{"is_valid_report": false, "error_message": "This document appears to be a resume, not a medical lab report.", "biomarkers": [], "diet_suggestions": "", "doctor_recommendation": ""}"""


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
        for key in ("result", "response", "data", "report"):
            if key in data and isinstance(data[key], dict):
                data = data[key]
                break

    return LLMExtraction.model_validate(data)


