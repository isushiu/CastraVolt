from datetime import datetime
from sqlalchemy import Boolean,CheckConstraint,DateTime,ForeignKey,Index,Integer,String,Text,text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from castravolt.database import Base


class RegistrationVersion(Base):
    __tablename__='registration_source_versions'
    __table_args__=(Index('uq_registration_active','active',unique=True,postgresql_where=text('active')),)
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    manifest:Mapped[dict]=mapped_column(JSONB)
    active:Mapped[bool]=mapped_column(Boolean,default=False)
    imported_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))


class RegistrationMonth(Base):
    __tablename__='registration_months'
    __table_args__=(CheckConstraint('count >= 0'),)
    version_id:Mapped[str]=mapped_column(ForeignKey('registration_source_versions.id',ondelete='CASCADE'),primary_key=True)
    state:Mapped[str]=mapped_column(String(40),primary_key=True)
    month:Mapped[str]=mapped_column(String(7),primary_key=True)
    count:Mapped[int]=mapped_column(Integer)


class TrendSummary(Base):
    __tablename__='trend_summary_cache'
    key:Mapped[str]=mapped_column(String(64),primary_key=True)
    version_id:Mapped[str]=mapped_column(ForeignKey('registration_source_versions.id',ondelete='CASCADE'),index=True)
    model:Mapped[str]=mapped_column(String(120))
    prompt_version:Mapped[str]=mapped_column(String(40))
    filters:Mapped[dict]=mapped_column(JSONB)
    status:Mapped[str]=mapped_column(String(16))
    content:Mapped[str|None]=mapped_column(Text)
    lease_token:Mapped[str|None]=mapped_column(String(36))
    lease_until:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
