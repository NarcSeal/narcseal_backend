from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.database import get_db
from app.models.officer import Officer, OfficerRole
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_officer(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    officer = db.query(Officer).filter(Officer.username == username).first()
    if officer is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not officer.is_active:
        raise HTTPException(status_code=401, detail="Inactive user account")
        
    return officer

def get_regional_admin(current_officer: Officer = Depends(get_current_officer)):
    if current_officer.role not in [OfficerRole.REGIONAL_ADMIN, OfficerRole.MAIN_ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to perform Regional Admin actions")
    return current_officer

def get_main_admin(current_officer: Officer = Depends(get_current_officer)):
    if current_officer.role != OfficerRole.MAIN_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized. Main Admin access required.")
    return current_officer
