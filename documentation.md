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

## llm_fixer.py — LLM-Powered Clause Analyzer

Async service that sends predatory clauses to a Llama-3.3-70b model (via Groq) and returns structured analysis. ts is the brain that explains WHY a clause is predatory and rewrites it.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_LLM_MODEL` | `"llama-3.3-70b-versatile"` | Groq-hosted Llama-3 model |
| `_SYSTEM_PROMPT` | *(see source)* | Instructs the LLM to return strict JSON with `reason_flagged`, `key_issues`, `improved_clause` |

### `ClauseAnalysis` (Pydantic Model)

Strict response schema enforced via Pydantic validation:

| Field | Type | Description |
|---|---|---|
| `reason_flagged` | `str` | One-sentence explanation of why the clause is predatory |
| `key_issues` | `list[str]` | 2-5 concise bullet points identifying specific legal issues |
| `improved_clause` | `str` | Complete rewritten clause that is legally fair |

### Class: `ClauseFixer`

#### `__init__(model: str = _LLM_MODEL)`

Creates an `AsyncGroq` client. Reads `GROQ_API_KEY` from environment variables.

#### `async analyze_clause(text: str) -> dict[str, Any]`

Sends a predatory clause to the LLM with JSON mode enforced (`response_format={"type": "json_object"}`). Validates the response with `ClauseAnalysis` Pydantic model. On any failure (network, parsing, LLM error), returns empty default fields instead of raising — graceful degradation frfr.

---

## graph_engine.py — Graph Engine for Legal Clause Analysis

Builds a similarity graph from clause embeddings, assigns risk scores using the trained classifier, and triggers LLM analysis for predatory clauses. ts is where the math AND the AI work basically.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_MODEL_NAME` | `"all-mpnet-base-v2"` | SentenceTransformers model used for embeddings (768-dim) |
| `_CLF_PATH` | `"momotopsy_risk_model.pkl"` | Path to the trained classifier |
| `_SIMILARITY_THRESHOLD` | `0.65` | Minimum cosine similarity to draw an edge between clauses |
| `_RISK_THRESHOLD` | `0.15` | Minimum risk score to flag a clause as Predatory (Recall-boosted) |

### Class: `LegalGraphBuilder`

Builds a NetworkX graph of clause relationships using NLP embeddings, risk classification, and LLM-powered analysis. Lowkey the main character of the analysis pipeline.

#### `__init__()`

Loads the SentenceTransformers encoder, the trained classifier (`momotopsy_risk_model.pkl`), and creates a `ClauseFixer` instance.

#### `async build_graph(clauses: list[str]) -> dict[str, Any]`

Constructs a clause-similarity graph with LLM analysis and returns it as a JSON-ready dict.

**Pipeline:**
1. Encode clauses into 768-dim dense vectors using MPNet.
2. Predict risk scores using `clf.predict_proba()`.
3. Create a node per clause with `label` (Safe/Predatory based on `_RISK_THRESHOLD`).
4. For Safe nodes: set `reason_flagged=None`, `key_issues=[]`, `improved_clause=None`.
5. For Predatory nodes: fire all LLM calls in parallel via `asyncio.gather()`.
6. Append LLM results (`reason_flagged`, `key_issues`, `improved_clause`) to node attributes.
7. Add edges where `cosine_similarity > threshold`.

- **Args:**
  - `clauses` — List of clause text strings.
- **Returns:** JSON-serializable dict produced by `nx.node_link_data()`. Each node includes `text`, `risk_score`, `label`, `reason_flagged`, `key_issues`, and `improved_clause`.

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

### `POST /api/negotiate`

Accepts an original clause, an improved version, and document type. Returns a JSON email subject and body generated by LLM.

### `GET /api/trending-risks`

Fetches the top 5 most frequently occurring risk categories from the SQL database over the last 30 days.

---

## scheduler.py — Lifecycle Engine

A background service powered by `APScheduler` that manages time-sensitive contractual events.

### Features
- **Smart Reminders**: Extracts dates (Auto-renewal, Termination) using LLM and schedules notifications.
- **Demo Multiplier**: When `DEMO_MODE` is True, notifications fire at accelerated intervals for live presentations.

---

## database.py — SQL Persistence Layer

Manages the SQLite `radar.db` used for persistence across sessions.

### Tables
- **`flagged_risks`**: Stores every predatory clause detected, used for the Scam Radar.
- **`lifecycle_events`**: Stores extracted dates and reminders.

---

## Frontend Architecture — Modern Antique Hub

The frontend is a React.js (Vite) application focused on high-density data visualization and premium aesthetics.

### ◈ Design Philosophy: Modern Antique
The UI is built on a custom design system defined in `index.css` using CSS variables:
- **Palette**: Deep Parchment (`#d3c1a6`), Ink Ink (`#2d2b1f`), and Antique Gold/Bronze.
- **Glassmorphism**: Extensive use of `backdrop-filter` and semi-transparent layers to maintain a "forensic desk" feel.
- **Micro-Animations**: Custom keyframe animations (`fadeInUp`, `scanPaper`) for smooth transitions.

### ◈ Component Breakdown

#### `Analysis.jsx` (Core Dashboard)
The main hub of the application. Manages the dashboard state and handles:
- **Sidebar Navigation**: Controls the active view (Overview, Clauses, Negotiation, Radar).
- **State Orchestration**: Passes analysis data from the backend into sub-components.

#### `NegotiationKit.jsx`
- Allows users to interactively select clauses for negotiation.
- Interfaces with the `/api/negotiate` endpoint to display live-generated templates.

#### `ScamRadar.jsx`
- A visual leaderboard fetching "Trending Risks" from the backend.
- Provides contextual insights into global legal patterns.

