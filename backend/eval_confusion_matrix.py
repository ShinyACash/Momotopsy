import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datasets import concatenate_datasets, load_dataset
from sentence_transformers import SentenceTransformer
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import sys
import os

# Import loading logic from train_model if possible, otherwise define locally
sys.path.append(os.path.dirname(__file__))
try:
    from train_model import (
        _MODEL_NAME, _EXPORT_PATH, _TEST_SIZE, _RANDOM_STATE,
        _load_lex_glue, _load_legalbench, _load_online_tos, _load_handcrafted
    )
    _RISK_THRESHOLD = 0.15
except ImportError:
    print("Could not import from train_model.py. Ensure it is in the same directory.")
    sys.exit(1)

def main():
    print("re-loading datasets to reproduce the official test split...")
    df_lex = _load_lex_glue()
    df_bench = _load_legalbench()
    df_ots = _load_online_tos()
    df_hand = _load_handcrafted()

    df = pd.concat([df_lex, df_bench, df_ots, df_hand], ignore_index=True)
    df.drop_duplicates(subset="text", inplace=True)

    print(f"Total samples (deduplicated): {len(df)}")

    print(f"Loading SentenceTransformer ({_MODEL_NAME})...")
    model = SentenceTransformer(_MODEL_NAME)

    print("Encoding vectors...")
    X = model.encode(df["text"].tolist(), show_progress_bar=True, convert_to_numpy=True)
    y = df["is_predatory"].values

    print("Splitting data (80/20)...")
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=_TEST_SIZE, random_state=_RANDOM_STATE, stratify=y,
    )

    if not os.path.exists(_EXPORT_PATH):
        print(f"Model file {_EXPORT_PATH} not found. Run train_model.py first.")
        return

    print(f"Loading model from {_EXPORT_PATH}...")
    clf = joblib.load(_EXPORT_PATH)

    print("Evaluating on test set (with 0.15 recall-boost threshold)...")
    probas = clf.predict_proba(X_test)
    risk_scores = probas[:, 1]
    y_pred = (risk_scores >= _RISK_THRESHOLD).astype(int)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Safe", "Predatory"]))

    cm = confusion_matrix(y_test, y_pred)
    
    print("\nGenerating Confusion Matrix Plot...")
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Safe", "Predatory"])
    fig, ax = plt.subplots(figsize=(8, 6))
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    plt.title("Momotopsy Risk Model: Confusion Matrix Evaluation")
    
    plot_path = "confusion_matrix_val.png"
    plt.savefig(plot_path)
    print(f"Success! Plot saved to: {os.path.abspath(plot_path)}")
    plt.show()

if __name__ == "__main__":
    main()
