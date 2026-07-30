"""Test the interpretation engine."""
from lablens.analysis.interpreter import summarize_report
from lablens.extraction.parser import parse_biomarkers
from tests.conftest import SAMPLE_LAB_TEXT


def test_summary_counts():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    summary = summarize_report(markers)
    assert summary.total_markers >= 12
    assert summary.normal_count > 0
    assert summary.abnormal_count > 0  # glucose, cholesterol, etc. are abnormal


def test_high_glucose_interpretation():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    summary = summarize_report(markers)
    glucose = next((i for i in summary.insights if i.name == "fasting_blood_glucose"), None)
    assert glucose is not None
    assert glucose.status == "high"
    assert "elevated" in glucose.interpretation.lower() or "prediabetes" in glucose.interpretation.lower()


def test_low_vitamin_d_interpretation():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    summary = summarize_report(markers)
    vd = next((i for i in summary.insights if i.name == "vitamin_d"), None)
    assert vd is not None
    assert vd.status in ("low", "critical_low")
    assert "vitamin d" in vd.interpretation.lower()


def test_normal_gets_positive_message():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    summary = summarize_report(markers)
    creat = next((i for i in summary.insights if i.name == "creatinine"), None)
    assert creat is not None
    assert creat.status == "normal"
    assert "normal" in creat.interpretation.lower()


def test_summary_has_plain_text():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    summary = summarize_report(markers)
    assert len(summary.plain_summary) > 50
    assert "⚠️" in summary.plain_summary or "✅" in summary.plain_summary


def test_categories_grouped():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    summary = summarize_report(markers)
    assert "blood_sugar" in summary.categories
    assert "lipid" in summary.categories
