from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer
from app.models.test_record import TestRecord
from app.schemas.test_record import TestRecordSchema
from app.services.hash_service import compute_record_hash
from app.services.auth_service import decode_token
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

router = APIRouter(prefix="/sync", tags=["Sync"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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
    return officer

@router.post("/upload")
def receive_synced_record(record: TestRecordSchema, current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    # Step 1: Verify the record belongs to this officer
    if record.officer_badge_id != current_officer.badge_id:
        raise HTTPException(status_code=403, detail="Record does not belong to this officer")

    # Step 2: Verify the Merkle Chain integrity
    recomputed_hash = compute_record_hash(record)
    if recomputed_hash != record.record_hash:
        # TAMPER DETECTED
        raise HTTPException(
            status_code=400, 
            detail="INTEGRITY CHECK FAILED: Record hash mismatch. Possible tampering detected."
        )

    # Step 3: Verify chain continuity
    if record.previous_hash != "GENESIS":
        previous_record = db.query(TestRecord).filter(TestRecord.record_hash == record.previous_hash).first()
        if not previous_record:
            raise HTTPException(
                status_code=400, 
                detail="CHAIN BREAK: Previous record not found. Possible record deletion detected."
            )

    # Check if record already exists (idempotent sync)
    existing = db.query(TestRecord).filter(TestRecord.record_id == record.record_id).first()
    if existing:
        return {"message": "Record already synced"}

    # Step 4: Save to PostgreSQL
    db_record = TestRecord(**record.model_dump())
    db.add(db_record)
    db.commit()

    return {"message": "Record synced and verified successfully"}
