from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/kits", tags=["Test Kits"])

class TestKitResponse(BaseModel):
    id: str
    name: str
    wait_time_seconds: int

# Hardcoded realistic wait times based on chemical reactions
KITS = [
    TestKitResponse(id="marquis", name="Marquis (Ecstasy/Heroin)", wait_time_seconds=60),
    TestKitResponse(id="scott", name="Scott (Cocaine)", wait_time_seconds=30),
    TestKitResponse(id="mandelin", name="Mandelin (Ketamine/Amphetamines)", wait_time_seconds=45),
    TestKitResponse(id="mecke", name="Mecke (Opiates)", wait_time_seconds=60),
    TestKitResponse(id="ehrlich", name="Ehrlich (LSD/Indoles)", wait_time_seconds=120),
    TestKitResponse(id="other", name="Other", wait_time_seconds=60),
]

@router.get("/", response_model=List[TestKitResponse])
def get_test_kits():
    """
    Returns the list of supported reagent test kits and their required reaction wait times.
    """
    return KITS
