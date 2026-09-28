from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, Text
from sqlalchemy.sql import func
from app.database import Base

class TestRecord(Base):
    __tablename__ = "test_records"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(36), unique=True, index=True, nullable=False) # UUID
    officer_badge_id = Column(String(20), index=True, nullable=False)
    officer_name = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255))
    test_result = Column(String(50), nullable=False)
    substance = Column(String(100))
    confidence = Column(Float, nullable=False)
    image_hash = Column(String(64), nullable=False) # SHA-256
    previous_hash = Column(String(64), nullable=False)
    record_hash = Column(String(64), nullable=False, index=True)
    device_id = Column(String(100), nullable=False)
    station_code = Column(String(20), nullable=False, index=True)
    district = Column(String(50), nullable=False, index=True)
    state = Column(String(50), nullable=False)
    test_kit_type = Column(String(50), nullable=True)
    sample_id = Column(String(100), nullable=True, index=True)
    sample_type = Column(String(50), nullable=True)
    is_sealed = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
