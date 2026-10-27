from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from castravolt.database import Base


class PoiCache(Base):
    __tablename__='poi_cache'
    key:Mapped[str]=mapped_column(String(64),primary_key=True)
    counts:Mapped[dict]=mapped_column(JSONB)
    provenance:Mapped[dict]=mapped_column(JSONB)
    extracted_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
