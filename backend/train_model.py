from __future__ import annotations

import joblib
import os
import numpy as np
import pandas as pd
from datasets import concatenate_datasets, load_dataset
from imblearn.combine import SMOTETomek
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import RandomizedSearchCV, train_test_split

_MODEL_NAME: str = "all-mpnet-base-v2"
_EXPORT_PATH: str = "momotopsy_risk_model.pkl"
_TEST_SIZE: float = 0.20
_RANDOM_STATE: int = 42

# Unfairness topic flags in joelniklaus/online_terms_of_service 
_UNFAIR_FLAGS: list[str] = ["a", "ch", "cr", "j", "law", "ltd", "ter", "use", "pinc"]


# Hand-crafted domain-specific examples 
# Each tuple: (clause_text, is_predatory)
# These fill the domain gap — the HF datasets are ToS-only, but real contracts
# span employment, rental, IP, and consumer law.

_HANDCRAFTED: list[tuple[str, int]] = [
    #  Employment — Predatory 
    ("All intellectual property developed during employment shall belong exclusively to the employer, including work done outside office hours on personal equipment.", 1),
    ("The employee agrees to a non-compete clause that extends for 10 years after termination, covering all industries and all geographic regions worldwide.", 1),
    ("The employer may terminate the employee at any time without cause, notice, or severance pay, and the employee waives all rights to contest the termination.", 1),
    ("The employee waives all rights to overtime compensation, regardless of hours worked or applicable labor regulations.", 1),
    ("Any inventions, discoveries, or creative works produced by the employee, whether during work hours or personal time, shall be the sole property of the employer in perpetuity.", 1),
    ("The employee agrees that the employer may reduce their salary, benefits, or working hours at any time without prior notice or consent.", 1),
    ("The employee shall not disparage the company in any form, including truthful statements, and breach of this clause results in forfeiture of all accrued benefits.", 1),
    ("The employer reserves the right to monitor all personal communications, devices, and social media accounts of the employee at any time without notice.", 1),
    ("Upon termination, the employee forfeits all unvested stock options, bonuses, and accrued vacation pay regardless of the reason for termination.", 1),
    ("The employee agrees to repay all training costs if they leave the company within 5 years, regardless of the reason for departure.", 1),

    # Employment — Safe 
    ("The employee shall receive overtime compensation in accordance with applicable labor regulations.", 0),
    ("Intellectual property created within the scope of employment and during work hours shall belong to the employer.", 0),
    ("Either party may terminate this employment agreement with 30 days written notice.", 0),
    ("The employee is entitled to annual leave as prescribed by applicable labor law.", 0),
    ("The employer shall provide a safe and healthy working environment in compliance with occupational health regulations.", 0),
    ("Non-compete restrictions shall be limited to 12 months and the employee's specific area of expertise within the local metropolitan area.", 0),
    ("The employee shall receive their final paycheck, including accrued vacation, within 14 days of termination.", 0),
    ("Performance reviews shall be conducted annually with clear, documented criteria communicated in advance.", 0),

    # Rental / Lease — Predatory 
    ("The landlord may enter the property at any time without prior notice for any reason, and the tenant waives all rights to privacy.", 1),
    ("The tenant forfeits the entire security deposit upon lease termination regardless of the condition of the property.", 1),
    ("The landlord may increase rent at any time without notice, and the tenant's continued occupancy constitutes acceptance of the new rate.", 1),
    ("The tenant waives all rights to withhold rent for any reason, including failure by the landlord to maintain habitable conditions.", 1),
    ("The landlord reserves the right to terminate this lease immediately and seize all of the tenant's personal belongings left on the premises.", 1),
    ("The tenant is responsible for all repairs, maintenance, and structural damage to the property, including damage caused by natural disasters or building defects.", 1),
    ("The tenant agrees not to pursue any legal action against the landlord for personal injury occurring on the property, under any circumstances.", 1),
    ("The landlord may assign this lease to any third party without notice to or consent from the tenant.", 1),

    # Rental / Lease — Safe 
    ("The tenant agrees to pay rent on the 1st of each month.", 0),
    ("The landlord shall maintain the property in a habitable condition as required by law.", 0),
    ("The landlord shall provide at least 24 hours written notice before entering the property, except in emergencies.", 0),
    ("The security deposit shall be returned within 30 days of lease termination, minus documented deductions for damages beyond normal wear and tear.", 0),
    ("Rent increases require 60 days written notice and shall not exceed the amount permitted by applicable rent control ordinances.", 0),
    ("Either party may terminate this lease with 30 days written notice at the end of any lease term.", 0),
    ("The landlord shall be responsible for repairs to the building structure, plumbing, and electrical systems.", 0),
    ("The tenant may sublease the property with prior written consent from the landlord, which shall not be unreasonably withheld.", 0),

    # IP / Licensing — Predatory 
    ("Users grant the company an irrevocable, perpetual, worldwide license to all content they create, including derivative works.", 1),
    ("The company may use, modify, sell, or sublicense any user-generated content without attribution, compensation, or notice to the user.", 1),
    ("By using this service, the user permanently transfers all intellectual property rights in any content uploaded to the platform.", 1),
    ("The company claims ownership of all data, metadata, and analytics derived from user activity, including personal data and behavioral profiles.", 1),
    ("Any feedback, suggestions, or ideas submitted to the company become the exclusive property of the company without any obligation to the user.", 1),
    ("The license granted to the company survives account deletion and extends to all future technologies and media formats not yet invented.", 1),
    ("The user grants the platform a perpetual, irrevocable, royalty-free license to reproduce, distribute, and create derivative works from all uploaded content.", 1),
    ("By uploading content, the user grants an unrestricted, perpetual license that cannot be revoked, even after account termination.", 1),
    ("The company obtains an irrevocable and perpetual right to use, sublicense, and commercialize any content submitted by users worldwide.", 1),
    ("All content uploaded to the service becomes the permanent property of the platform under an irrevocable worldwide license.", 1),
    ("The user hereby assigns a perpetual, irrevocable, transferable license covering all content and derivatives to the company.", 1),
    ("Users agree that the company holds a non-revocable, worldwide, perpetual license to all materials submitted, including the right to sublicense.", 1),
    ("The platform is granted an irrevocable, perpetual right to all user-generated content, extending to any modifications or adaptations thereof.", 1),
    ("By accepting these terms, users grant a perpetual and irrevocable license allowing the company to exploit submitted content in any medium.", 1),

    # IP / Licensing — Safe 
    ("Users retain ownership of their content and grant the platform a limited license to display it within the service.", 0),
    ("The company may use anonymized, aggregated data for analytics purposes only.", 0),
    ("All intellectual property rights in user content remain with the user; the platform license terminates upon account deletion.", 0),
    ("The company shall credit the original author when featuring user content in marketing materials.", 0),
    ("Users may request deletion of their content and associated data at any time.", 0),
    ("The platform's license to user content is limited, revocable, and expires upon account closure.", 0),
    ("Content licenses granted by users are non-exclusive and may be revoked with 30 days written notice.", 0),
    ("Users grant a limited license for display purposes only, which terminates when the content is removed by the user.", 0),

    # Consumer / Terms of Service — Predatory
    ("By signing, the user waives all rights to class-action lawsuits and agrees to forfeit any claims exceeding $100.", 1),
    ("The company shall not be held liable for any damages, losses, or injuries arising from the use of its products, under any circumstances whatsoever.", 1),
    ("The service provider may modify these terms at any time without prior notification, and continued use constitutes acceptance.", 1),
    ("The company reserves the right to terminate this agreement at any time, without notice, and seize all user assets.", 1),
    ("The company may share user data with any third party without consent or notification for any purpose.", 1),
    ("The user agrees to indemnify the company against all claims, including those arising from the company's own negligence or willful misconduct.", 1),
    ("Disputes shall be resolved exclusively in a jurisdiction chosen by the company, and the user waives any objection to inconvenient forum.", 1),
    ("The company may retroactively change pricing and charge the user for previously free features without prior notice.", 1),
    ("The user waives the right to a refund under any circumstances, including non-delivery of services or defective products.", 1),
    ("The company reserves the right to suspend the user's account and retain all funds without explanation or appeal.", 1),
    ("The user waives all rights to participate in class-action proceedings and forfeits any individual claims above $50.", 1),
    ("By using this service, the user agrees to waive the right to class-action lawsuits and caps all individual claims at $200.", 1),
    ("The user irrevocably waives the right to join or initiate any class-action lawsuit against the company.", 1),
    ("All claims must be brought individually, and the user waives any right to class-action relief or consolidated arbitration.", 1),
    ("The user agrees to forfeit all rights to class-action litigation, and any individual claim shall not exceed $75.", 1),
    ("By accepting these terms, the user permanently waives the right to class-action proceedings and agrees to binding individual arbitration.", 1),
    ("The user surrenders all class-action rights and agrees that any dispute shall be resolved individually with a maximum recovery of $100.", 1),
    ("Class-action lawsuits are expressly prohibited, and the user accepts that all disputes must be resolved through individual binding arbitration.", 1),

    # Consumer / Terms of Service — Safe 
    ("Payments are due within 30 days of invoice receipt.", 0),
    ("Both parties agree to resolve disputes through mediation before pursuing litigation.", 0),
    ("The company will notify users at least 30 days before any material changes to these terms.", 0),
    ("Users may cancel their subscription at any time and receive a prorated refund for the unused portion.", 0),
    ("The company limits its total liability to the amount paid by the user in the preceding 12 months.", 0),
    ("Personal data will be processed in accordance with our privacy policy and applicable data protection laws.", 0),
    ("The user may export their data in a standard format at any time during or after their subscription.", 0),
    ("Disputes shall be resolved under the laws of the user's country of residence.", 0),
    ("Users retain the right to pursue class-action remedies where permitted by applicable law.", 0),
    ("Nothing in this agreement limits the user's statutory right to participate in collective legal proceedings.", 0),
    # Safe arbitration — must contrast with predatory class-action waivers above
    ("Both parties agree to resolve disputes through binding arbitration administered by a neutral third party.", 0),
    ("Disputes shall be submitted to binding arbitration under the rules of the American Arbitration Association.", 0),
    ("The parties agree to resolve any dispute through final and binding arbitration, with each party bearing its own costs.", 0),
    ("Any controversy arising under this agreement shall be settled by arbitration in accordance with applicable rules.", 0),
    ("Both parties consent to binding arbitration as the exclusive means of resolving disputes under this contract.", 0),
    ("Disputes between the parties shall be resolved through arbitration conducted in the jurisdiction of the agreement.", 0),
    ("The parties agree to good-faith negotiation before initiating binding arbitration proceedings.", 0),
    ("All disputes shall be resolved through mediation first, and if unresolved, through binding arbitration.", 0),
]

