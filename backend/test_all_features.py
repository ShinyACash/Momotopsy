import asyncio
import httpx
import os
import datetime

async def test_negotiate():
    print("\n--- 1. Testing Counter-Strike Negotiation Kit ---")
    payload = {
        "node_id": "test_node_01",
        "original_text": "The company may unilaterally terminate this lease at any point and seize all assets.",
        "improved_text": "Either party may terminate this agreement with a 30-day written notice.",
        "document_type": "Commercial Lease"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post("http://localhost:8000/api/negotiate", json=payload)
            r.raise_for_status()
            print("[SUCCESS]: Negotiation payload generated!")
            resp = r.json()
            print(f"Subject: {resp.get('email_subject')}")
            print(f"Body: {resp.get('email_body')}\n")
        except Exception as e:
            print(f"[FAILED]: POST /api/negotiate error: {e}\n(Is the FastAPI server running?)")

async def test_trending():
    print("\n--- 2. Testing Scam Radar Trending ---")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("http://localhost:8000/api/trending-risks")
            r.raise_for_status()
            print("[SUCCESS]: Trending risks retrieved!")
            data = r.json().get("trending", [])
            for item in data:
                print(f" - {item['issue']}: {item['count']} hits")
            print()
        except Exception as e:
            print(f"[FAILED]: GET /api/trending-risks error: {e}")

async def inject_lifecycle_test():
    print("\n--- 3. Injecting Lifecycle Event for Notification Scheduler ---")
    try:
        from database import SessionLocal, LifecycleEvent
        db = SessionLocal()
        
        # Insert a deadline exactly 5 days from now
        future = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(days=5)
        test_event = LifecycleEvent(
            document_id="demonstration_contract.pdf",
            event_type="Server Stress Test",
            deadline_date=future,
            description="Testing the Smart Notifications background poller.",
            is_alert_sent=0
        )
        db.add(test_event)
        db.commit()
        db.close()
        print("[SUCCESS]: Injected lifecycle event into DB.")
        print("Look at the terminal running 'main.py'. You should see the [SMART REMINDER] blast if DEMO_MODE=True!")
    except Exception as e:
        print(f"[FAILED]: Failed injecting lifecycle event: {e}")

async def run_all():
    print("Testing the latest Momotopsy infrastructure additions...\n")
    await test_trending()
    await test_negotiate()
    await inject_lifecycle_test()

if __name__ == "__main__":
    asyncio.run(run_all())
