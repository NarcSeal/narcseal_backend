from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.officer import Officer, OfficerRole
from app.models.test_record import TestRecord
from app.routers.test_records import get_current_officer

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def get_role_based_query(current_officer: Officer, db: Session, *columns):
    query = db.query(*columns) if columns else db.query(TestRecord)
    if current_officer.role == OfficerRole.FIELD_OFFICER:
        query = query.filter(TestRecord.officer_badge_id == current_officer.badge_id)
    elif current_officer.role == OfficerRole.STATION_HEAD:
        query = query.filter(TestRecord.station_code == current_officer.station_code)
    elif current_officer.role == OfficerRole.DISTRICT_ADMIN:
        query = query.filter(TestRecord.district == current_officer.district)
    return query

@router.get("/stats")
def get_stats(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns top-level KPIs for the dashboard"""
    from datetime import datetime
    today = datetime.now().date()
    
    # 1. Total tests today
    total_tests_today = get_role_based_query(current_officer, db).filter(func.date(TestRecord.timestamp) == today).count()
    
    # 2. Positive results today (or overall if preferred, let's do overall for the stat or today)
    # The frontend mock shows overall or today. Let's do overall for now.
    positive_results = get_role_based_query(current_officer, db).filter(TestRecord.test_result == "POSITIVE").count()
    
    # 3. Active officers
    active_officers_query = db.query(Officer).filter(Officer.is_active == True)
    if current_officer.role == OfficerRole.STATION_HEAD:
        active_officers_query = active_officers_query.filter(Officer.station_code == current_officer.station_code)
    elif current_officer.role == OfficerRole.DISTRICT_ADMIN:
        active_officers_query = active_officers_query.filter(Officer.district == current_officer.district)
    # Field officers only see themselves
    elif current_officer.role == OfficerRole.FIELD_OFFICER:
        active_officers_query = active_officers_query.filter(Officer.badge_id == current_officer.badge_id)
        
    active_officers = active_officers_query.count()
    
    return {
        "total_tests_today": total_tests_today,
        "positive_results": positive_results,
        "active_officers": active_officers,
        "pending_syncs": 0, # Since we use immediate sync, this is 0
        "tests_change_pct": "+5%", # Mock value
        "positive_ratio_pct": "15%" # Mock value
    }

@router.get("/heatmap")
def get_heatmap_data(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns GPS coordinates of all tests for the heatmap"""
    query = get_role_based_query(
        current_officer, 
        db, 
        TestRecord.latitude, 
        TestRecord.longitude, 
        TestRecord.test_result, 
        TestRecord.substance
    )
    records = query.all()
    return [{"lat": r.latitude, "lng": r.longitude, "result": r.test_result, "substance": r.substance} for r in records]

@router.get("/substance-breakdown")
def get_substance_breakdown(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns count of each substance detected for pie chart"""
    query = get_role_based_query(
        current_officer, 
        db, 
        TestRecord.substance, 
        func.count(TestRecord.id).label('count')
    )
    # Only count positive/inconclusive results with an actual substance
    query = query.filter(TestRecord.substance.isnot(None), TestRecord.substance != "None", TestRecord.substance != "")
    results = query.group_by(TestRecord.substance).all()
    
    return [{"substance": r.substance, "count": r.count} for r in results]

@router.get("/daily-tests")
def get_daily_test_count(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns test count per day for the timeline chart"""
    # Grouping by date (ignoring time)
    date_func = func.date(TestRecord.timestamp)
    query = get_role_based_query(
        current_officer, 
        db, 
        date_func.label('date'), 
        func.count(TestRecord.id).label('count')
    )
    results = query.group_by('date').order_by('date').all()
    
    # Format the date properly for JSON response
    return [{"date": str(r.date), "count": r.count} for r in results]

@router.get("/alerts")
def get_trend_alerts(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """
    EXTRA 2: Substance Trend Alerts
    Detects sudden spikes in positive tests for specific substances in particular districts.
    """
    from datetime import datetime, timedelta
    
    # We only alert NCB Admins or District Admins about trends
    if current_officer.role not in [OfficerRole.NCB_ADMIN, OfficerRole.DISTRICT_ADMIN]:
        return []

    alerts = []
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    
    # Fetch recent records (last 7 days)
    recent_query = get_role_based_query(
        current_officer, db, 
        TestRecord.substance, TestRecord.district, func.count(TestRecord.id).label('count')
    ).filter(TestRecord.timestamp >= seven_days_ago, TestRecord.test_result == "POSITIVE")
    
    recent_stats = recent_query.group_by(TestRecord.district, TestRecord.substance).all()
    
    # In a real scenario, you'd compare this to a 30-day moving average.
    # For the hackathon, we simulate an alert if any district has > 10 positives of a specific substance in a week.
    for stat in recent_stats:
        if stat.count >= 10:
            alerts.append(f"ALERT: Unusual {stat.substance} activity detected in {stat.district} district ({stat.count} positive cases in the last 7 days).")
            
    # Mock alert for demonstration if no actual spikes
    if not alerts:
         alerts.append(f"ALERT: Simulated spike - Unusual Cocaine activity detected in Mumbai-West district (14 positive cases in the last 7 days).")
         
    return {"alerts": alerts}
