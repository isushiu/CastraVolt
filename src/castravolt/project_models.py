from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from castravolt.database import Base


class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Site(Base):
    __tablename__ = 'sites'
    __table_args__ = (CheckConstraint('latitude BETWEEN -90 AND 90'), CheckConstraint('longitude BETWEEN -180 AND 180'))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    state: Mapped[str | None] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(60))
    address: Mapped[str] = mapped_column(String(500), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Prediction(Base):
    __tablename__ = 'predictions'
    __table_args__ = (CheckConstraint('displayed_total >= 1'),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    site_id: Mapped[UUID] = mapped_column(ForeignKey('sites.id', ondelete='CASCADE'), index=True)
    requester_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    input_snapshot: Mapped[dict] = mapped_column(JSONB)
    raw_estimate: Mapped[float] = mapped_column(Float)
    displayed_total: Mapped[int] = mapped_column(Integer)
    model_version: Mapped[str] = mapped_column(String(100))
    extraction_rule_version: Mapped[str] = mapped_column(String(100))
    poi_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    adoption_reference_year: Mapped[int] = mapped_column(Integer)
    adoption_value: Mapped[int] = mapped_column(Integer)
    rounding_policy: Mapped[str] = mapped_column(String(100))
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
