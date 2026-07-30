import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lablens.db.models import Base

SAMPLE_LAB_TEXT = """
LABORATORY REPORT
Patient: John Doe
Date: 2025-06-15

BLOOD SUGAR
Fasting Blood Glucose: 126 mg/dL (70 - 100)
HbA1c: 6.8% (< 5.7)

LIPID PANEL
Total Cholesterol: 245 mg/dL (< 200)
HDL Cholesterol: 38 mg/dL (> 40)
LDL Cholesterol: 165 mg/dL (< 100)
Triglycerides: 210 mg/dL (< 150)

LIVER FUNCTION
ALT (SGPT): 42 U/L (7 - 56)
AST (SGOT): 35 U/L (10 - 40)

KIDNEY FUNCTION
Creatinine: 0.9 mg/dL (0.7 - 1.3)
BUN: 15 mg/dL (7 - 20)

COMPLETE BLOOD COUNT
Hemoglobin: 14.5 g/dL (12 - 17.5)
WBC: 7.2 x10³/µL (4 - 11)
Platelets: 250 x10³/µL (150 - 400)

THYROID
TSH: 2.1 mIU/L (0.4 - 4.0)

VITAMINS
Vitamin D: 18 ng/mL (30 - 100)
Vitamin B12: 350 pg/mL (200 - 900)
"""


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
