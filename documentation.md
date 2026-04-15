# Momotopsy — Backend Documentation

ts is a prototype backend — still iterating, but here's the documentation for the current code.

---

## omni_parser.py — Omni-Parser for Legal Document Ingestion

This module is lowkey the backbone of the whole pipeline — it handles PDF, DOCX, and image files, returning a clean list of clause strings.

### Module-Level Constants

| Constant | Description |
|---|---|
| `_PDF` | MIME type for PDF files (`application/pdf`) |
| `_DOCX` | MIME type for DOCX files (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`) |
| `_IMAGE_TYPES` | Set of supported image MIME types (`image/png`, `image/jpeg`) |
| `_ocr_reader` | Lazy-loaded singleton EasyOCR reader — heavy initialization, so only created once |

### `_get_ocr_reader() -> easyocr.Reader`

Returns a singleton EasyOCR reader (English). Lazily initialized on first call cuz we don't wanna tank startup time unless OCR is actually needed.

### `_normalize(text: str) -> str`

Applies text normalization pipeline:
1. Normalize unicode form (NFKC).
2. Remove zero-width / control characters (keeps newlines & spaces).
3. Collapse whitespace into single spaces and strip leading/trailing whitespace.

### Class: `DocumentIngester`

Parses raw file bytes into a list of cleaned clause strings. ts basically eats any document format and spits out clean text.

#### `ingest(data: bytes, mime_type: str) -> list[str]`

Accept raw file bytes and MIME type, return list of clause strings.

- **Args:**
  - `data` — Raw file byte stream.
  - `mime_type` — MIME type of the uploaded file.
- **Returns:** List of normalized text strings, one per logical clause/block.
- **Raises:** `ValueError` if the MIME type is unsupported.

#### `_extract_pdf(data: bytes) -> list[str]`

Extract text blocks from a PDF using PyMuPDF. Iterates page-by-page, using `get_text("blocks")` which returns tuples of `(x0, y0, x1, y1, text, ...)`.

#### `_extract_docx(data: bytes) -> list[str]`

Extract paragraphs from a DOCX file using `python-docx`.

#### `_extract_image(data: bytes) -> list[str]`

Run EasyOCR on an image and return detected text blocks. Uses `detail=0` to get plain string results.

---

## graph_engine.py — Graph Engine for Legal Clause Analysis

Builds a similarity graph from clause embeddings and assigns mock risk scores. ts is where the math works basically.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_MODEL_NAME` | `"all-MiniLM-L6-v2"` | SentenceTransformers model used for embeddings |
| `_SIMILARITY_THRESHOLD` | `0.65` | Minimum cosine similarity to draw an edge between clauses |

### Class: `LegalGraphBuilder`

Builds a NetworkX graph of clause relationships using NLP embeddings. Lowkey the main character of the analysis pipeline.

#### `__init__()`

Loads the SentenceTransformers model into memory.

#### `build_graph(clauses: list[str]) -> dict[str, Any]`

Constructs a clause-similarity graph and returns it as a JSON-ready dict.

**Pipeline:**
1. Encode clauses into dense vectors.
2. Create a node per clause.
3. Add edges where `cosine_similarity > threshold`.
4. Assign deterministic mock risk scores.

- **Args:**
  - `clauses` — List of clause text strings.
- **Returns:** JSON-serializable dict produced by `nx.node_link_data()`.

#### `_mock_risk_score(clause: str) -> float`

Generates a deterministic pseudo-random risk score in `[0, 1]`. Uses a SHA-256 content hash so the same clause always receives the same score — reproducible across runs cuz naur we do not want RNG shi.

---

## main.py — FastAPI Application

Exposes the `/analyze` endpoint that ingests a legal document, builds a clause-similarity graph, and returns it as JSON. One endpoint, zero friction.

### Application Lifecycle

- **Startup (lifespan):** Instantiates `DocumentIngester` and `LegalGraphBuilder` as module-level singletons. The graph builder loads the ML model into memory at this stage.
- **CORS Middleware:** Configured with `allow_origins=["*"]` so the React/D3.js frontend can connect without issues.

### `POST /analyze`

Analyze an uploaded legal document. Accepts PDF, DOCX, PNG, or JPEG.

**Flow:**
1. Validate MIME type against `DocumentIngester.SUPPORTED_MIMES` -> `415` if unsupported.
2. Read file bytes -> `400` if empty.
3. Parse via `DocumentIngester.ingest()` -> `422` if parsing fails or no text extracted.
4. Build graph via `LegalGraphBuilder.build_graph()`.
5. Return JSON with `filename`, `total_clauses`, and `graph` (node-link format).

- **Args:**
  - `file` — The uploaded document (`UploadFile`).
- **Returns:** JSON-serializable graph dict (node-link format).

### Entrypoint

When run directly (`python main.py`), starts Uvicorn on `0.0.0.0:8000` with hot-reload enabled.

---

## train_model.py — Momotopsy Risk Model Trainer

Trains a RandomForest classifier on legal clause embeddings to detect predatory contract language. Highkey the most important script in the repo.

### Data Sources

| Dataset | Source | Rows | Label Logic |
|---|---|---|---|
| `lex_glue/unfair_tos` | All splits (train+val+test) | ~9,414 | Predatory if `len(labels) > 0` |
| `nguha/legalbench` `unfair_tos` | Test split | ~3,813 | Predatory if `answer != "Other"` |

After deduplication: **~13,045 unique clauses**.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_MODEL_NAME` | `"all-MiniLM-L6-v2"` | SentenceTransformers model |
| `_EXPORT_PATH` | `"momotopsy_risk_model.pkl"` | Output path for the trained model |
| `_TEST_SIZE` | `0.20` | Test split ratio |
| `_RANDOM_STATE` | `42` | Random seed for reproducibility |

### `_load_lex_glue() -> pd.DataFrame`

Downloads all splits of `lex_glue/unfair_tos`, concatenates them, and creates the binary `is_predatory` column.

### `_load_legalbench() -> pd.DataFrame`

Downloads `nguha/legalbench` unfair_tos test split. Maps `answer` column to binary — anything that isn't "Other" is predatory.

### `main()`

End-to-end training pipeline:

1. **Data Ingestion** — Loads both datasets, combines into a single DataFrame, deduplicates on `text`.
2. **Semantic Embedding** — Loads `all-MiniLM-L6-v2`, encodes the `text` column into a 384-dim embedding matrix (`X`). `is_predatory` becomes the target `y`.
3. **SMOTE Oversampling** — Applies SMOTE on the training split to balance the classes (cuz the dataset is ~89% Safe / 11% Predatory).
4. **Model Training** — 80/20 stratified split. Trains `RandomForestClassifier(n_estimators=200, class_weight="balanced")`.
5. **Evaluation & Export** — Prints `accuracy_score` and `classification_report`. Exports model via `joblib.dump()`.

### Training Results (v4)

| Metric | Safe | Predatory |
|---|---|---|
| Precision | 0.96 | 0.94 |
| Recall | 1.00 | 0.62 |
| F1-Score | 0.98 | 0.75 |

**Overall accuracy: 95.6%** on 2,609 test samples.

---

## test_model.py — Model Validation Script

Validates the trained anomaly detector against a set of mock contract clauses. Lowkey just checks whether the model can tell apart chill contract language from straight-up predatory clauses.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_MODEL_PATH` | `"momotopsy_risk_model.pkl"` | Path to the trained model |
| `_ENCODER_NAME` | `"all-MiniLM-L6-v2"` | SentenceTransformers model for encoding test clauses |

### `MOCK_CLAUSES`

A curated list of 12 mock legal clauses — mix of safe (rent payments, arbitration, overtime) and unhinged predatory ones (asset seizure, rights waiver, IP grabs). Bruh if the model can't handle these, we have a problem.

### `main()`

1. **Load model** — Reads `momotopsy_risk_model.pkl` via joblib. Exits gracefully with a clear error if the file doesn't exist.
2. **Load encoder** — Initializes `all-MiniLM-L6-v2`.
3. **Encode & predict** — Embeds the mock clauses, runs `predict()` for binary labels and `predict_proba()` for confidence scores.
4. **Pretty print** — Outputs a formatted table with clause number, verdict (SAFE / PREDATORY), risk percentage, and clause text. Summary stats at the bottom.
