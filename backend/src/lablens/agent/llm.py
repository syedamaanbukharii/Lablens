import json
from typing import List, Optional

from groq import Groq
from pydantic import BaseModel, Field

from lablens.config import get_settings


class LLMBiomarker(BaseModel):
    name: str = Field(..., description="Canonical snake_case name of the biomarker, e.g. fasting_blood_glucose, ast_sgot, alt_sgpt")
    display_name: str = Field(..., description="Human readable name, e.g. AST (SGOT)")
    value: float = Field(..., description="The numeric value extracted")
    unit: str = Field(..., description="The unit of measurement")
    ref_low: Optional[float] = Field(None, description="The lower bound of the reference range if provided")
    ref_high: Optional[float] = Field(None, description="The upper bound of the reference range if provided")
    category: str = Field(..., description="One of: blood_sugar, lipid, liver, kidney, cbc, thyroid, vitamins, general")


class LLMExtraction(BaseModel):
    is_valid_report: bool = Field(..., description="True if the text appears to be a medical lab report. False if it is a resume, generic document, or non-medical text.")
    error_message: str = Field(..., description="If is_valid_report is false, explain that a valid medical lab report is required. Otherwise empty string.")
    biomarkers: List[LLMBiomarker] = Field(default_factory=list, description="List of extracted biomarkers if valid report")
    diet_suggestions: str = Field(..., description="General dietary suggestions (what to eat / avoid) based on any abnormal biomarkers. If everything is normal, provide general healthy diet advice.")
    doctor_recommendation: str = Field(..., description="The type of medical specialist to consult based on the findings (e.g. Endocrinologist for diabetes/thyroid, Hepatologist for liver, General Practitioner if normal).")


def extract_from_llm(text: str) -> LLMExtraction:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("Groq API key not configured")
        
    client = Groq(api_key=settings.groq_api_key)
    
    schema = LLMExtraction.model_json_schema()
    
    prompt = f"""You are an expert medical data extraction AI.
    
Analyze the following text. Determine if it is a medical lab report.
If it is NOT a medical lab report (e.g. a resume, letter, invoice), set is_valid_report to false and provide an error_message.
If it IS a medical lab report, extract all biomarkers, their values, units, and reference ranges.
Also, provide general diet suggestions based on abnormal results, and recommend the type of doctor to consult.
IMPORTANT: Your response MUST be valid JSON matching the following schema:
{json.dumps(schema)}

Text to analyze:
{text[:6000]}
"""

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    content = response.choices[0].message.content
    data = json.loads(content)
    return LLMExtraction(**data)
