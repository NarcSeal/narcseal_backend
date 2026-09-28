from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True) # e.g., "Ahmedabad Region"
    code = Column(String(20), unique=True, nullable=False) # e.g., "AHM"
    status = Column(String(20), default="ACTIVE") # "ACTIVE", "INACTIVE"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    officers = relationship("Officer", back_populates="region")
