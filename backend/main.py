from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
import datetime

from database import init_db, get_db, FlaggedRisk, LifecycleEvent
from graph_engine import LegalGraphBuilder
from omni_parser import DocumentIngester
from scheduler import start_scheduler, stop_scheduler

ingester: DocumentIngester | None = None
graph_builder: LegalGraphBuilder | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ingester, graph_builder
    init_db()  # Initialize the SQLite tables
    ingester = DocumentIngester()
    graph_builder = LegalGraphBuilder()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Momotopsy",
    description="AI-powered predatory clause detection using NLP embeddings & Graph Theory.",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze", response_model=None)
async def analyze_contract(file: UploadFile = File(...)) -> dict[str, Any]:
    assert ingester is not None and graph_builder is not None

    mime = file.content_type or ""
    if mime not in DocumentIngester.SUPPORTED_MIMES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type: {mime!r}. "
                f"Accepted: {sorted(DocumentIngester.SUPPORTED_MIMES)}"
            ),
        )

    data: bytes = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        clauses: list[str] = ingester.ingest(data, mime)
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Failed to parse document: {exc}"
        ) from exc

    if not clauses:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the uploaded file.",
        )

    graph_data: dict[str, Any] = await graph_builder.build_graph(clauses)

    # ---------------------------------------------------------
    # SCAM RADAR: Quietly log predatory issues to the database
    # ---------------------------------------------------------
    try:
        db = next(get_db())
        radar_records = []
        for node in graph_data.get("nodes", []):
            if node["label"] == "Predatory" and node.get("key_issues"):
                # Use key_issues string or flatten if array. Often it's a list from LLM.
                issues = node["key_issues"]
                if isinstance(issues, list):
                    issues = issues[0] if issues else "Uncategorized Risk"
                radar_records.append(FlaggedRisk(
                    document_type="Uncategorized Contract",  # To be dynamically updated from frontend later
                    issue_category=str(issues),
                    severity_score=node.get("risk_score", 0.8),
                    timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                ))
        if radar_records:
            db.bulk_save_objects(radar_records)
            db.commit()
    except Exception as e:
        print(f"Scam Radar logging failed: {e}")
        # non-fatal, continue returning response
    
    # ---------------------------------------------------------
    # SMART REMINDERS: Extract explicit dates and save
    # ---------------------------------------------------------
    try:
        raw_text = " ".join(clauses)
        events = await graph_builder.fixer.extract_lifecycle_events(raw_text)
        lifecycle_records = []
        for e in events:
            try:
                date_obj = datetime.datetime.strptime(e.get("date_str", ""), "%Y-%m-%d")
                lifecycle_records.append(
                    LifecycleEvent(
                        document_id=file.filename,
                        event_type=e.get("event_type", "Deadline"),
                        deadline_date=date_obj,
                        description=e.get("description", ""),
                        is_alert_sent=0,
                        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) # Added timestamp for sanity
                    )
                )
            except ValueError:
                pass # Unparseable date
                
        if lifecycle_records:
            db = next(get_db())
            db.bulk_save_objects(lifecycle_records)
            db.commit()
    except Exception as e:
        print(f"Lifecycle Event extraction failed: {e}")

    return {
        "filename": file.filename,
        "total_clauses": len(clauses),
        "document_risk_score": graph_data.get("graph", {}).get("document_risk_score", 0.0),
        "lifecycle_events": [
            {
                "event_type": e.event_type,
                "deadline_date": e.deadline_date.strftime("%Y-%m-%d"),
                "description": e.description
            } for e in lifecycle_records
        ],
        "graph": graph_data,
    }

class NegotiateRequest(BaseModel):
    node_id: str
    original_text: str
    improved_text: str
    document_type: str

@app.post("/api/negotiate")
async def negotiate_clause(payload: NegotiateRequest) -> dict:
    """Generate a Counter-Strike negotiation payload."""
    assert graph_builder is not None
    if not payload.improved_text or payload.improved_text == "None":
        raise HTTPException(status_code=400, detail="Cannot negotiate without an improved clause provided.")
    
    result = await graph_builder.fixer.generate_negotiation_doc(
        payload.original_text, 
        payload.improved_text, 
        payload.document_type
    )
    return result

@app.get("/api/trending-risks")
def get_trending_risks(db: Session = Depends(get_db)):
    """Return top 5 most frequently flagged risks of the last 30 days for Radar."""
    thirty_days_ago = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=30)
    
    results = (
        db.query(FlaggedRisk.issue_category, func.count(FlaggedRisk.id).label("count"))
        .filter(FlaggedRisk.timestamp >= thirty_days_ago)
        .group_by(FlaggedRisk.issue_category)
        .order_by(func.count(FlaggedRisk.id).desc())
        .limit(5)
        .all()
    )
    
    trending = [{"issue": row[0], "count": row[1]} for row in results]
    return {"trending": trending}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
