import datetime
import random
from database import SessionLocal, init_db, FlaggedRisk

def seed_data():
    # Ensure table exists
    init_db()
    
    doc_types = ["Commercial Lease", "Residential Lease", "Employment Contract", "NDA", "Terms of Service", "SaaS Agreement"]
    issue_categories = [
        "Unilateral Termination Right",
        "Exorbitant Late Fee structure",
        "Automatic Uncapped Rent Increase",
        "Overbroad Non-Compete",
        "Forced Arbitration Clause",
        "Perpetual Data Privacy Surrender",
        "Asymmetric Indemnification",
        "Vague Performance/Default Metrics"
    ]

    db = SessionLocal()
    try:
        # Clear existing data for fresh seed
        db.query(FlaggedRisk).delete()

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        records = []
        
        for _ in range(100):
            # Scatter records over the last 30 days
            days_ago = random.randint(0, 30)
            timestamp = now - datetime.timedelta(days=days_ago)
            
            # 80% chance of getting a very high severity issue for dramatic effect
            severity = round(random.uniform(0.65, 0.99), 2)
            
            records.append(
                FlaggedRisk(
                    document_type=random.choice(doc_types),
                    issue_category=random.choice(issue_categories),
                    severity_score=severity,
                    timestamp=timestamp
                )
            )
            
        db.bulk_save_objects(records)
        db.commit()
        print("Scam Radar DB Seeded! Injected 100 dummy records.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
