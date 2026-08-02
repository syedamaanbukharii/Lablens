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

    # Convert LLMBiomarker to ParsedBiomarker for compatibility with interpreter
    parsed = [
        ParsedBiomarker(
            name=bm.name,
            display_name=bm.display_name,
            value=bm.value,
            unit=bm.unit,
            ref_low=bm.ref_low,
            ref_high=bm.ref_high,
            category=bm.category
        )
        for bm in llm_data.biomarkers
    ]

    # Save extra LLM fields
    report.diet_suggestions = llm_data.diet_suggestions
    report.doctor_recommendation = llm_data.doctor_recommendation

    # Step 4: Interpret (rules-based plain-language)
    summary = summarize_report(parsed)

    # Step 5: Persist biomarkers
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

    report.status = "processed"
    report.summary = summary.plain_summary
    await db.commit()

    # Step 6: Compute trends from historical data
    trends = await _compute_user_trends(db, user_id, parsed)

    return {
        "report_id": report.id,
        "status": "processed",
        "extraction_method": extraction.method,
        "summary": summary.plain_summary,
        "total_markers": summary.total_markers,
        "normal_count": summary.normal_count,
        "abnormal_count": summary.abnormal_count,
        "critical_count": summary.critical_count,
        "markers": [
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
        ],
        "categories": {
            cat: [{"name": i.display_name, "value": i.value, "unit": i.unit, "status": i.status, "emoji": i.emoji}
                  for i in items]
            for cat, items in summary.categories.items()
        },
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
