import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./radar.db"

# connect_args for sqlite to allow multiple threads handling requests
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class FlaggedRisk(Base):
    __tablename__ = "flagged_risks"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(String, index=True)
    issue_category = Column(String, index=True)
    severity_score = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))

class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True)
    event_type = Column(String)  # e.g., "Auto-Renewal", "KYC", "Internship End"
    deadline_date = Column(DateTime, index=True)
    description = Column(String)
    is_alert_sent = Column(Integer, default=0) # Use 0/1 for SQLite boolean compat

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
