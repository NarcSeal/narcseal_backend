from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer, OfficerRole
from app.dependencies import get_current_officer, get_regional_admin
from pydantic import BaseModel

router = APIRouter(prefix="/officers", tags=["Officers"])

from typing import Optional
from sqlalchemy import or_

@router.get("/")
def get_officers(q: Optional[str] = None, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns a list of officers based on the current user's role."""
    query = db.query(Officer)
    
    # Regional Admins can only see officers in their region
    if current_officer.role == OfficerRole.REGIONAL_ADMIN:
        query = query.filter(Officer.region_id == current_officer.region_id)
    # Field officers shouldn't be able to list all officers
    elif current_officer.role == OfficerRole.OFFICER:
        raise HTTPException(status_code=403, detail="Not authorized to view officer list")
        
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Officer.full_name.ilike(search_term),
                Officer.badge_id.ilike(search_term),
                Officer.station_code.ilike(search_term)
            )
        )
        
    officers = query.all()
    # Map to frontend expected format
    result_list = []
    from app.models.test_record import TestRecord
    for o in officers:
        total = db.query(TestRecord).filter(TestRecord.officer_badge_id == o.badge_id).count()
        positive = db.query(TestRecord).filter(TestRecord.officer_badge_id == o.badge_id, TestRecord.test_result == "POSITIVE").count()
        result_list.append({
            "id": str(o.id),
            "badge_id": o.badge_id,
            "name": o.full_name,
            "rank": o.rank,
            "region_id": o.region_id,
            "station": o.station_code,
            "total_tests": total,
            "positive_count": positive, 
            "last_active": "Just now", 
            "status": "ACTIVE" if o.is_active else "OFFLINE",
            "sync_status": "SYNCED",
            "device_model": "NCB-Spec Device",
        })
    return result_list

@router.get("/{badge_id}")
def get_officer(badge_id: str, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Get details for a specific officer."""
    officer = db.query(Officer).filter(Officer.badge_id == badge_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
        
    # Security check to ensure they can view this officer
    if current_officer.role == OfficerRole.OFFICER and current_officer.badge_id != badge_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this officer")
    if current_officer.role == OfficerRole.REGIONAL_ADMIN and current_officer.region_id != officer.region_id:
        raise HTTPException(status_code=403, detail="Not authorized to view officers outside your region")
        
    from app.models.test_record import TestRecord
    total = db.query(TestRecord).filter(TestRecord.officer_badge_id == officer.badge_id).count()
    positive = db.query(TestRecord).filter(TestRecord.officer_badge_id == officer.badge_id, TestRecord.test_result == "POSITIVE").count()

    return {
        "id": str(officer.id),
        "badge_id": officer.badge_id,
        "name": officer.full_name,
        "rank": officer.rank,
        "station": officer.station_code,
        "total_tests": total,
        "positive_count": positive,
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
    if current_officer.role == OfficerRole.OFFICER and current_officer.badge_id != badge_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if current_officer.role == OfficerRole.REGIONAL_ADMIN:
        target_officer = db.query(Officer).filter(Officer.badge_id == badge_id).first()
        if not target_officer or target_officer.region_id != current_officer.region_id:
            raise HTTPException(status_code=403, detail="Not authorized to view tests for this region")
        
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

class OfficerCreate(BaseModel):
    badge_id: str
    full_name: str
    username: str
    password: str
    rank: str
    station_code: str

@router.post("/")
def create_officer(officer: OfficerCreate, db: Session = Depends(get_db), admin: Officer = Depends(get_regional_admin)):
    from app.services.auth_service import get_password_hash
    
    existing = db.query(Officer).filter(Officer.username == officer.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    existing_badge = db.query(Officer).filter(Officer.badge_id == officer.badge_id).first()
    if existing_badge:
        raise HTTPException(status_code=400, detail="Badge ID already exists")

    # Inherit region from the admin creating them
    # If a MAIN_ADMIN is creating an officer, we might need a region_id passed, but for now we enforce Regional Admin creation
    region_id = admin.region_id
    if not region_id:
        raise HTTPException(status_code=400, detail="Admin has no region assigned.")
    
    db_officer = Officer(
        badge_id=officer.badge_id,
        full_name=officer.full_name,
        username=officer.username,
        hashed_password=get_password_hash(officer.password),
        rank=officer.rank,
        station_code=officer.station_code,
        region_id=region_id,
        district="N/A", # Deprecated field
        state="N/A", # Deprecated field
        role=OfficerRole.OFFICER
    )
    db.add(db_officer)
    db.commit()
    db.refresh(db_officer)
    
    return {"message": "Officer created successfully", "id": db_officer.id}
