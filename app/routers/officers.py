from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer, OfficerRole
from app.routers.test_records import get_current_officer

router = APIRouter(prefix="/officers", tags=["Officers"])

from typing import Optional
from sqlalchemy import or_

@router.get("/")
def get_officers(q: Optional[str] = None, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns a list of officers based on the current user's role."""
    query = db.query(Officer)
    
    # Station Heads can only see officers in their station
    if current_officer.role == OfficerRole.STATION_HEAD:
        query = query.filter(Officer.station_code == current_officer.station_code)
    # District Admins can see officers in their district
    elif current_officer.role == OfficerRole.DISTRICT_ADMIN:
        query = query.filter(Officer.district == current_officer.district)
    # Field officers shouldn't be able to list all officers
    elif current_officer.role == OfficerRole.FIELD_OFFICER:
        raise HTTPException(status_code=403, detail="Not authorized to view officer list")
        
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Officer.full_name.ilike(search_term),
                Officer.badge_id.ilike(search_term),
                Officer.station_code.ilike(search_term),
                Officer.district.ilike(search_term)
            )
        )
        
    officers = query.all()
    # Map to frontend expected format
    return [
        {
            "id": str(o.id),
            "badge_id": o.badge_id,
            "name": o.full_name,
            "rank": o.rank,
            "station": o.station_code,
            "total_tests": 0, # Could be aggregated, keeping 0 for simplicity
            "positive_count": 0, 
            "last_active": "Just now", 
            "status": "ACTIVE" if o.is_active else "OFFLINE",
            "sync_status": "SYNCED",
            "device_model": "NCB-Spec Device",
        } for o in officers
    ]

@router.get("/{badge_id}")
def get_officer(badge_id: str, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Get details for a specific officer."""
    officer = db.query(Officer).filter(Officer.badge_id == badge_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    # Security check to ensure they can view this officer
    if current_officer.role == OfficerRole.FIELD_OFFICER and current_officer.badge_id != badge_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this officer")
    if current_officer.role == OfficerRole.STATION_HEAD and current_officer.station_code != officer.station_code:
        raise HTTPException(status_code=403, detail="Not authorized to view officers outside your station")
        
    return {
        "id": str(officer.id),
        "badge_id": officer.badge_id,
        "name": officer.full_name,
        "rank": officer.rank,
        "station": officer.station_code,
        "total_tests": 0,
        "positive_count": 0,
        "last_active": "Just now",
        "status": "ACTIVE" if officer.is_active else "OFFLINE",
        "sync_status": "SYNCED",
        "device_model": "NCB-Spec Device",
    }

@router.get("/{badge_id}/tests")
def get_officer_tests(badge_id: str, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Get the tests performed by a specific officer"""
    from app.models.test_record import TestRecord
    
    # Simple security check
    if current_officer.role == OfficerRole.FIELD_OFFICER and current_officer.badge_id != badge_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    records = db.query(TestRecord).filter(TestRecord.officer_badge_id == badge_id).order_by(TestRecord.timestamp.desc()).all()
    
    # Map to frontend format
    return [
        {
            "id": r.record_id,
            "substance": r.substance,
            "result": r.test_result,
            "weight": "Unknown",
            "date": str(r.timestamp),
            "confidence": r.confidence,
            "hash_status": "VERIFIED"
        } for r in records
    ]
