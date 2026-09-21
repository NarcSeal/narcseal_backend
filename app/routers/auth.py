from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer
from app.services.auth_service import verify_password, create_access_token, get_password_hash
from app.schemas.officer import OfficerLogin, OfficerRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(credentials: OfficerLogin, db: Session = Depends(get_db)):
    officer = db.query(Officer).filter(Officer.username == credentials.username).first()
    if not officer or not verify_password(credentials.password, officer.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    if not officer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your supervisor."
        )

    token = create_access_token(data={
        "sub": officer.username,
        "badge_id": officer.badge_id,
        "role": officer.role.value,
        "station_code": officer.station_code,
        "district": officer.district,
        "state": officer.state,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "officer_name": officer.full_name,
        "badge_id": officer.badge_id,
        "role": officer.role.value
    }

@router.post("/register")
def register_officer(
    officer_data: OfficerRegister,
    db: Session = Depends(get_db)
):
    existing = db.query(Officer).filter(
        (Officer.badge_id == officer_data.badge_id) | (Officer.username == officer_data.username)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Officer already registered")

    new_officer = Officer(
        badge_id=officer_data.badge_id,
        full_name=officer_data.full_name,
        username=officer_data.username,
        hashed_password=get_password_hash(officer_data.password),
        rank=officer_data.rank,
        station_code=officer_data.station_code,
        district=officer_data.district,
        state=officer_data.state
    )
    db.add(new_officer)
    db.commit()
    return {"message": f"Officer {officer_data.full_name} registered successfully"}
