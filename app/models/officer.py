from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.sql import func
from app.database import Base
import enum
from sqlalchemy.orm import relationship

class OfficerRank(str, enum.Enum):
    CONSTABLE = "constable"
    HEAD_CONSTABLE = "head_constable"
    SUB_INSPECTOR = "sub_inspector"
    INSPECTOR = "inspector"
    DSP = "dsp"
    SP = "sp"
    DIG = "dig"
    IG = "ig"

class OfficerRole(str, enum.Enum):
    OFFICER = "officer"                    # Can only see their own tests
    REGIONAL_ADMIN = "regional_admin"      # Can see all tests in their region
    MAIN_ADMIN = "main_admin"              # Can see everything (God mode)

class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    badge_id = Column(String(20), unique=True, nullable=False, index=True)  # e.g., "NCB-4421"
    full_name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    rank = Column(Enum(OfficerRank), nullable=False)
    role = Column(Enum(OfficerRole), default=OfficerRole.OFFICER)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True) # Only NULL for MAIN_ADMIN
    station_code = Column(String(20), nullable=False)  # e.g., "MUM-NCB-01"
    district = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    phone_number = Column(String(15))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    region = relationship("Region", back_populates="officers")
