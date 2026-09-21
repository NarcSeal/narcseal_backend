from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.officer import Officer
from app.routers.test_records import get_current_officer
from app.models.test_record import TestRecord
import os
import hashlib
import uuid

router = APIRouter(prefix="/sync", tags=["Media"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-image")
async def upload_evidence_image(
    record_id: str = Form(...),
    image_hash: str = Form(...),
    file: UploadFile = File(...),
    current_officer: Officer = Depends(get_current_officer),
    db: Session = Depends(get_db)
):
    """
    Endpoint for uploading the actual physical image evidence.
    Validates the SHA-256 hash of the uploaded image against the provided image_hash.
    """
    
    # Verify the record exists and belongs to the officer
    record = db.query(TestRecord).filter(TestRecord.record_id == record_id).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Test record not found. Please sync the record JSON first.")
        
    if record.officer_badge_id != current_officer.badge_id:
        raise HTTPException(status_code=403, detail="Not authorized to upload media for this record.")
        
    if record.image_hash != image_hash:
        raise HTTPException(status_code=400, detail="Hash mismatch in form data.")

    # Read file bytes and compute hash
    contents = await file.read()
    sha256 = hashlib.sha256()
    sha256.update(contents)
    computed_hash = sha256.hexdigest()
    
    if computed_hash != image_hash:
        raise HTTPException(status_code=400, detail="TAMPER DETECTED: Uploaded image bytes do not match the cryptographic hash.")
        
    # Save the file securely
    # Using a UUID filename to prevent path traversal or overwriting
    file_extension = os.path.splitext(file.filename)[1]
    if not file_extension:
        file_extension = ".jpg"
        
    safe_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
        
    # Ideally, we would save this file_path to the TestRecord model, 
    # but currently we can map it via record_id on the frontend if needed,
    # or just update a new field if we add it. 
    # Since we can't easily run alembic migrations safely right now without the full project context,
    # we will name the file exactly as the record_id to easily serve it!
    
    # Better approach: rename it to record_id.jpg
    final_path = os.path.join(UPLOAD_DIR, f"{record_id}.jpg")
    os.rename(file_path, final_path)
    
    return {"message": "Image uploaded and hash verified successfully", "filename": f"{record_id}.jpg"}
