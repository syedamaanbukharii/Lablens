"""Clinical interpretation: plain-language summaries and trend analysis.

The interpretation engine converts structured biomarker data into the kind of
explanation a doctor would give a patient. Rules-based for the interpretations
(because an incorrect clinical explanation is dangerous), with an optional LLM
layer for natural-language polish.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lablens.extraction.parser import ParsedBiomarker, classify_status

# Plain-language explanations keyed by (biomarker_name, status)
INTERPRETATIONS: dict[tuple[str, str], str] = {
    # Blood sugar
    ("fasting_blood_glucose", "normal"): "Your fasting blood sugar is within the normal range. This suggests your body is managing glucose well.",
    ("fasting_blood_glucose", "high"): "Your fasting blood sugar is elevated. This may indicate prediabetes or early diabetes. Consider reducing refined carbohydrates and increasing physical activity. A follow-up test is recommended.",
    ("fasting_blood_glucose", "critical_high"): "Your fasting blood sugar is significantly elevated. This strongly suggests diabetes. Please consult your doctor promptly for further evaluation and management.",
    ("fasting_blood_glucose", "low"): "Your fasting blood sugar is below normal. This could cause symptoms like shakiness, dizziness, or fatigue. Please discuss with your doctor.",
    ("hba1c", "normal"): "Your HbA1c is in the normal range, indicating good blood sugar control over the past 2-3 months.",
    ("hba1c", "high"): "Your HbA1c is elevated, suggesting higher-than-normal average blood sugar over the past 2-3 months. This may indicate prediabetes (5.7-6.4%) or diabetes (≥6.5%).",
    # Lipid
    ("total_cholesterol", "normal"): "Your total cholesterol is within a healthy range.",
    ("total_cholesterol", "high"): "Your total cholesterol is elevated. High cholesterol increases cardiovascular risk. Consider dietary changes, exercise, and discuss with your doctor whether medication is needed.",
    ("hdl_cholesterol", "normal"): "Your HDL (good) cholesterol is at a healthy level. HDL helps remove bad cholesterol from your arteries.",
    ("hdl_cholesterol", "low"): "Your HDL (good) cholesterol is low. Low HDL increases heart disease risk. Regular exercise, healthy fats, and quitting smoking can help raise it.",
    ("ldl_cholesterol", "normal"): "Your LDL (bad) cholesterol is within the desirable range.",
    ("ldl_cholesterol", "high"): "Your LDL (bad) cholesterol is elevated. This is a key risk factor for heart disease. Reducing saturated fats, increasing fiber, and exercise can help lower it.",
    ("triglycerides", "normal"): "Your triglycerides are within the normal range.",
    ("triglycerides", "high"): "Your triglycerides are elevated. High triglycerides increase cardiovascular risk. Reducing sugar, alcohol, and refined carbs can help.",
    # Liver
    ("alt_sgpt", "normal"): "Your ALT liver enzyme is within the normal range, suggesting healthy liver function.",
    ("alt_sgpt", "high"): "Your ALT liver enzyme is elevated. This can indicate liver inflammation. Common causes include medications, alcohol, fatty liver disease, or viral hepatitis.",
    ("ast_sgot", "normal"): "Your AST liver enzyme is normal.",
    ("ast_sgot", "high"): "Your AST is elevated, which may indicate liver or muscle damage. Your doctor may want to investigate further.",
    # Kidney
    ("creatinine", "normal"): "Your creatinine is within the normal range, indicating healthy kidney function.",
    ("creatinine", "high"): "Your creatinine is elevated. This may indicate reduced kidney function. Staying hydrated and following up with your doctor is important.",
    ("egfr", "normal"): "Your eGFR indicates healthy kidney filtration.",
    ("egfr", "low"): "Your eGFR is below normal, suggesting reduced kidney function. Please discuss with your doctor for monitoring and management.",
    # CBC
    ("hemoglobin", "normal"): "Your hemoglobin is within the normal range.",
    ("hemoglobin", "low"): "Your hemoglobin is low, which may indicate anemia. Common causes include iron deficiency, vitamin B12 deficiency, or chronic conditions. You may feel tired or short of breath.",
    ("hemoglobin", "high"): "Your hemoglobin is elevated. This can be caused by dehydration, smoking, or living at high altitude. Persistent elevation needs evaluation.",
    ("wbc", "normal"): "Your white blood cell count is normal, indicating a healthy immune response.",
    ("wbc", "high"): "Your white blood cell count is elevated. This often indicates your body is fighting an infection. Persistent elevation may need further investigation.",
    ("wbc", "low"): "Your white blood cell count is low, which may affect your body's ability to fight infections. Please discuss with your doctor.",
    ("platelets", "normal"): "Your platelet count is within the normal range.",
    ("platelets", "low"): "Your platelet count is low. This may increase bleeding risk. Please consult your doctor.",
    # Thyroid
    ("tsh", "normal"): "Your TSH is within the normal range, suggesting healthy thyroid function.",
    ("tsh", "high"): "Your TSH is elevated, which may indicate an underactive thyroid (hypothyroidism). Symptoms can include fatigue, weight gain, and feeling cold.",
    ("tsh", "low"): "Your TSH is low, which may indicate an overactive thyroid (hyperthyroidism). Symptoms can include weight loss, anxiety, and rapid heartbeat.",
    # Vitamins
    ("vitamin_d", "normal"): "Your vitamin D level is adequate.",
    ("vitamin_d", "low"): "Your vitamin D is below optimal. Low vitamin D can affect bone health and immune function. Sun exposure and supplementation can help.",
    ("vitamin_d", "critical_low"): "Your vitamin D is significantly low. This can affect bone health, immune function, and mood. Supplementation is strongly recommended — please discuss dosage with your doctor.",
    ("vitamin_b12", "normal"): "Your vitamin B12 level is adequate.",
    ("vitamin_b12", "low"): "Your vitamin B12 is low. This can cause fatigue, weakness, and neurological symptoms. Supplementation is usually effective.",
    ("iron", "low"): "Your iron level is low, which may contribute to anemia and fatigue.",
    ("ferritin", "low"): "Your ferritin (iron stores) is low. Even if your hemoglobin is normal, low ferritin can cause fatigue and hair loss.",
}

# Generic fallbacks
GENERIC_STATUS: dict[str, str] = {
    "normal": "This value is within the normal reference range.",
    "high": "This value is above the normal reference range. Please discuss with your doctor.",
    "low": "This value is below the normal reference range. Please discuss with your doctor.",
    "critical_high": "This value is significantly above normal. Please consult your doctor promptly.",
    "critical_low": "This value is significantly below normal. Please consult your doctor promptly.",
}


@dataclass
class BiomarkerInsight:
    name: str
    display_name: str
    value: float
    unit: str
    status: str
    category: str
    interpretation: str
    ref_low: float | None = None
    ref_high: float | None = None
    emoji: str = ""


@dataclass
class TrendPoint:
    date: str
    value: float
    status: str


@dataclass
class BiomarkerTrend:
    name: str
    display_name: str
    unit: str
    ref_low: float | None = None
    ref_high: float | None = None
    points: list[TrendPoint] = field(default_factory=list)
    direction: str = "stable"  # improving | worsening | stable | insufficient_data
    summary: str = ""


@dataclass
class ReportSummary:
    total_markers: int = 0
    normal_count: int = 0
    abnormal_count: int = 0
    critical_count: int = 0
    insights: list[BiomarkerInsight] = field(default_factory=list)
    plain_summary: str = ""
    categories: dict[str, list[BiomarkerInsight]] = field(default_factory=dict)


STATUS_EMOJI = {
    "normal": "✅",
    "high": "⚠️",
    "low": "⚠️",
    "critical_high": "🔴",
    "critical_low": "🔴",
}


def interpret_biomarker(bm: ParsedBiomarker) -> BiomarkerInsight:
    """Generate a plain-language interpretation for one biomarker."""
    status = classify_status(bm.value, bm.ref_low, bm.ref_high)
    key = (bm.name, status)
    interpretation = INTERPRETATIONS.get(key, GENERIC_STATUS.get(status, ""))

    return BiomarkerInsight(
        name=bm.name,
        display_name=bm.display_name,
        value=bm.value,
        unit=bm.unit,
        ref_low=bm.ref_low,
        ref_high=bm.ref_high,
        status=status,
        category=bm.category,
        interpretation=interpretation,
        emoji=STATUS_EMOJI.get(status, ""),
    )


def summarize_report(biomarkers: list[ParsedBiomarker]) -> ReportSummary:
    """Generate a complete report summary with categorized insights."""
    insights = [interpret_biomarker(bm) for bm in biomarkers]

    normal = [i for i in insights if i.status == "normal"]
    abnormal = [i for i in insights if i.status in ("high", "low")]
    critical = [i for i in insights if i.status in ("critical_high", "critical_low")]

    # Group by category
    categories: dict[str, list[BiomarkerInsight]] = {}
    for ins in insights:
        categories.setdefault(ins.category, []).append(ins)

    # Build plain-language summary
    parts: list[str] = []
    if critical:
        names = ", ".join(i.display_name for i in critical)
        parts.append(f"🔴 Attention needed: {names} {'is' if len(critical) == 1 else 'are'} significantly outside the normal range and should be discussed with your doctor soon.")
    if abnormal:
        names = ", ".join(i.display_name for i in abnormal)
        parts.append(f"⚠️ {names} {'is' if len(abnormal) == 1 else 'are'} outside the normal range. See the details below for what this means and what you can do.")
    if normal and not critical and not abnormal:
        parts.append("✅ All your lab values are within normal ranges. Keep up the good work!")
    elif normal:
        parts.append(f"✅ {len(normal)} other marker{'s' if len(normal) > 1 else ''} {'are' if len(normal) > 1 else 'is'} within normal ranges.")

    return ReportSummary(
        total_markers=len(insights),
        normal_count=len(normal),
        abnormal_count=len(abnormal),
        critical_count=len(critical),
        insights=insights,
        plain_summary="\n\n".join(parts),
        categories=categories,
    )


def compute_trends(history: list[tuple[str, float, str]]) -> BiomarkerTrend | None:
    """Compute trend from a list of (date_str, value, status) tuples, oldest first."""
    if len(history) < 2:
        return None

    points = [TrendPoint(date=d, value=v, status=s) for d, v, s in history]

    # Simple trend: compare last two values
    prev, curr = points[-2], points[-1]
    if curr.value > prev.value * 1.05:
        if curr.status in ("high", "critical_high") or prev.status in ("high", "critical_high"):
            direction = "worsening"
        elif curr.status in ("low", "critical_low") or prev.status in ("low", "critical_low"):
            direction = "improving"
        else:
            direction = "increasing"
    elif curr.value < prev.value * 0.95:
        if curr.status in ("low", "critical_low") or prev.status in ("low", "critical_low"):
            direction = "worsening"
        elif curr.status in ("high", "critical_high") or prev.status in ("high", "critical_high"):
            direction = "improving"
        else:
            direction = "decreasing"
    else:
        direction = "stable"

    return BiomarkerTrend(points=points, direction=direction, name="", display_name="", unit="")
