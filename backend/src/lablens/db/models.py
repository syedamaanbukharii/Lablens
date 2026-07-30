"""Database models.

Real persistence. Not a dict. A restart doesn't lose patient data.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from lablens.config import get_settings


def _uid() -> str:
    return secrets.token_urlsafe(12)


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String(16), primary_key=True, default=_uid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    date_of_birth = Column(String(10), default="")  # stored as string, never a raw date
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    reports = relationship("LabReport", back_populates="user", cascade="all, delete-orphan")


class LabReport(Base):
    __tablename__ = "lab_reports"

    id = Column(String(16), primary_key=True, default=_uid)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), default="")
    report_date = Column(DateTime, nullable=True, index=True)
    lab_name = Column(String(255), default="")
    raw_text = Column(Text, default="")
    summary = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending | processed | error
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="reports")
    biomarkers = relationship("Biomarker", back_populates="report", cascade="all, delete-orphan")


class Biomarker(Base):
    __tablename__ = "biomarkers"
    __table_args__ = (
        UniqueConstraint("report_id", "name", name="uq_report_biomarker"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(16), ForeignKey("lab_reports.id"), nullable=False, index=True)
    user_id = Column(String(16), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    display_name = Column(String(150), default="")
    value = Column(Float, nullable=True)
    unit = Column(String(30), default="")
    ref_low = Column(Float, nullable=True)
    ref_high = Column(Float, nullable=True)
    status = Column(String(20), default="normal")  # normal | low | high | critical_low | critical_high
    category = Column(String(50), default="general")  # blood_sugar, lipid, liver, kidney, cbc, thyroid, etc.
    interpretation = Column(Text, default="")
    report_date = Column(DateTime, nullable=True)

    report = relationship("LabReport", back_populates="biomarkers")


# --- Engine & session ---

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session
