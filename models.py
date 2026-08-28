from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def utcnow():
    return datetime.now(timezone.utc)

class ResultRecord(Base):
    __tablename__ = "result_records"
    __table_args__ = (
        UniqueConstraint("probidhan", "roll", "exam_year", "semester", name="uq_result_identity"),
        Index("ix_result_lookup", "probidhan", "roll"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    probidhan: Mapped[str] = mapped_column(String(20), index=True)
    roll: Mapped[str] = mapped_column(String(30), index=True)
    registration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exam_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    referred_subjects: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
