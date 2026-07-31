"""FastAPI application.

Every data endpoint requires JWT authentication. No theater RBAC — real auth.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lablens import __version__
from lablens.agent.pipeline import process_lab_report
from lablens.auth.service import AuthService, get_current_user
from lablens.config import get_settings
from lablens.db.models import Biomarker, LabReport, User, get_db, init_db
from fastapi.responses import JSONResponse
import traceback


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="LabLens", version=__version__, description="AI lab report summarizer", lifespan=lifespan)
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500, 
        content={"message": str(exc), "traceback": traceback.format_exc()},
        headers={"Access-Control-Allow-Origin": "*"}
    )


# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str


# ---------- Auth routes ----------

@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered.")

    user = User(
        email=req.email,
        hashed_password=AuthService.hash_password(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = AuthService.create_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, full_name=user.full_name)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await AuthService.authenticate(db, form.username, form.password)
    if not user:
        raise HTTPException(401, "Invalid email or password.")
    token = AuthService.create_token(user.id, user.email)
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, full_name=user.full_name)


@app.get("/api/auth/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(user_id=user.id, email=user.email, full_name=user.full_name)


# ---------- Report routes ----------

@app.post("/api/reports/upload")
async def upload_report(
    file: UploadFile = File(...),
    report_date: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a lab report PDF and get AI-powered analysis."""
    if not file.filename:
        raise HTTPException(422, "Filename is required.")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_mb}MB.")

    parsed_date = None
    if report_date:
        try:
            parsed_date = datetime.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(422, "Invalid date format. Use ISO 8601 (YYYY-MM-DD).") from None

    result = await process_lab_report(db, user.id, content, file.filename, parsed_date)
    return result


@app.get("/api/reports")
async def list_reports(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports for the authenticated user."""
    result = await db.execute(
        select(LabReport)
        .where(LabReport.user_id == user.id)
        .order_by(LabReport.report_date.desc())
    )
    reports = result.scalars().all()
    return [
        {
            "report_id": r.id,
            "filename": r.filename,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "status": r.status,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@app.get("/api/reports/{report_id}")
async def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single report with all biomarkers."""
    result = await db.execute(
        select(LabReport).where(LabReport.id == report_id, LabReport.user_id == user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found.")

    markers = await db.execute(
        select(Biomarker).where(Biomarker.report_id == report_id).order_by(Biomarker.category)
    )

    return {
        "report_id": report.id,
        "filename": report.filename,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "status": report.status,
        "summary": report.summary,
        "diet_suggestions": report.diet_suggestions,
        "doctor_recommendation": report.doctor_recommendation,
        "markers": [
            {
                "name": m.name,
                "display_name": m.display_name,
                "value": m.value,
                "unit": m.unit,
                "ref_low": m.ref_low,
                "ref_high": m.ref_high,
                "status": m.status,
                "category": m.category,
                "interpretation": m.interpretation,
            }
            for m in markers.scalars().all()
        ],
    }


# ---------- Trends ----------

@app.get("/api/trends")
async def get_trends(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get historical trends for all biomarkers."""
    result = await db.execute(
        select(Biomarker)
        .where(Biomarker.user_id == user.id)
        .order_by(Biomarker.name, Biomarker.report_date.asc())
    )
    all_markers = result.scalars().all()

    # Group by biomarker name
    grouped: dict[str, list] = {}
    for m in all_markers:
        grouped.setdefault(m.name, []).append(m)

    trends = []
    for name, markers in grouped.items():
        if len(markers) < 2:
            continue

        points = [
            {
                "date": m.report_date.strftime("%Y-%m-%d") if m.report_date else "?",
                "value": m.value,
                "status": m.status,
            }
            for m in markers
        ]

        prev, curr = markers[-2], markers[-1]
        if curr.value and prev.value:
            if curr.value > prev.value * 1.05:
                direction = "increasing"
            elif curr.value < prev.value * 0.95:
                direction = "decreasing"
            else:
                direction = "stable"
        else:
            direction = "stable"

        trends.append({
            "name": name,
            "display_name": markers[0].display_name,
            "unit": markers[0].unit,
            "ref_low": markers[0].ref_low,
            "ref_high": markers[0].ref_high,
            "direction": direction,
            "points": points,
        })

    return {"trends": trends}


# ---------- Dashboard ----------

@app.get("/api/dashboard")
async def dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard summary for the authenticated user."""
    report_count = await db.execute(
        select(func.count(LabReport.id)).where(LabReport.user_id == user.id)
    )
    total_reports = report_count.scalar() or 0

    latest = await db.execute(
        select(LabReport)
        .where(LabReport.user_id == user.id)
        .order_by(LabReport.report_date.desc())
        .limit(1)
    )
    latest_report = latest.scalar_one_or_none()

    # Count abnormal markers in the latest report
    abnormal = 0
    if latest_report:
        abn_count = await db.execute(
            select(func.count(Biomarker.id))
            .where(Biomarker.report_id == latest_report.id, Biomarker.status != "normal")
        )
        abnormal = abn_count.scalar() or 0

    return {
        "total_reports": total_reports,
        "latest_report_id": latest_report.id if latest_report else None,
        "latest_report_date": latest_report.report_date.isoformat() if latest_report and latest_report.report_date else None,
        "latest_summary": latest_report.summary if latest_report else None,
        "abnormal_markers_latest": abnormal,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__}
