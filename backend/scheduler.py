import os
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from database import SessionLocal, LifecycleEvent
from notifier import send_smart_reminder

load_dotenv()

scheduler = AsyncIOScheduler()

def check_upcoming_deadlines():
    """Polled by APScheduler to find impending contract deadlines."""
    demo_mode = os.environ.get("DEMO_MODE", "False").lower() == "true"
    db = SessionLocal()
    
    try:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        thirty_days_ahead = now + datetime.timedelta(days=30)
        
        # Look forward for events approaching in a safe timeframe
        query = db.query(LifecycleEvent).filter(
            LifecycleEvent.deadline_date <= thirty_days_ahead,
            LifecycleEvent.deadline_date >= now
        )
        
        if not demo_mode:
            query = query.filter(LifecycleEvent.is_alert_sent == 0)
            
        events = query.all()
        
        for event in events:
            # Calculate integer days remaining
            delta = event.deadline_date - now
            days_left = max(0, delta.days)
            
            # Fire the notification
            send_smart_reminder(event.event_type, event.description, days_left)
            
            # Persist sent state to avoid spam (unless in DEMO MODE)
            if not demo_mode:
                event.is_alert_sent = 1
                
        if events and not demo_mode:
            db.commit()

    except Exception as e:
        print(f"Scheduler failed to read database: {e}")
    finally:
        db.close()

def start_scheduler():
    """Hooks into the main FastAPI lifespan cycle."""
    demo_mode = os.environ.get("DEMO_MODE", "False").lower() == "true"
    
    if demo_mode:
        print("\n\n[WARNING]: MULTIPLIER ACTIVE! (DEMO_MODE=True)")
        print("SCHEDULER FIRING EVERY 30 SECONDS... IGNORING ALL SENT FLAGS.\n")
        # Blast repeated notifications for live tech demos
        scheduler.add_job(check_upcoming_deadlines, IntervalTrigger(days=2), id="lifecycle_job", replace_existing=True)
    else:
        # Standard maintenance sweep (set to 4 days as requested)
        scheduler.add_job(check_upcoming_deadlines, IntervalTrigger(days=4), id="lifecycle_job", replace_existing=True)

    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
