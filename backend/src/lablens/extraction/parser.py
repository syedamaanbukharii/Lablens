"""Biomarker parser: extract structured lab values from free text.

This is a rules-based parser, not an LLM call. Lab reports follow predictable
formats (name, value, unit, reference range), and a parser that handles 90% of
common formats reliably is more valuable than an LLM that handles 98% but
hallucinates on the other 2% — because a hallucinated lab value is dangerous.

The LLM layer (in agent/) handles the *interpretation* and *summary* on top of
these parsed values, where fluency matters and precision is less critical.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedBiomarker:
    name: str
    display_name: str
    value: float
    unit: str
    ref_low: float | None = None
    ref_high: float | None = None
    category: str = "general"
    raw_line: str = ""


# Canonical biomarker definitions: (pattern, display_name, unit, ref_low, ref_high, category)
BIOMARKER_DEFS: list[tuple[re.Pattern, str, str, float | None, float | None, str]] = [
    # Blood sugar
    (re.compile(r"(?:fasting\s+)?(?:blood\s+)?(?:glucose|sugar|FBS|FBG|RBS)\s*(?:\(fasting\))?\s*", re.I),
     "Fasting Blood Glucose", "mg/dL", 70.0, 100.0, "blood_sugar"),
    (re.compile(r"(?:HbA1c|A1C|glycated\s+h[ae]moglobin|glycosylated)\s*", re.I),
     "HbA1c", "%", None, 5.7, "blood_sugar"),
    # Lipid panel
    (re.compile(r"(?:total\s+)?cholesterol\s*", re.I),
     "Total Cholesterol", "mg/dL", None, 200.0, "lipid"),
    (re.compile(r"(?:HDL|high\s+density)\s*(?:cholesterol)?\s*", re.I),
     "HDL Cholesterol", "mg/dL", 40.0, None, "lipid"),
    (re.compile(r"(?:LDL|low\s+density)\s*(?:cholesterol)?\s*", re.I),
     "LDL Cholesterol", "mg/dL", None, 100.0, "lipid"),
    (re.compile(r"triglycerides?\s*", re.I),
     "Triglycerides", "mg/dL", None, 150.0, "lipid"),
    # Liver
    (re.compile(r"(?:SGPT|ALT|alanine\s+(?:amino)?transaminase)\s*", re.I),
     "ALT (SGPT)", "U/L", 7.0, 56.0, "liver"),
    (re.compile(r"(?:SGOT|AST|aspartate\s+(?:amino)?transaminase)\s*", re.I),
     "AST (SGOT)", "U/L", 10.0, 40.0, "liver"),
    (re.compile(r"(?:ALP|alkaline\s+phosphatase)\s*", re.I),
     "ALP", "U/L", 44.0, 147.0, "liver"),
    (re.compile(r"(?:total\s+)?bilirubin\s*", re.I),
     "Bilirubin", "mg/dL", 0.1, 1.2, "liver"),
    (re.compile(r"(?:albumin)\s*", re.I),
     "Albumin", "g/dL", 3.5, 5.5, "liver"),
    # Kidney
    (re.compile(r"(?:creatinine|serum\s+creatinine)\s*", re.I),
     "Creatinine", "mg/dL", 0.7, 1.3, "kidney"),
    (re.compile(r"(?:BUN|blood\s+urea\s+nitrogen|urea)\s*", re.I),
     "BUN", "mg/dL", 7.0, 20.0, "kidney"),
    (re.compile(r"(?:eGFR|GFR|glomerular\s+filtration)\s*", re.I),
     "eGFR", "mL/min", 90.0, None, "kidney"),
    (re.compile(r"(?:uric\s+acid)\s*", re.I),
     "Uric Acid", "mg/dL", 3.5, 7.2, "kidney"),
    # CBC
    (re.compile(r"(?:h[ae]moglobin|Hb|HGB)\s*", re.I),
     "Hemoglobin", "g/dL", 12.0, 17.5, "cbc"),
    (re.compile(r"(?:WBC|white\s+blood\s+cell|leucocyte|leukocyte)\s*(?:count)?\s*", re.I),
     "WBC", "×10³/μL", 4.0, 11.0, "cbc"),
    (re.compile(r"(?:RBC|red\s+blood\s+cell|erythrocyte)\s*(?:count)?\s*", re.I),
     "RBC", "×10⁶/μL", 4.5, 5.5, "cbc"),
    (re.compile(r"(?:platelet|PLT)\s*(?:count)?\s*", re.I),
     "Platelets", "×10³/μL", 150.0, 400.0, "cbc"),
    (re.compile(r"(?:HCT|hematocrit|PCV)\s*", re.I),
     "Hematocrit", "%", 36.0, 48.0, "cbc"),
    (re.compile(r"(?:ESR|sed\s*rate|erythrocyte\s+sedimentation)\s*", re.I),
     "ESR", "mm/hr", None, 20.0, "cbc"),
    # Thyroid
    (re.compile(r"(?:TSH|thyroid\s+stimulating)\s*", re.I),
     "TSH", "mIU/L", 0.4, 4.0, "thyroid"),
    (re.compile(r"(?:free\s+T4|FT4|thyroxine)\s*", re.I),
     "Free T4", "ng/dL", 0.8, 1.8, "thyroid"),
    (re.compile(r"(?:free\s+T3|FT3|triiodothyronine)\s*", re.I),
     "Free T3", "pg/mL", 2.3, 4.2, "thyroid"),
    # Vitamins
    (re.compile(r"(?:vitamin\s+D|25-OH\s*D|25-hydroxy)\s*", re.I),
     "Vitamin D", "ng/mL", 30.0, 100.0, "vitamins"),
    (re.compile(r"(?:vitamin\s+B12|cobalamin)\s*", re.I),
     "Vitamin B12", "pg/mL", 200.0, 900.0, "vitamins"),
    (re.compile(r"(?:iron|serum\s+iron)\s*", re.I),
     "Iron", "μg/dL", 60.0, 170.0, "vitamins"),
    (re.compile(r"(?:ferritin)\s*", re.I),
     "Ferritin", "ng/mL", 12.0, 300.0, "vitamins"),
    (re.compile(r"(?:calcium|Ca)\s*(?:\(total\))?\s*", re.I),
     "Calcium", "mg/dL", 8.5, 10.5, "vitamins"),
]

# Pattern for value + optional unit + optional reference range
VALUE_PAT = re.compile(
    r"[:\s]*"                          # separator
    r"(\d+\.?\d*)"                     # value
    r"\s*"
    r"([a-zA-Z/%μ×³⁶·]+(?:/[a-zA-Z²³μ]+)?)?"  # unit (optional)
    r"(?:\s*[\(\[]?\s*"
    r"(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)"  # ref range (optional)
    r"\s*[\)\]]?)?"
)


def parse_biomarkers(text: str) -> list[ParsedBiomarker]:
    """Extract structured biomarker data from lab report text."""
    results: list[ParsedBiomarker] = []
    seen: set[str] = set()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 5:
            continue

        for pattern, display_name, default_unit, def_low, def_high, category in BIOMARKER_DEFS:
            match = pattern.search(stripped)
            if not match:
                continue

            # Look for numeric value after the biomarker name
            remainder = stripped[match.end():]
            val_match = VALUE_PAT.search(remainder)
            if not val_match:
                continue

            try:
                value = float(val_match.group(1))
            except (ValueError, TypeError):
                continue

            # Skip unreasonable values (likely page numbers or IDs)
            if value > 50000 or value < 0:
                continue

            name = display_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
            if name in seen:
                continue
            seen.add(name)

            unit = val_match.group(2) or default_unit
            ref_low = float(val_match.group(3)) if val_match.group(3) else def_low
            ref_high = float(val_match.group(4)) if val_match.group(4) else def_high

            results.append(ParsedBiomarker(
                name=name,
                display_name=display_name,
                value=value,
                unit=unit,
                ref_low=ref_low,
                ref_high=ref_high,
                category=category,
                raw_line=stripped[:200],
            ))
            break  # one match per line

    return results


def classify_status(value: float, ref_low: float | None, ref_high: float | None) -> str:
    """Classify a biomarker value against its reference range."""
    if ref_low is not None and value < ref_low:
        # Critical if more than 30% below low end
        return "critical_low" if ref_low > 0 and value < ref_low * 0.7 else "low"
    if ref_high is not None and value > ref_high:
        return "critical_high" if value > ref_high * 1.5 else "high"
    return "normal"