# Weight multiplier — hand-crafted examples are duplicated this many times so
# they don't get drowned out by the ~19k HuggingFace samples.
_HANDCRAFTED_WEIGHT: int = 5


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


def _load_online_tos() -> pd.DataFrame:
    """Load joelniklaus/online_terms_of_service — English clauses only."""
    ds_train = load_dataset("joelniklaus/online_terms_of_service", split="train")
    ds_val = load_dataset("joelniklaus/online_terms_of_service", split="validation")
    ds_test = load_dataset("joelniklaus/online_terms_of_service", split="test")
    ds_full = concatenate_datasets([ds_train, ds_val, ds_test])
    df = ds_full.to_pandas()

    # Keep English clauses only
    df = df[df["language"] == "en"].copy()

    # A clause is predatory if ANY unfairness flag is True
    df["is_predatory"] = df[_UNFAIR_FLAGS].any(axis=1).astype(int)

    # Use the 'sentence' column as text
    df = df.rename(columns={"sentence": "text"})
    return df[["text", "is_predatory"]].copy()


def _load_handcrafted() -> pd.DataFrame:
    """Load hand-crafted domain-specific examples, duplicated by weight factor."""
    rows = [{"text": clause, "is_predatory": label} for clause, label in _HANDCRAFTED]
    df = pd.DataFrame(rows)
    # Repeat to amplify signal against the much larger HF datasets
    return pd.concat([df] * _HANDCRAFTED_WEIGHT, ignore_index=True)


