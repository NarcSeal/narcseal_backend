from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.region import Region
from app.models.officer import Officer, OfficerRole
from app.dependencies import get_main_admin
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/regions", tags=["Regions"])

class RegionCreate(BaseModel):
    name: str
    code: str

class RegionResponse(BaseModel):
    id: int
    name: str
    code: str
    status: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[RegionResponse])
def get_all_regions(db: Session = Depends(get_db), admin: Officer = Depends(get_main_admin)):
    regions = db.query(Region).all()
    return regions

@router.post("/", response_model=RegionResponse)
def create_region(region: RegionCreate, db: Session = Depends(get_db), admin: Officer = Depends(get_main_admin)):
    existing = db.query(Region).filter((Region.name == region.name) | (Region.code == region.code)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Region with this name or code already exists")
    
    db_region = Region(name=region.name, code=region.code)
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region
