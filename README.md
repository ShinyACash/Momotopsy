# Momotopsy

AI-powered Legal Contract Analyzer that detects predatory clauses using NLP embeddings and Graph Theory.
TS is a prototype and not the final bs.

## What it does

Upload a legal document (PDF, DOCX, or image) and Momotopsy will:
1. **Parse** the document into individual clauses
2. **Embed** each clause into a 384-dimensional vector using `all-MiniLM-L6-v2`
3. **Build a similarity graph** connecting semantically related clauses
4. **Flag predatory clauses** using a trained RandomForest classifier

## Tech Stack

| Layer | Tech |
|---|---|
| API | FastAPI, Uvicorn |
| Ingestion | PyMuPDF, python-docx, EasyOCR |
| ML | SentenceTransformers, scikit-learn, SMOTE |
| Graph | NetworkX |
| Frontend | React, D3.js *(planned)* |

## Project Structure

```
Momotopsy/
├── backend/
│   ├── main.py                      # FastAPI app — POST /analyze
│   ├── omni_parser.py               # Document ingestion (PDF/DOCX/image)
│   ├── graph_engine.py              # Clause similarity graph builder
│   ├── train_model.py               # Model training pipeline
│   ├── test_model.py                # Model validation with mock clauses
│   └── momotopsy_risk_model.pkl     # Trained classifier
├── requirements.txt
├── documentation.md                 # Backend API & module documentation
└── README.md
```

## Quick Start

```bash
pip install -r requirements.txt
```

### Train the model

```bash
cd backend
python train_model.py
```

### Run the API

```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`. Docs at `/docs`.

### Test the model

```bash
cd backend
python test_model.py
```

## Model Performance

Trained on ~13k deduplicated legal clauses from two HuggingFace datasets (`lex_glue/unfair_tos` + `nguha/legalbench`), with SMOTE oversampling to handle class imbalance.

| Metric | Safe | Predatory |
|---|---|---|
| Precision | 0.96 | 0.94 |
| Recall | 1.00 | 0.62 |
| F1-Score | 0.98 | 0.75 |

**Overall accuracy: 95.6%**

## API Usage

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@contract.pdf"
```

Returns a JSON response with the clause similarity graph, including risk scores and edge weights.