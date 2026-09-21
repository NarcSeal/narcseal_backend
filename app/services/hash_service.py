import hashlib
from app.schemas.test_record import TestRecordSchema

def compute_record_hash(record: TestRecordSchema) -> str:
    """
    Recomputes the Merkle chain hash to verify integrity.
    Matches the logic defined in Fragment 6.2 of the Implementation Plan.
    """
    # Simulate the timestamp conversion - needs to match mobile exactly
    # In practice, usually best to use a strict string representation ISO8601
    timestamp_str = record.timestamp.isoformat()
    
    # Match the dataString concatenation logic from mobile
    data_string = (
        f"{record.officer_badge_id}"
        f"{timestamp_str}"
        f"{record.latitude}"
        f"{record.longitude}"
        f"{record.test_result}"
        f"{record.substance}"
        f"{record.confidence}"
        f"{record.image_hash}"
        f"{record.previous_hash}"
    )
    
    # Compute SHA256
    return hashlib.sha256(data_string.encode('utf-8')).hexdigest()
