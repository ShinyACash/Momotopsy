from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from datasets import concatenate_datasets, load_dataset
from imblearn.over_sampling import SMOTE
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

_MODEL_NAME: str = "all-MiniLM-L6-v2"
_EXPORT_PATH: str = "momotopsy_risk_model.pkl"
_TEST_SIZE: float = 0.20
_RANDOM_STATE: int = 42


def _load_lex_glue() -> pd.DataFrame:
    ds_train = load_dataset("lex_glue", "unfair_tos", split="train")
    ds_val = load_dataset("lex_glue", "unfair_tos", split="validation")
    ds_test = load_dataset("lex_glue", "unfair_tos", split="test")
    ds_full = concatenate_datasets([ds_train, ds_val, ds_test])
    df = ds_full.to_pandas()
    df["is_predatory"] = df["labels"].apply(lambda lbls: int(len(lbls) > 0))
    return df[["text", "is_predatory"]].copy()


def _load_legalbench() -> pd.DataFrame:
    ds = load_dataset("nguha/legalbench", "unfair_tos", split="test")
    df = ds.to_pandas()
    df["is_predatory"] = df["answer"].apply(lambda a: int(a != "Other"))
    return df[["text", "is_predatory"]].copy()


def main() -> None:
    print("Downloading datasets...")

    print("  [1/2] lex_glue / unfair_tos (all splits)...")
    df_lex = _load_lex_glue()
    print(f"         {len(df_lex)} clauses")

    print("  [2/2] nguha/legalbench / unfair_tos (test)...")
    df_bench = _load_legalbench()
    print(f"         {len(df_bench)} clauses")

    df = pd.concat([df_lex, df_bench], ignore_index=True)
    df.drop_duplicates(subset="text", inplace=True)

    total = len(df)
    predatory = int(df["is_predatory"].sum())
    print(f"\n    Combined (deduplicated): {total}")
    print(f"    Predatory : {predatory}  ({predatory / total:.1%})")
    print(f"    Safe      : {total - predatory}  ({(total - predatory) / total:.1%})")

    print(f"\nLoading SentenceTransformer ({_MODEL_NAME})...")
    model = SentenceTransformer(_MODEL_NAME)

    print("Encoding vectors (this may take a minute)...")
    X = model.encode(
        df["text"].tolist(),
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    y = df["is_predatory"].values

    print(f"    Embedding matrix shape: {X.shape}")

    print("\nSplitting data (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=_TEST_SIZE, random_state=_RANDOM_STATE, stratify=y,
    )
    print(f"    Train: {len(X_train)}  |  Test: {len(X_test)}")

    print("Applying SMOTE oversampling on training set...")
    smote = SMOTE(random_state=_RANDOM_STATE)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    pred_count = int(np.sum(y_train_resampled))
    safe_count = len(y_train_resampled) - pred_count
    print(f"    After SMOTE: {len(X_train_resampled)}  (Safe: {safe_count}, Predatory: {pred_count})")

    print("Training RandomForestClassifier (n_estimators=200)...")
    clf = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=_RANDOM_STATE, n_jobs=-1)
    clf.fit(X_train_resampled, y_train_resampled)
    print("Training complete.")

    print("\nEvaluating on test set...")
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"    Accuracy: {acc:.4f}\n")
    print(classification_report(
        y_test, y_pred, target_names=["Safe", "Predatory"],
    ))

    print(f"Exporting model -> {_EXPORT_PATH}")
    joblib.dump(clf, _EXPORT_PATH)
    print("Model saved successfully.\n")


if __name__ == "__main__":
    main()