#### `NotificationCenter.jsx`
- A retractable slide-out panel that displays real-time risk alerts and lifecycle reminders.

---

## train_model.py — Momotopsy Risk Model Trainer

Trains a HistGradientBoostingClassifier on legal clause embeddings...

### Data Sources

| Dataset | Source | Rows | Label Logic |
|---|---|---|---|
| `lex_glue/unfair_tos` | All splits (train+val+test) | ~9,414 | Predatory if `len(labels) > 0` |
| `nguha/legalbench` `unfair_tos` | Test split | ~3,813 | Predatory if `answer != "Other"` |
| `joelniklaus/online_terms_of_service` | All splits (EN only) | ~6,000+ | Predatory if any unfairness flag is True |
| Hand-crafted domain examples | Inline (5x weighted) | ~135 unique | Curated binary labels across employment, rental, IP, consumer domains |

After deduplication: **~19,400 unique clauses**.

### Hand-Crafted Examples

The HF datasets are 100% Terms of Service. Real contracts span employment, rental, IP, and consumer law — the hand-crafted examples fill this domain gap. Each predatory example is paired with safe counterparts for balanced signals. Categories include:

- **Employment**: IP assignment overreach, non-compete overreach, overtime waiver, at-will termination abuse
- **Rental/Lease**: asset seizure, unreasonable entry rights, security deposit forfeiture, habitability waivers
- **IP/Licensing**: irrevocable perpetual licenses, derivative work claims, permanent content transfers
- **Consumer**: class-action waivers, unilateral term changes, blanket liability waivers, refund waivers

Examples are duplicated 5x (`_HANDCRAFTED_WEIGHT`) so they don't get drowned out by the ~19k HF samples.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_MODEL_NAME` | `"all-mpnet-base-v2"` | High-performance SentenceTransformers model |
| `_EXPORT_PATH` | `"momotopsy_risk_model.pkl"` | Output path for the trained model |
| `_TEST_SIZE` | `0.20` | Test split ratio |
| `_RANDOM_STATE` | `42` | Random seed for reproducibility |
| `_UNFAIR_FLAGS` | `["a", "ch", "cr", ...]` | Unfairness topic flags for online_terms_of_service dataset |
| `_HANDCRAFTED_WEIGHT` | `5` | Multiplier for hand-crafted example repetition |

### `_load_lex_glue() -> pd.DataFrame`

Downloads all splits of `lex_glue/unfair_tos`, concatenates them, and creates the binary `is_predatory` column.

### `_load_legalbench() -> pd.DataFrame`

Downloads `nguha/legalbench` unfair_tos test split. Maps `answer` column to binary — anything that isn't "Other" is predatory.

### `_load_online_tos() -> pd.DataFrame`

Downloads all splits of `joelniklaus/online_terms_of_service`, filters to English clauses only, and marks any clause with at least one unfairness flag as predatory.

### `_load_handcrafted() -> pd.DataFrame`

Loads the inline hand-crafted domain examples and duplicates them by the weight factor.

### `main()`

End-to-end training pipeline:

1. **Data Ingestion** — Loads all four datasets, combines into a single DataFrame, deduplicates on `text`.
2. **Semantic Embedding** — Loads `all-mpnet-base-v2`, encodes the `text` column into a 768-dim embedding matrix (`X`). Uses disk-caching to speed up retraining.
3. **SMOTETomek Resampling** — Applies SMOTE + Tomek Links on the training split. After resampling, we typically have ~27k balanced samples.
4. **Hyperparameter Tuning** — 80/20 stratified split. Uses `RandomizedSearchCV` on a `HistGradientBoostingClassifier` to optimize `learning_rate`, `max_depth`, and `l2_regularization`.
5. **Evaluation & Export** — Prints detailed metrics, saves a confusion matrix plot, and exports the model via `joblib.dump()`.

### Training Results (v2 - MPNet + Tuned)

| Metric | Safe | Predatory |
|---|---|---|
| Precision | 0.98 | 0.71 |
| Recall | 0.96 | 0.84 |
| F1-Score | 0.97 | 0.77 |

**Overall accuracy: 95.0%** (at 0.15 risk threshold) on 3,883 test samples. 
*Note: Precision was prioritized to 0.71+ to reduce false positives while maintaining 84%+ recall.*

---

## test_model.py — Model Validation Script

Validates the trained anomaly detector against a set of mock contract clauses. Lowkey just checks whether the model can tell apart chill contract language from straight-up predatory clauses.

### Module-Level Constants

| Constant | Value | Description |
|---|---|---|
| `_MODEL_PATH` | `"momotopsy_risk_model.pkl"` | Path to the trained model |
| `_ENCODER_NAME` | `"all-mpnet-base-v2"` | SentenceTransformers model (MPNet) |
| `_RISK_THRESHOLD` | `0.15` | Production risk threshold for flagging |

### `MOCK_CLAUSES`

A curated list of 12 mock legal clauses — mix of safe (rent payments, arbitration, overtime) and unhinged predatory ones (asset seizure, rights waiver, IP grabs). Bruh if the model can't handle these, we have a problem.

### `main()`

1. **Load model** — Reads `momotopsy_risk_model.pkl` via joblib. Exits gracefully with a clear error if the file doesn't exist.
2. **Load encoder** — Initializes `all-MiniLM-L6-v2`.
3. **Encode & predict** — Embeds the mock clauses, runs `predict()` for binary labels and `predict_proba()` for confidence scores.
4. **Pretty print** — Outputs a formatted table with clause number, verdict (SAFE / PREDATORY), risk percentage, and clause text. Summary stats at the bottom.
