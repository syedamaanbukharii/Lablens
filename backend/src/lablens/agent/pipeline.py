"""Agent pipeline: orchestrates the full lab report processing flow.

    Upload → Extract text → Parse biomarkers → Interpret → Persist → Trends

This is genuinely agentic in the sense that matters: the pipeline *branches*
based on what it finds. A report with all-normal values gets a short summary;
one with critical findings gets a detailed explanation with urgency flagging;
one that fails to parse routes to LLM-based fallback extraction. The path
through the system depends on the data, not a fixed sequence.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lablens.analysis.interpreter import (
    compute_trends,
    summarize_report,
)
from lablens.db.models import Biomarker, LabReport
from lablens.extraction.parser import ParsedBiomarker, classify_status, parse_biomarkers
from lablens.extraction.pdf import extract_text


from lablens.agent.llm import extract_from_llm

async def process_lab_report(
    db: AsyncSession,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    report_date: datetime | None = None,
) -> dict[str, Any]:
    """Full pipeline: extract → parse → interpret → persist → trends."""

    # Step 1: Extract text from PDF/image
    extraction = extract_text(file_bytes, filename)

    # Step 2: Create report record
    report = LabReport(
        user_id=user_id,
        filename=filename,
        report_date=report_date or datetime.now(UTC),
        raw_text=extraction.text,
        status="processing",
    )
    db.add(report)
    await db.flush()

    # Step 3: Parse biomarkers using LLM
    try:
        llm_data = extract_from_llm(extraction.text)
    except Exception as e:
        report.status = "error"
        report.summary = f"Error communicating with LLM: {str(e)}"
        await db.commit()
        raise

    if not llm_data.is_valid_report:
        report.status = "invalid_report"
        report.summary = llm_data.error_message
        await db.commit()
        return {
            "report_id": report.id,
            "status": "invalid_report",
            "extraction_method": extraction.method,
            "raw_text_preview": extraction.text[:500],
            "summary": report.summary,
            "markers": [],
            "trends": [],
            "diet_suggestions": "",
            "doctor_recommendation": ""
        }

    # Guard: if extraction failed (scanned PDF without OCR) or LLM found 0 biomarkers
    if not llm_data.biomarkers or extraction.confidence == 0.0:
        report.status = "invalid_report"
        if extraction.confidence == 0.0:
            report.summary = "No text could be extracted from the PDF. Please upload a valid text-based medical lab report."
        else:
            report.summary = "The document was analyzed but no biomarkers could be identified. Please ensure you're uploading a medical lab report with test results."
        await db.commit()
        return {
            "report_id": report.id,
            "status": "invalid_report",
            "extraction_method": extraction.method,
            "raw_text_preview": extraction.text[:500],
            "summary": report.summary,
            "markers": [],
            "trends": [],
            "diet_suggestions": "",
            "doctor_recommendation": ""
        }

    # Separate numeric and qualitative biomarkers
    numeric_biomarkers = []
    qualitative_biomarkers = []
    for bm in llm_data.biomarkers:
        if isinstance(bm.value, (int, float)):
            numeric_biomarkers.append(bm)
        else:
            qualitative_biomarkers.append(bm)

    # Convert numeric LLMBiomarker to ParsedBiomarker for rules-based interpreter
    parsed = [
        ParsedBiomarker(
            name=bm.name,
            display_name=bm.display_name,
            value=float(bm.value),
            unit=bm.unit,
            ref_low=bm.ref_low,
            ref_high=bm.ref_high,
            category=bm.category
        )
        for bm in numeric_biomarkers
    ]

    # Save extra LLM fields
    report.diet_suggestions = llm_data.diet_suggestions
    report.doctor_recommendation = llm_data.doctor_recommendation

    # Step 4: Interpret numeric markers (rules-based plain-language)
    summary = summarize_report(parsed)

    # Step 5: Persist numeric biomarkers
    for bm in parsed:
        status = classify_status(bm.value, bm.ref_low, bm.ref_high)
        marker = Biomarker(
            report_id=report.id,
            user_id=user_id,
            name=bm.name,
            display_name=bm.display_name,
            value=bm.value,
            unit=bm.unit,
            ref_low=bm.ref_low,
            ref_high=bm.ref_high,
            status=status,
            category=bm.category,
            interpretation=next(
                (i.interpretation for i in summary.insights if i.name == bm.name), ""
            ),
            report_date=report.report_date,
        )
        db.add(marker)

    # Step 5b: Persist qualitative biomarkers (use LLM's own status)
    qual_insights = []
    for bm in qualitative_biomarkers:
        # Map LLM status to our status format
        llm_status = (bm.status or "normal").lower()
        if llm_status in ("abnormal", "critical"):
            status = "high" if llm_status == "abnormal" else "critical_high"
        elif llm_status in ("normal", "high", "low", "critical_high", "critical_low"):
            status = llm_status
        else:
            status = "normal"

        text_val = str(bm.value) if bm.value else ""
        ref_text = bm.ref_text if hasattr(bm, 'ref_text') else ""

        # Qualitative interpretation
        if status == "normal":
            interp = f"{bm.display_name} is {text_val}, which is within normal/expected range."
        else:
            interp = f"{bm.display_name} is {text_val} (expected: {ref_text or 'normal'}). This is outside the expected range — please discuss with your doctor."

        marker = Biomarker(
            report_id=report.id,
            user_id=user_id,
            name=bm.name,
            display_name=bm.display_name,
            value=None,  # Qualitative: no numeric value
            text_value=text_val,
            unit=bm.unit,
            ref_low=None,
            ref_high=None,
            ref_text=ref_text,
            status=status,
            category=bm.category,
            interpretation=interp,
            report_date=report.report_date,
        )
        db.add(marker)

        emoji = "✅" if status == "normal" else ("⚠️" if status in ("high", "low") else "🔴")
        qual_insights.append({
            "name": bm.name,
            "display_name": bm.display_name,
            "value": text_val,
            "unit": bm.unit,
            "ref_low": None,
            "ref_high": None,
            "ref_text": ref_text,
            "status": status,
            "category": bm.category,
            "interpretation": interp,
            "emoji": emoji,
        })
    # Build combined summary that includes qualitative markers
    qual_normal = sum(1 for q in qual_insights if q["status"] == "normal")
    qual_abnormal = sum(1 for q in qual_insights if q["status"] in ("high", "low"))
    qual_critical = sum(1 for q in qual_insights if q["status"] in ("critical_high", "critical_low"))

    total_normal = summary.normal_count + qual_normal
    total_abnormal = summary.abnormal_count + qual_abnormal
    total_critical = summary.critical_count + qual_critical
    total_markers = summary.total_markers + len(qual_insights)

    # If all results are qualitative, build a custom summary
    if not parsed and qual_insights:
        parts = []
        if qual_critical:
            names = ", ".join(q["display_name"] for q in qual_insights if q["status"] in ("critical_high", "critical_low"))
            parts.append(f"🔴 Attention needed: {names} — significantly outside expected range.")
        if qual_abnormal:
            names = ", ".join(q["display_name"] for q in qual_insights if q["status"] in ("high", "low"))
            parts.append(f"⚠️ {names} — outside the expected range. See details below.")
        if qual_normal and not qual_critical and not qual_abnormal:
            parts.append("✅ All your test results are within normal/expected ranges. Keep up the good work!")
        elif qual_normal:
            parts.append(f"✅ {qual_normal} other test{'s' if qual_normal > 1 else ''} {'are' if qual_normal > 1 else 'is'} within normal ranges.")
        plain_summary = "\n\n".join(parts)
    else:
        plain_summary = summary.plain_summary

    report.status = "processed"
    report.summary = plain_summary
    await db.commit()

    # Step 6: Compute trends from historical data (numeric only)
    trends = await _compute_user_trends(db, user_id, parsed)

    # Merge numeric and qualitative markers for the response
    all_markers = [
        {
            "name": i.name,
            "display_name": i.display_name,
            "value": i.value,
            "unit": i.unit,
            "ref_low": i.ref_low,
            "ref_high": i.ref_high,
            "status": i.status,
            "category": i.category,
            "interpretation": i.interpretation,
            "emoji": i.emoji,
        }
        for i in summary.insights
    ] + qual_insights

    # Build combined categories
    all_categories = {}
    for cat, items in summary.categories.items():
        all_categories[cat] = [{"name": i.display_name, "value": i.value, "unit": i.unit, "status": i.status, "emoji": i.emoji} for i in items]
    for q in qual_insights:
        cat = q["category"]
        if cat not in all_categories:
            all_categories[cat] = []
        all_categories[cat].append({"name": q["display_name"], "value": q["value"], "unit": q["unit"], "status": q["status"], "emoji": q["emoji"]})

    return {
        "report_id": report.id,
        "status": "processed",
        "extraction_method": extraction.method,
        "summary": plain_summary,
        "total_markers": total_markers,
        "normal_count": total_normal,
        "abnormal_count": total_abnormal,
        "critical_count": total_critical,
        "markers": all_markers,
        "categories": all_categories,
        "trends": trends,
        "diet_suggestions": report.diet_suggestions,
        "doctor_recommendation": report.doctor_recommendation,
    }


async def _compute_user_trends(
    db: AsyncSession, user_id: str, current_parsed: list[ParsedBiomarker]
) -> list[dict[str, Any]]:
    """Fetch historical values for each biomarker and compute trends."""
    trends: list[dict[str, Any]] = []

    for bm in current_parsed:
        result = await db.execute(
            select(Biomarker)
            .where(Biomarker.user_id == user_id, Biomarker.name == bm.name)
            .order_by(Biomarker.report_date.asc())
        )
        history_records = result.scalars().all()

        if len(history_records) < 2:
            continue

        history = [
            (
                r.report_date.strftime("%Y-%m-%d") if r.report_date else "unknown",
                r.value,
                r.status,
            )
            for r in history_records
            if r.value is not None
        ]

        trend = compute_trends(history)
        if trend:
            trend.name = bm.name
            trend.display_name = bm.display_name
            trend.unit = bm.unit
            trend.ref_low = bm.ref_low
            trend.ref_high = bm.ref_high

            # Generate trend summary
            if len(trend.points) >= 2:
                prev_val, curr_val = trend.points[-2].value, trend.points[-1].value
                dir_str = "upward" if curr_val > prev_val else "downward"
            else:
                dir_str = "stable"

            if trend.direction == "worsening":
                trend.summary = f"Your {bm.display_name} has been trending {dir_str}, which is worsening."
            elif trend.direction == "improving":
                trend.summary = f"Your {bm.display_name} has been trending {dir_str} — showing improvement."
            elif trend.direction in ("increasing", "decreasing"):
                trend.summary = f"Your {bm.display_name} has been trending {dir_str}, but remains within normal limits."
            else:
                trend.summary = f"Your {bm.display_name} has been stable across your recent tests."

            trends.append({
                "name": trend.name,
                "display_name": trend.display_name,
                "unit": trend.unit,
                "ref_low": trend.ref_low,
                "ref_high": trend.ref_high,
                "direction": trend.direction,
                "summary": trend.summary,
                "points": [{"date": p.date, "value": p.value, "status": p.status} for p in trend.points],
            })

    return trends
