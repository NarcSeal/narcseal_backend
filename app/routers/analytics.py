from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.officer import Officer, OfficerRole
from app.models.test_record import TestRecord
from app.dependencies import get_current_officer

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def get_role_based_query(current_officer: Officer, db: Session, *columns):
    query = db.query(*columns) if columns else db.query(TestRecord)
    
    if current_officer.role == OfficerRole.OFFICER:
        query = query.filter(TestRecord.officer_badge_id == current_officer.badge_id)
    elif current_officer.role == OfficerRole.REGIONAL_ADMIN:
        # Join with officer to check region
        query = query.join(Officer, TestRecord.officer_badge_id == Officer.badge_id)\
                     .filter(Officer.region_id == current_officer.region_id)
    elif current_officer.role == OfficerRole.MAIN_ADMIN:
        pass # Can see everything
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
    if current_officer.role == OfficerRole.REGIONAL_ADMIN:
        active_officers_query = active_officers_query.filter(Officer.region_id == current_officer.region_id)
    elif current_officer.role == OfficerRole.OFFICER:
        active_officers_query = active_officers_query.filter(Officer.badge_id == current_officer.badge_id)
        
    active_officers = active_officers_query.count()
    
    # Calculate yesterday's tests for trend
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    total_tests_yesterday = get_role_based_query(current_officer, db).filter(func.date(TestRecord.timestamp) == yesterday).count()
    
    if total_tests_yesterday > 0:
        change = ((total_tests_today - total_tests_yesterday) / total_tests_yesterday) * 100
        tests_change_pct = f"{'+' if change > 0 else ''}{change:.1f}%"
    else:
        tests_change_pct = "+0.0%" if total_tests_today == 0 else "+100.0%"
        
    # Calculate positivity rate
    total_tests_overall = get_role_based_query(current_officer, db).count()
    if total_tests_overall > 0:
        pos_ratio = (positive_results / total_tests_overall) * 100
        positive_ratio_pct = f"{pos_ratio:.1f}%"
    else:
        positive_ratio_pct = "0.0%"

    return {
        "total_tests_today": total_tests_today,
        "positive_results": positive_results,
        "active_officers": active_officers,
        "pending_syncs": 0,
        "tests_change_pct": tests_change_pct,
        "positive_ratio_pct": positive_ratio_pct
    }

@router.get("/heatmap")
def get_heatmap_data(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """Returns GPS coordinates of all tests for the heatmap"""
    query = get_role_based_query(current_officer, db)
    records = query.all()
    return [{
        "id": r.id,
        "lat": r.latitude,
        "lng": r.longitude,
        "result": r.test_result,
        "substance": r.substance,
        "location": r.station_code,
        "weight_g": 0,
        "officer": r.officer_badge_id,
        "timestamp": str(r.timestamp),
        "confidence": r.confidence
    } for r in records if r.latitude is not None and r.longitude is not None]

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
    from datetime import datetime, timedelta
    date_func = func.date(TestRecord.timestamp)
    
    # Let's get the last 30 days
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    
    query = get_role_based_query(current_officer, db).filter(date_func >= thirty_days_ago)
    records = query.all()
    
    # Aggregate in Python for simpler logic of positive/negative grouping
    daily_stats = {}
    for r in records:
        d = r.timestamp.date()
        date_str = d.strftime("%b %d")
        if date_str not in daily_stats:
            daily_stats[date_str] = {"date": date_str, "total": 0, "positive": 0, "negative": 0}
        
        daily_stats[date_str]["total"] += 1
        if r.test_result == "POSITIVE":
            daily_stats[date_str]["positive"] += 1
        else:
            daily_stats[date_str]["negative"] += 1
            
    # Sort by actual date
    sorted_stats = sorted(daily_stats.values(), key=lambda x: datetime.strptime(x["date"], "%b %d"))
    
    return sorted_stats

@router.get("/alerts")
def get_trend_alerts(current_officer: Officer = Depends(get_current_officer), db: Session = Depends(get_db)):
    """
    EXTRA 2: Substance Trend Alerts
    Detects sudden spikes in positive tests for specific substances in particular districts.
    """
    from datetime import datetime, timedelta
    
    # We only alert Main Admins or Regional Admins about trends
    if current_officer.role not in [OfficerRole.MAIN_ADMIN, OfficerRole.REGIONAL_ADMIN]:
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
