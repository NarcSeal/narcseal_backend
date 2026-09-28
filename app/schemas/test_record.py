from pydantic import BaseModel
from datetime import datetime

class TestRecordSchema(BaseModel):
    record_id: str
    officer_badge_id: str
    officer_name: str
    timestamp: datetime
    latitude: float
    longitude: float
    address: str
    test_result: str
    substance: str
    confidence: float
    image_hash: str
    previous_hash: str
    record_hash: str
    device_id: str
    station_code: str
    district: str
    state: str
    test_kit_type: str | None = None
    sample_id: str | None = None
    sample_type: str | None = None
    is_sealed: bool = True
    notes: str | None = None
