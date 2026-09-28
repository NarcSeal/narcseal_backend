import sys
import os
from datetime import datetime, timedelta
import random
import uuid

# Setup path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models.officer import Officer, OfficerRole, OfficerRank
from app.models.region import Region
from app.models.test_record import TestRecord
from app.services.auth_service import get_password_hash

def seed_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create Regions
    hq_region = Region(name="HQ", code="HQ")
    mh_region = Region(name="Maharashtra Region", code="MH")
    gj_region = Region(name="Gujarat Region", code="GJ")
    db.add_all([hq_region, mh_region, gj_region])
    db.commit()

    # 1. Create a global NCB Admin to view the entire dashboard
    admin = db.query(Officer).filter(Officer.username == "admin").first()
    if not admin:
        admin = Officer(
            badge_id="NCB-HQ-001",
            full_name="Aakanksha Sharma (Admin)",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            rank=OfficerRank.SP,
            station_code="NCB-HQ",
            district="HQ",
            state="Delhi",
            role=OfficerRole.MAIN_ADMIN,
            region_id=hq_region.id
        )
        db.add(admin)

    # Helper to generate tests
    def create_tests(badge_id, name, station, district, state, pos, neg, inc):
        # Center coordinates
        if state == "Maharashtra":
            base_lat, base_lng = 19.0760, 72.8777 # Mumbai
        else:
            base_lat, base_lng = 23.0225, 72.5714 # Ahmedabad
            
        substances = ["Heroin", "Cocaine", "Methamphetamine", "Cannabis"]
        
        tests = []
        for i in range(pos):
            tests.append(("POSITIVE", random.choice(substances)))
        for i in range(neg):
            tests.append(("NEGATIVE", "Unknown (Cleared)"))
        for i in range(inc):
            tests.append(("INCONCLUSIVE", "Unknown (Pending Lab)"))
            
        for result, substance in tests:
            rec = TestRecord(
                record_id=f"REC-{str(uuid.uuid4())[:8].upper()}",
                officer_badge_id=badge_id,
                officer_name=name,
                timestamp=datetime.now() - timedelta(hours=random.randint(1, 48)),
                latitude=base_lat + random.uniform(-0.1, 0.1),
                longitude=base_lng + random.uniform(-0.1, 0.1),
                address=f"Checkpoint {random.randint(1, 10)}, {district}",
                test_result=result,
                substance=substance,
                confidence=random.uniform(90.0, 99.9) if result == "POSITIVE" else 99.9,
                image_hash=str(uuid.uuid4()),
                previous_hash=str(uuid.uuid4()),
                record_hash=str(uuid.uuid4()),
                device_id=f"DEV-{badge_id}",
                station_code=station,
                district=district,
                state=state,
                is_sealed=True,
                notes="Generated for demo"
            )
            db.add(rec)

    # 2. Create 5 Mumbai Officers
    for i in range(1, 6):
        badge = f"MH-OFF-{i:03d}"
        if not db.query(Officer).filter(Officer.badge_id == badge).first():
            off = Officer(
                badge_id=badge,
                full_name=f"Mumbai Officer {i}",
                username=f"mum.off.{i}",
                hashed_password=get_password_hash("password123"),
                rank=OfficerRank.INSPECTOR,
                station_code="MUM-REG-01",
                district="Mumbai",
                state="Maharashtra",
                role=OfficerRole.OFFICER,
                region_id=mh_region.id
            )
            db.add(off)
            # 2 positive, 3 negative, 1 inconclusive
            create_tests(badge, off.full_name, off.station_code, off.district, off.state, 2, 3, 1)

    # 3. Create 5 Gujarat Officers
    for i in range(1, 6):
        badge = f"GJ-OFF-{i:03d}"
        if not db.query(Officer).filter(Officer.badge_id == badge).first():
            off = Officer(
                badge_id=badge,
                full_name=f"Gujarat Officer {i}",
                username=f"guj.off.{i}",
                hashed_password=get_password_hash("password123"),
                rank=OfficerRank.INSPECTOR,
                station_code="GUJ-REG-01",
                district="Ahmedabad",
                state="Gujarat",
                role=OfficerRole.OFFICER,
                region_id=gj_region.id
            )
            db.add(off)
            # 1 positive, 1 negative, 2 inconclusive
            create_tests(badge, off.full_name, off.station_code, off.district, off.state, 1, 1, 2)

    # 4. Create Regional Admins
    mh_admin = Officer(
        badge_id="MH-ADMIN-01",
        full_name="Rajesh Patel (MH Admin)",
        username="mh_admin",
        hashed_password=get_password_hash("admin123"),
        rank=OfficerRank.DSP,
        station_code="MUM-HQ",
        district="Mumbai",
        state="Maharashtra",
        role=OfficerRole.REGIONAL_ADMIN,
        region_id=mh_region.id
    )
    gj_admin = Officer(
        badge_id="GJ-ADMIN-01",
        full_name="Sanjay Desai (GJ Admin)",
        username="gj_admin",
        hashed_password=get_password_hash("admin123"),
        rank=OfficerRank.DSP,
        station_code="AHM-HQ",
        district="Ahmedabad",
        state="Gujarat",
        role=OfficerRole.REGIONAL_ADMIN,
        region_id=gj_region.id
    )
    db.add_all([mh_admin, gj_admin])

    db.commit()
    db.close()
    print("Database seeded with Mumbai and Gujarat officers and tests!")

if __name__ == "__main__":
    seed_data()