def main() -> None:
    print("Downloading datasets...")

    print("  [1/4] lex_glue / unfair_tos (all splits)...")
    df_lex = _load_lex_glue()
    print(f"         {len(df_lex)} clauses")

    print("  [2/4] nguha/legalbench / unfair_tos (test)...")
    df_bench = _load_legalbench()
    print(f"         {len(df_bench)} clauses")

    print("  [3/4] joelniklaus/online_terms_of_service (EN only)...")
    df_ots = _load_online_tos()
    print(f"         {len(df_ots)} clauses")

    print("  [4/4] Hand-crafted domain examples...")
    df_hand = _load_handcrafted()
    pred_hand = int(df_hand["is_predatory"].sum())
    safe_hand = len(df_hand) - pred_hand
    print(f"         {len(df_hand)} clauses ({pred_hand} predatory, {safe_hand} safe)")

    df = pd.concat([df_lex, df_bench, df_ots, df_hand], ignore_index=True)
    df.drop_duplicates(subset="text", inplace=True)

    total = len(df)
    predatory = int(df["is_predatory"].sum())
    print(f"\n    Combined (deduplicated): {total}")
    print(f"    Predatory : {predatory}  ({predatory / total:.1%})")
    print(f"    Safe      : {total - predatory}  ({(total - predatory) / total:.1%})")

    print(f"\nLoading SentenceTransformer ({_MODEL_NAME})...")
    model = SentenceTransformer(_MODEL_NAME)

    X_CACHE = "embeddings_cache.npy"
    Y_CACHE = "labels_cache.npy"

    if os.path.exists(X_CACHE) and os.path.exists(Y_CACHE):
        print(f"Loading cached embeddings from {X_CACHE}...")
        X = np.load(X_CACHE)
        y = np.load(Y_CACHE)
    else:
        print("Encoding vectors (this may take a few minutes)...")
        X = model.encode(
            df["text"].tolist(),
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        y = df["is_predatory"].values
        print(f"Saving embeddings to cache...")
        np.save(X_CACHE, X)
        np.save(Y_CACHE, y)

    print(f"    Embedding matrix shape: {X.shape}")

    print("\nSplitting data (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=_TEST_SIZE, random_state=_RANDOM_STATE, stratify=y,
    )
    print(f"    Train: {len(X_train)}  |  Test: {len(X_test)}")

    print("Applying SMOTETomek resampling on training set...")
    resampler = SMOTETomek(random_state=_RANDOM_STATE)
    X_train_resampled, y_train_resampled = resampler.fit_resample(X_train, y_train)
    pred_count = int(np.sum(y_train_resampled))
    safe_count = len(y_train_resampled) - pred_count
    print(f"    After SMOTETomek: {len(X_train_resampled)}  (Safe: {safe_count}, Predatory: {pred_count})")

    print("Tuning HistGradientBoostingClassifier with RandomizedSearchCV...")
    base_clf = HistGradientBoostingClassifier(
        max_iter=500,
        class_weight="balanced",
        random_state=_RANDOM_STATE,
    )
    
    param_dist = {
        "learning_rate": [0.01, 0.05, 0.1],
        "max_depth": [4, 6, 8, None],
        "min_samples_leaf": [5, 10, 20],
        "l2_regularization": [0.0, 0.1, 1.0],
        "max_bins": [128, 255],
    }
    
    # 5-fold CV with 10 random iterations 
    search = RandomizedSearchCV(
        base_clf,
        param_distributions=param_dist,
        n_iter=10,
        cv=3,  # 3-fold to speed up slightly
        scoring="f1_macro",
        n_jobs=-1,
        random_state=_RANDOM_STATE,
        verbose=1,
    )
    
    search.fit(X_train_resampled, y_train_resampled)
    clf = search.best_estimator_
    
    print(f"Best params found: {search.best_params_}")
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

    print("Generating Confusion Matrix...")
    cm = confusion_matrix(y_test, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Safe", "Predatory"])
    
    fig, ax = plt.subplots(figsize=(8, 6))
    disp.plot(ax=ax, cmap="Blues", values_format="d")
    plt.title(f"Momotopsy Risk Model: Confusion Matrix (Recall focus)")
    
    plot_path = "confusion_matrix_train.png"
    plt.savefig(plot_path)
    print(f"Confusion matrix plot saved to {plot_path}")


if __name__ == "__main__":
    main()
