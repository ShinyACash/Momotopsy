from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_PATH: str = "momotopsy_risk_model.pkl"
_ENCODER_NAME: str = "all-MiniLM-L6-v2"

MOCK_CLAUSES: list[str] = [
    "The tenant agrees to pay rent on the 1st of each month.",
    "Both parties agree to resolve disputes through binding arbitration.",
    "The company reserves the right to terminate this agreement at any time, without notice, and seize all user assets.",
    "Users grant the company an irrevocable, perpetual, worldwide license to all content they create, including derivative works.",
    "The landlord shall maintain the property in a habitable condition as required by law.",
    "The service provider may modify these terms at any time without prior notification, and continued use constitutes acceptance.",
    "Either party may terminate this agreement with 30 days written notice.",
    "By signing, the user waives all rights to class-action lawsuits and agrees to forfeit any claims exceeding $100.",
    "The employee shall receive overtime compensation in accordance with applicable labor regulations.",
    "The company shall not be held liable for any damages, losses, or injuries arising from the use of its products, under any circumstances whatsoever.",
    "All intellectual property developed during employment shall belong exclusively to the employer, including work done outside office hours on personal equipment.",
    "Payments are due within 30 days of invoice receipt.",
]


def main() -> None:
    pkl = Path(_MODEL_PATH)
    if not pkl.exists():
        print(f"\nModel file not found: {pkl.resolve()}")
        print("\tRun train_model.py first to generate the .pkl file.\n")
        sys.exit(1)

    print(f"Loading trained model from {_MODEL_PATH}...")
    clf = joblib.load(_MODEL_PATH)

    print(f"Loading SentenceTransformer ({_ENCODER_NAME})...")
    encoder = SentenceTransformer(_ENCODER_NAME)

    print(f"Encoding {len(MOCK_CLAUSES)} mock clauses...\n")
    embeddings = encoder.encode(MOCK_CLAUSES, convert_to_numpy=True, show_progress_bar=False)

    predictions = clf.predict(embeddings)
    probabilities = clf.predict_proba(embeddings)

    print("=" * 90)
    print(f"  {'#':<4} {'VERDICT':<12} {'RISK %':<10} CLAUSE")
    print("=" * 90)

    for i, (clause, pred, proba) in enumerate(zip(MOCK_CLAUSES, predictions, probabilities), 1):
        label = "[naur] PREDATORY" if pred == 1 else "[yay] SAFE"
        risk_pct = proba[1] * 100
        truncated = clause if len(clause) <= 55 else clause[:52] + "..."
        print(f"  {i:<4} {label:<12} {risk_pct:>6.1f}%    {truncated}")

    print("=" * 90)

    total = len(predictions)
    flagged = int(np.sum(predictions))
    safe = total - flagged
    print(f"\nSummary: {total} clauses analyzed — {flagged} flagged, {safe} safe\n")


if __name__ == "__main__":
    main()
