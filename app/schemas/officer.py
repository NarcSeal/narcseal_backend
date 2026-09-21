from pydantic import BaseModel

class OfficerLogin(BaseModel):
    username: str
    password: str

class OfficerRegister(BaseModel):
    badge_id: str
    full_name: str
    username: str
    password: str
    rank: str
    station_code: str
    district: str
    state: str
