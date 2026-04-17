# Momotopsy ◈

**Mapping the Rotten Filling in the Fine Print.**

Momotopsy is a premium AI-powered legal forensics platform designed to detect, analyze, and rectify predatory contract language. From apartment leases to employment agreements, Momotopsy empowers users to understand the high-risk implications of "standard" legal boilerplate and negotiate fair alternatives before they sign.

---

## ◈ Core Capabilities

### 1. Forensic Ingestion & Analysis
- **Multi-Modal Parsing**: High-fidelity text extraction from PDF, Word (.docx), and high-resolution images (OCR).
- **Interconnected Risk Mapping**: Clauses are embedded into 768-dimensional vector space. We use **Graph Theory (NetworkX)** to map dependencies and semantic overlaps between different parts of the contract.
- **Predatory Detection**: A custom-trained Random Forest classifier (MPNet + HistGradientBoosting) trained on 19,400+ clauses to identify toxic language with **84% recall**.

### 2. Negotiation Kit (Counter-Strike)
- **Rectification Engine**: High-risk clauses trigger a parallelized Llama-3.3-70b autopsy (via Groq), generating plain-English explanations and fair rewrites.
- **Template Generation**: Select flagged clauses to generate assertive, professional negotiation email templates ready for departure.

### 3. Scam Radar & Smart Reminders
- **Trending Risks**: A localized dashboard tracking the most common predatory categories (Data Harvesting, Asset Seizure, etc.) in real-time.
- **Lifecycle Engine**: Automatically detects deadlines and renewal dates within your contract, populating a push-notification center for smart reminders.

---

## ◈ Tech Stack

**Backend (Forensics & Intelligence)**
- **API**: FastAPI, Uvicorn
- **NLP**: SentenceTransformers (`all-mpnet-base-v2`), scikit-learn
- **AI**: Groq SDK + Llama-3.3-70b (Async inference)
- **Database**: SQLite (SQLAlchemy) for risk persistence & lifecycle events
- **OCR/Parsing**: PyMuPDF, python-docx, EasyOCR

**Frontend (Modern Antique Hub)**
- **Framework**: React.js (Vite)
- **Styling**: Premium "Modern Antique" Design System (Vanilla CSS + Custom Tokens)
- **UI Architecture**: Sidebar navigation with high-density glassmorphism and micro-animations.

---

## ◈ Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- Groq API Key (Set in `.env`)

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Create a .env file with GROQ_API_KEY
python main.py
```
*Note: The first run will download the 420MB MPNet model.*

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## ◈ The Design Philosophy
Momotopsy utilizes a **Modern Antique** aesthetic. We believe legal analysis shouldn't feel like a sterile spreadsheet—it should feel like a forensic investigation. The UI combines parchment tones, bronze accents, and deep ink-washes with cutting-edge glassmorphism and responsive layouts.

**Because signing should feel like a choice, not a trap.**