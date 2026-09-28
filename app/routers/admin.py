from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer, OfficerRole, OfficerRank
from app.models.region import Region
from app.dependencies import get_main_admin
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

class RegionalAdminCreate(BaseModel):
    badge_id: str
    full_name: str
    username: str
    password: str
    region_id: int

@router.get("/regional-admins")
def get_regional_admins(db: Session = Depends(get_db), admin: Officer = Depends(get_main_admin)):
    admins = db.query(Officer).filter(Officer.role == OfficerRole.REGIONAL_ADMIN).all()
    result = []
    for a in admins:
        region = db.query(Region).filter(Region.id == a.region_id).first()
        officers_count = db.query(Officer).filter(Officer.region_id == a.region_id, Officer.role == OfficerRole.OFFICER).count()
        # count tests
        from app.models.test_record import TestRecord
        officer_badges = [o.badge_id for o in db.query(Officer).filter(Officer.region_id == a.region_id).all()]
        tests_count = db.query(TestRecord).filter(TestRecord.officer_badge_id.in_(officer_badges)).count() if officer_badges else 0
        
        result.append({
            "id": a.id,
            "badge_id": a.badge_id,
            "name": a.full_name,
            "region": region.name if region else "Unknown",
            "region_id": a.region_id,
            "officers": officers_count,
            "total_tests": tests_count,
            "status": "Active" if a.is_active else "Inactive"
        })
    return result

@router.post("/regional-admins")
def create_regional_admin(admin_data: RegionalAdminCreate, db: Session = Depends(get_db), admin: Officer = Depends(get_main_admin)):
    from app.services.auth_service import get_password_hash
    
    existing = db.query(Officer).filter(Officer.username == admin_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
        
        
    db_admin = Officer(
        badge_id=admin_data.badge_id,
        full_name=admin_data.full_name,
        username=admin_data.username,
        hashed_password=get_password_hash(admin_data.password),
        rank=OfficerRank.SP, # Or whatever default
        station_code="HQ",
        district="N/A",
        state="N/A",
        role=OfficerRole.REGIONAL_ADMIN,
        region_id=admin_data.region_id
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    
    return {"message": "Regional Admin created successfully", "id": db_admin.id}
