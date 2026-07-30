"""Test biomarker parser — the core extraction logic."""
from lablens.extraction.parser import classify_status, parse_biomarkers
from tests.conftest import SAMPLE_LAB_TEXT


def test_parses_blood_sugar():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    glucose = next((m for m in markers if m.name == "fasting_blood_glucose"), None)
    assert glucose is not None
    assert glucose.value == 126.0
    assert glucose.ref_low == 70.0
    assert glucose.ref_high == 100.0


def test_parses_hba1c():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    a1c = next((m for m in markers if m.name == "hba1c"), None)
    assert a1c is not None
    assert a1c.value == 6.8


def test_parses_lipid_panel():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    names = {m.name for m in markers}
    assert "total_cholesterol" in names
    assert "hdl_cholesterol" in names
    assert "ldl_cholesterol" in names
    assert "triglycerides" in names


def test_parses_cbc():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    hgb = next((m for m in markers if m.name == "hemoglobin"), None)
    assert hgb is not None
    assert hgb.value == 14.5


def test_parses_vitamin_d():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    vd = next((m for m in markers if m.name == "vitamin_d"), None)
    assert vd is not None
    assert vd.value == 18.0


def test_extracts_correct_count():
    markers = parse_biomarkers(SAMPLE_LAB_TEXT)
    assert len(markers) >= 12  # at least 12 markers in sample


def test_classify_normal():
    assert classify_status(85.0, 70.0, 100.0) == "normal"


def test_classify_high():
    assert classify_status(126.0, 70.0, 100.0) == "high"


def test_classify_critical_high():
    assert classify_status(300.0, 70.0, 100.0) == "critical_high"


def test_classify_low():
    assert classify_status(60.0, 70.0, 100.0) == "low"


def test_classify_critical_low():
    assert classify_status(3.0, 12.0, 17.5) == "critical_low"


def test_empty_text():
    assert parse_biomarkers("") == []


def test_garbage_text():
    assert parse_biomarkers("This is not a lab report at all.") == []
