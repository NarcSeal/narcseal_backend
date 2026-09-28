from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.database import get_db
from app.models.officer import Officer, OfficerRole
from app.models.test_record import TestRecord
from app.dependencies import get_current_officer

router = APIRouter(prefix="/records", tags=["Records"])

def format_record(record: TestRecord):
    return {
        "id": record.record_id,
        "timestamp": str(record.timestamp),
        "officer_name": record.officer_name,
        "officer_badge": record.officer_badge_id,
        "station": record.station_code,
        "substance": record.substance,
        "result": record.test_result,
        "weight_grams": 0, # Not in DB schema yet
        "confidence_score": record.confidence,
        "gps_lat": record.latitude,
        "gps_lng": record.longitude,
        "location_name": record.address,
        "sample_type": record.sample_type or "Unknown",
        "sample_id": record.sample_id,
        "test_kit_type": record.test_kit_type,
        "notes": record.notes,
        "is_sealed": record.is_sealed,
        "device_id": record.device_id,
        "image_url": f"/uploads/{record.record_id}.jpg", # Serves the actual uploaded image
        "sha256_hash": record.image_hash,
        "prev_block_hash": record.previous_hash,
        "merkle_root": record.record_hash,
        "tamper_flag": False,
        "court_admissible": True,
    }

@router.get("/")
def get_all_records(
    result: Optional[str] = None,
    substance: Optional[str] = None,
    station: Optional[str] = None,
    search: Optional[str] = None,
    current_officer: Officer = Depends(get_current_officer), 
    db: Session = Depends(get_db)
):
    """Returns a list of records mapped to dashboard's expected JSON format"""
    query = db.query(TestRecord)
    
    # Role-based filtering
    if current_officer.role == OfficerRole.OFFICER:
        query = query.filter(TestRecord.officer_badge_id == current_officer.badge_id)
    elif current_officer.role == OfficerRole.REGIONAL_ADMIN:
        query = query.join(Officer, TestRecord.officer_badge_id == Officer.badge_id)\
                     .filter(Officer.region_id == current_officer.region_id)
    elif current_officer.role == OfficerRole.MAIN_ADMIN:
        pass

    # Query param filtering
    if result and result != 'ALL':
        query = query.filter(TestRecord.test_result == result)
    if substance and substance != 'ALL':
        query = query.filter(TestRecord.substance.ilike(f"%{substance}%"))
    if station and station != 'ALL':
        query = query.filter(TestRecord.station_code == station)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                TestRecord.record_id.ilike(search_term),
                TestRecord.officer_name.ilike(search_term),
                TestRecord.substance.ilike(search_term),
                TestRecord.station_code.ilike(search_term)
            )
        )
        
    records = query.order_by(TestRecord.timestamp.desc()).all()
    return [format_record(r) for r in records]

@router.get("/{record_id}")
def get_record(record_id: str, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns the details of a single record"""
    record = db.query(TestRecord).filter(TestRecord.record_id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    # Role check
    if current_officer.role == OfficerRole.OFFICER and record.officer_badge_id != current_officer.badge_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if current_officer.role == OfficerRole.REGIONAL_ADMIN:
        record_officer = db.query(Officer).filter(Officer.badge_id == record.officer_badge_id).first()
        if not record_officer or record_officer.region_id != current_officer.region_id:
            raise HTTPException(status_code=403, detail="Not authorized to view records from other regions")
        
    return format_record(record)
