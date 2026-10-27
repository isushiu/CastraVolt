from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from castravolt.database import Base


class GeocodeCache(Base):
    __tablename__='geocode_cache'
    key: Mapped[str] = mapped_column(String(64),primary_key=True)
    results: Mapped[list] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),index=True)
