from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from graph_engine import LegalGraphBuilder
from omni_parser import DocumentIngester

ingester: DocumentIngester | None = None
graph_builder: LegalGraphBuilder | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ingester, graph_builder
    ingester = DocumentIngester()
    graph_builder = LegalGraphBuilder()
    yield


app = FastAPI(
    title="Momotopsy",
    description="AI-powered predatory clause detection using NLP embeddings & Graph Theory.",
    version="0.1.0",
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

    graph_data: dict[str, Any] = graph_builder.build_graph(clauses)

    return {
        "filename": file.filename,
        "total_clauses": len(clauses),
        "graph": graph_data,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
