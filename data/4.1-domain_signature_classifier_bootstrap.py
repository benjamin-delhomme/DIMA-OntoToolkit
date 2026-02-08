#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
domain_signature_classifier.py

Refactored domain signature classification pipeline.
This script performs:
1. Data loading and merging from modular CSV outputs.
2. Strict feature selection and normalization to prevent data leakage/duplication.
3. Model training (Multinomial Logistic Regression with L2 penalty) and cross-validation.
4. Non-parametric bootstrapping (default B=2000) for coefficient uncertainty estimation.
5. Permutation testing for baseline significance.
6. Serialization of model artifacts (coefficients, errors) to allow decoupled plotting.
7. Generation of publication-ready visualizations.

USAGE:
  ./4.1-domain_signature_classifier_bootstrap.py \
      --domains bbc.co.uk kyivpost.com sputnikglobe.com \
      --n-splits 5 --n-boot 2000 --seed 42 --n-perm 500 --stat accuracy

"""

import sys
import re
import csv
import json
import argparse
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, permutation_test_score
from sklearn.utils import resample
from sklearn.metrics import confusion_matrix,accuracy_score, f1_score, precision_recall_fscore_support

# ---------------------------------------------------------------------------
# Data Loading & Preprocessing
# ---------------------------------------------------------------------------

def normalize_domain_name(raw_domain: object) -> str:
    """
    Normalizes a domain string by stripping whitespace, converting to lowercase,
    and removing 'www.' prefixes.

    Args:
        raw_domain (object): The raw domain string.

    Returns:
        str: The normalized domain string. Returns empty string if input is None.
    """
    if raw_domain is None:
        return ""
    s = str(raw_domain).strip().lower()
    s = re.sub(r"^www\.", "", s)
    return s


def load_and_merge_datasets(semantic_path: Path, bias_path: Path, quote_path: Path, debug: bool = False) -> pd.DataFrame:
    """
    Loads semantic, bias, and quote datasets from CSV files and merges them 
    on 'article_id'.

    Key Features:
    - Validates uniqueness of 'article_id' in source files (warns on duplicates).
    - Merges dataframes using a Left Join on the Semantic backbone.
    - Resolves the 'domain' column from available sources.
    - DROPS any article that contains missing values (NaNs) in the merged set to ensure data integrity.
    - Logs the number of dropped articles.

    Args:
        semantic_path (Path): Path to the semantic overview CSV.
        bias_path (Path): Path to the bias overview CSV.
        quote_path (Path): Path to the quote agent overview CSV.
        debug (bool): If True, prints verbose column lists and shapes for each file.

    Returns:
        pd.DataFrame: A clean, merged dataframe containing only articles with complete data.

    Raises:
        SystemExit: If input files are missing or 'domain' cannot be resolved.
    """
    # 1. Validation
    for p in (semantic_path, bias_path, quote_path):
        if not p.exists():
            sys.exit(f"[ERR] Input file not found: {p}")

    # 2. Loading (Force article_id to string)
    print(f"   > Loading CSVs...")
    sem_df = pd.read_csv(semantic_path, dtype={"article_id": str})
    bias_df = pd.read_csv(bias_path, dtype={"article_id": str})
    quote_df = pd.read_csv(quote_path, dtype={"article_id": str})

    # --- DUPLICATE CHECK ---
    for name, df in [("Semantic", sem_df), ("Bias", bias_df), ("Quote", quote_df)]:
        if df["article_id"].duplicated().any():
            dup_count = df["article_id"].duplicated().sum()
            print(f"[WARN] {name} file contains {dup_count} duplicate article_ids! Keeping first occurrence.")
            df.drop_duplicates(subset="article_id", keep="first", inplace=True)

    if debug:
        print(f"\n[DEBUG] --- CSV INSPECTION ---")
        print(f"[DEBUG] Semantic File ({sem_df.shape}): Columns: {', '.join(sem_df.columns)}")
        print(f"[DEBUG] Bias File ({bias_df.shape}):     Columns: {', '.join(bias_df.columns)}")
        print(f"[DEBUG] Quote File ({quote_df.shape}):    Columns: {', '.join(quote_df.columns)}")
        print(f"[DEBUG] ----------------------\n")

    # 3. Merging
    # Left join on semantic (backbone)
    df = sem_df.merge(bias_df, on="article_id", how="left", suffixes=("", "__bias"))
    df = df.merge(quote_df, on="article_id", how="left", suffixes=("", "__quote"))

    # 4. Domain Resolution
    if "domain" not in df.columns or df["domain"].isna().all():
        for candidate in ("domain__bias", "domain__quote"):
            if candidate in df.columns and not df[candidate].isna().all():
                df["domain"] = df[candidate]
                break
    
    if "domain" not in df.columns:
        sys.exit("[ERR] Merged dataframe lacks a 'domain' column. Check input CSV headers.")

    # 5. Normalization & Cleanup
    df["domain"] = df["domain"].apply(normalize_domain_name)

    # 6. MISSING VALUE HANDLING (Strict)
    initial_count = len(df)
    # We drop rows where ANY column is NaN. This is strict but safe for this analysis.
    # Note: We focus on numeric columns for this check to avoid dropping due to empty string metadata.
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df_clean = df.dropna(subset=numeric_cols)
    
    dropped_count = initial_count - len(df_clean)
    if dropped_count > 0:
        print(f"[WARN] Dropped {dropped_count} articles due to missing values (NaNs). Remaining: {len(df_clean)}")
        if debug:
            # Show which columns had the most NaNs
            nan_counts = df[numeric_cols].isna().sum()
            print(f"[DEBUG] Top missing columns:\n{nan_counts[nan_counts > 0].sort_values(ascending=False).head(5)}")

    if debug:
        print(f"[DEBUG] Final Merged DataFrame Shape: {df_clean.shape}")

    return df_clean


# ---------------------------------------------------------------------------
# Feature Engineering & Selection
# ---------------------------------------------------------------------------

def extract_semantic_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts predefined structural semantic features.

    Args:
        df (pd.DataFrame): The merged dataframe.

    Returns:
        pd.DataFrame: A dataframe containing only the selected semantic features.
    """
    # 1. Define Backbone Features (Scientific "Control" Variables)
    semantic_cols = [
        "avg_premises_per_argument", "avg_developments_per_argument", "avg_conclusions_per_argument",
        "avg_pdc_per_argument", "premise_ratio", "development_ratio", "conclusion_ratio", "arguments_per_100",
        "premises_per_100", "developments_per_100",	"conclusions_per_100"
    ]
    
    feats = {}
    for col in semantic_cols:
        if col in df.columns:
            # Prefix 'sem__' helps track origin in the final importance plot
            feats[f"sem__{col}"] = pd.to_numeric(df[col], errors="coerce")
            
    return pd.DataFrame(feats)


def extract_bias_features(df: pd.DataFrame, denominator_col: str = "total_arguments") -> pd.DataFrame:
    """
    Extracts bias features based on a STRICT whitelist.
    
    Includes:
    - Pre-calculated frequency metrics (_per_100).
    - Calculated density metrics (_per_argument) derived from raw counts (optional, enabled below).

    Args:
        df (pd.DataFrame): The merged dataframe.
        denominator_col (str): The column name to use for normalization (total_arguments).

    Returns:
        pd.DataFrame: A dataframe containing opportunity-normalized bias features.
    """
    feats = {}
    
    # 1. Define the Whitelist (Exact Column Names)
    bias_whitelist_freq = [
        "overall_per_100",
        "BizarrenessEffect_per_100",
        "ContrastEffect_per_100",
        "DistinctionBias_per_100",
        "NegativityBias_per_100",
        "OmissionBias_per_100",
        "VonRestorffEffect_per_100"
    ]
    
    # 2. Extract Whitelisted Frequency Features
    for col in bias_whitelist_freq:
        if col in df.columns:
            val = pd.to_numeric(df[col], errors="coerce")
            feats[f"bias__{col}"] = val

    # 3. Calculate Density Features (_per_argument)
    # To maintain consistency with previous logic, we also calculate the per-argument density
    # for these same bias types, if the raw count column exists.
    
    if denominator_col in df.columns:
        denom = pd.to_numeric(df[denominator_col], errors="coerce").replace(0, np.nan)
        
        # Map the normalized names back to their raw count names
        # e.g. "OmissionBias_per_100" -> "OmissionBias"
        for freq_col in bias_whitelist_freq:
            raw_col = freq_col.replace("_per_100", "") # e.g. "OmissionBias"
            
            if raw_col in df.columns:
                val = pd.to_numeric(df[raw_col], errors="coerce")
                # Only calculate if data exists
                if val.notna().sum() > 0:
                    feats[f"bias__{raw_col}_per_argument"] = val / denom

    return pd.DataFrame(feats)


def extract_quote_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts quote, agent, and mention features based on a STRICT whitelist.
    
    Args:
        df (pd.DataFrame): The merged dataframe.

    Returns:
        pd.DataFrame: A dataframe containing only the explicitly whitelisted features.
    """
    # 1. Define the Strict Whitelist (Exact Column Names)
    # These are the frequency (_per_100), density (_per_argument), and ratio (_per_quote) metrics.
    # Raw counts are excluded to prevent multicollinearity with article length.
    quote_whitelist = [
        # --- General Quote Metrics ---
        "quotes_per_100", "quotes_per_argument",
        
        # --- Quote Types ---
        "quote_type__DirectQuote_per_100", "quote_type__DirectQuote_per_argument",
        "quote_type__IndirectQuote_per_100", "quote_type__IndirectQuote_per_argument",
        "quote_type__ParaphrasedQuote_per_100", "quote_type__ParaphrasedQuote_per_argument",
        
        # --- Quote Status/Function ---
        "quote_status__CallToAction_per_100", "quote_status__CallToAction_per_argument",
        "quote_status__Contradiction_per_100", "quote_status__Contradiction_per_argument",
        "quote_status__HypotheticalStatement_per_100", "quote_status__HypotheticalStatement_per_argument",
        "quote_status__InterpretiveStatement_per_100", "quote_status__InterpretiveStatement_per_argument",
        "quote_status__OfficialPosition_per_100", "quote_status__OfficialPosition_per_argument",
        "quote_status__PersonalOpinion_per_100", "quote_status__PersonalOpinion_per_argument",
        "quote_status__ReportedStatement_per_100", "quote_status__ReportedStatement_per_argument",
        
        # --- Agents & Mentions General ---
        "unique_agents_per_100", "unique_agents_per_argument",
        "unique_agent_types_per_100", "unique_agent_types_per_argument",
        "mentions_per_100", "mentions_per_argument", "mentions_per_quote",
        
        # --- Specific Agent Types (Mentions) ---
        "mentions_agent_type__NarratedAcademic_per_100", "mentions_agent_type__NarratedAcademic_per_argument", "mentions_agent_type__NarratedAcademic_per_quote",
        "mentions_agent_type__NarratedActivist_per_100", "mentions_agent_type__NarratedActivist_per_argument", "mentions_agent_type__NarratedActivist_per_quote",
        "mentions_agent_type__NarratedAgentUndecided_per_100", "mentions_agent_type__NarratedAgentUndecided_per_argument", "mentions_agent_type__NarratedAgentUndecided_per_quote",
        "mentions_agent_type__NarratedBusinessLeader_per_100", "mentions_agent_type__NarratedBusinessLeader_per_argument", "mentions_agent_type__NarratedBusinessLeader_per_quote",
        "mentions_agent_type__NarratedCorporation_per_100", "mentions_agent_type__NarratedCorporation_per_argument", "mentions_agent_type__NarratedCorporation_per_quote",
        "mentions_agent_type__NarratedCriminal_per_100", "mentions_agent_type__NarratedCriminal_per_argument", "mentions_agent_type__NarratedCriminal_per_quote",
        "mentions_agent_type__NarratedCriminalOrganization_per_100", "mentions_agent_type__NarratedCriminalOrganization_per_argument", "mentions_agent_type__NarratedCriminalOrganization_per_quote",
        "mentions_agent_type__NarratedGeneralPublic_per_100", "mentions_agent_type__NarratedGeneralPublic_per_argument", "mentions_agent_type__NarratedGeneralPublic_per_quote",
        "mentions_agent_type__NarratedGeneralWorker_per_100", "mentions_agent_type__NarratedGeneralWorker_per_argument", "mentions_agent_type__NarratedGeneralWorker_per_quote",
        "mentions_agent_type__NarratedGovernment_per_100", "mentions_agent_type__NarratedGovernment_per_argument", "mentions_agent_type__NarratedGovernment_per_quote",
        "mentions_agent_type__NarratedInstitution_per_100", "mentions_agent_type__NarratedInstitution_per_argument", "mentions_agent_type__NarratedInstitution_per_quote",
        "mentions_agent_type__NarratedInternationalOrganization_per_100", "mentions_agent_type__NarratedInternationalOrganization_per_argument", "mentions_agent_type__NarratedInternationalOrganization_per_quote",
        "mentions_agent_type__NarratedJournalist_per_100", "mentions_agent_type__NarratedJournalist_per_argument", "mentions_agent_type__NarratedJournalist_per_quote",
        "mentions_agent_type__NarratedMediaOrganization_per_100", "mentions_agent_type__NarratedMediaOrganization_per_argument", "mentions_agent_type__NarratedMediaOrganization_per_quote",
        "mentions_agent_type__NarratedMilitary_per_100", "mentions_agent_type__NarratedMilitary_per_argument", "mentions_agent_type__NarratedMilitary_per_quote",
        "mentions_agent_type__NarratedMilitaryFigure_per_100", "mentions_agent_type__NarratedMilitaryFigure_per_argument", "mentions_agent_type__NarratedMilitaryFigure_per_quote",
        "mentions_agent_type__NarratedNGO_per_100", "mentions_agent_type__NarratedNGO_per_argument", "mentions_agent_type__NarratedNGO_per_quote",
        "mentions_agent_type__NarratedNarratedPerson_per_100", "mentions_agent_type__NarratedNarratedPerson_per_argument", "mentions_agent_type__NarratedNarratedPerson_per_quote",
        "mentions_agent_type__NarratedOrganization_per_100", "mentions_agent_type__NarratedOrganization_per_argument", "mentions_agent_type__NarratedOrganization_per_quote",
        "mentions_agent_type__NarratedPerson_per_100", "mentions_agent_type__NarratedPerson_per_argument", "mentions_agent_type__NarratedPerson_per_quote",
        "mentions_agent_type__NarratedPolitician_per_100", "mentions_agent_type__NarratedPolitician_per_argument", "mentions_agent_type__NarratedPolitician_per_quote",
        "mentions_agent_type__NarratedState_per_100", "mentions_agent_type__NarratedState_per_argument", "mentions_agent_type__NarratedState_per_quote"
    ]
    
    feats = {}
    for col in quote_whitelist:
        if col in df.columns:
            # Prefix 'quote__' helps track origin in the final importance plot
            # and prevents collisions with other feature sets.
            val = pd.to_numeric(df[col], errors="coerce")
            
            # Note: We do not check for empty here because if a whitelisted feature 
            feats[f"quote__{col}"] = val
            
    return pd.DataFrame(feats)


def build_feature_matrix(df: pd.DataFrame, target_domains: List[str]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Orchestrates feature extraction, filters the dataset to target domains, 
    and constructs the final X (features) and y (target) arrays.

    Args:
        df (pd.DataFrame): The merged dataframe.
        target_domains (List[str]): List of normalized domains to include in the analysis.

    Returns:
        Tuple[np.ndarray, np.ndarray, List[str]]: 
            - X: The feature matrix (float).
            - y: The target labels (string).
            - feature_names: List of column names corresponding to the columns in X.
    """
    # 1. Domain Filtering
    # Filter the dataframe to only include the requested domains
    # We use .copy() to avoid SettingWithCopy warnings on subsequent operations
    df_filtered = df[df["domain"].isin(target_domains)].copy()
    
    if len(df_filtered) == 0:
        sys.exit(f"[ERR] No articles found for domains: {target_domains}. Check spelling or input files.")

    print(f"   > Building features for {len(df_filtered)} articles across {len(target_domains)} domains...")

    # 2. Feature Extraction (Modular)
    # Each function returns a DataFrame of features sharing the same index as df_filtered
    sem_feats = extract_semantic_features(df_filtered)
    bias_feats = extract_bias_features(df_filtered)
    quote_feats = extract_quote_features(df_filtered)

    # 3. Horizontal Concatenation
    # Combine all feature sets into one large matrix
    X_df = pd.concat([sem_feats, bias_feats, quote_feats], axis=1)

    # 4. Final Cleanup
    # Fill any remaining NaNs (e.g., div by zero) with 0 before passing to sklearn
    # (Though the pipeline Imputer handles this, it's good practice to be clean here)
    X_df = X_df.fillna(0.0)

    # 5. Output Formatting
    X = X_df.to_numpy(dtype=np.float64)
    y = df_filtered["domain"].to_numpy(dtype=str)
    feature_names = list(X_df.columns)

    return X, y, feature_names


# ---------------------------------------------------------------------------
# Modeling & Statistical Evaluation
# ---------------------------------------------------------------------------

def build_pipeline(seed: int = 42) -> Pipeline:
    """
    Constructs the classification pipeline: Scaler -> Logistic Regression.
    
    Note: No Imputer is needed because build_feature_matrix() fills NaNs with 0.0,
    which is the semantically correct value for missing counts/ratios.

    Args:
        seed (int): Random seed for solver reproducibility.

    Returns:
        Pipeline: The un-fitted scikit-learn pipeline object.
    """
    return Pipeline([
        # Step 1: Normalize Features
        # Centers and scales features (mean=0, var=1).
        # Essential for L2 regularization and comparing coefficients (Beta).
        ('scaler', StandardScaler()),
        
        # Step 2: Classifier
        # - class_weight='balanced': Ensures small domains (e.g. BBC) aren't ignored
        ('clf', LogisticRegression(
            # multi_class='multinomial', 
            C=1.0,
            solver='lbfgs',
            max_iter=1000,  # High iteration count to prevent convergence warnings
            random_state=seed,
            class_weight='balanced' 
        ))
    ])
    
def stratified_resample_indices(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Resample indices WITHIN each class to preserve class sizes.
    Used for bootstrapping OOF predictions.
    """
    out = []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        if idx.size == 0:
            continue
        # Sample with replacement
        out.extend(rng.choice(idx, size=idx.size, replace=True).tolist())
    return np.array(out, dtype=int)


def run_statistical_analysis(pipeline: Pipeline, X: np.ndarray, y: np.ndarray, 
                             feature_names: List[str], n_splits: int, n_boot: int, 
                             n_perm: int, metric: str, seed: int) -> Dict:
    """
    Orchestrates the full statistical evaluation suite for the classifier.

    Specs:
    1. Executes Stratified K-Fold Cross-Validation to estimate predictive performance.
    2. Computes a Confusion Matrix based on Out-Of-Fold (OOF) predictions.
    3. Performs Non-Parametric Bootstrap resampling on OOF PREDICTIONS (for distribution plot & CI).
    4. Performs Non-Parametric Bootstrap resampling on MODEL COEFFICIENTS (for feature plot).
    5. Runs a Permutation Test to calculate the empirical p-value against a null hypothesis.

    Args:
        pipeline (Pipeline): The unfitted scikit-learn pipeline (Scaler -> Classifier).
        X (np.ndarray): The feature matrix of shape (n_samples, n_features).
        y (np.ndarray): The target vector of shape (n_samples,).
        feature_names (List[str]): List of feature names corresponding to columns in X.
        n_splits (int): Number of folds for Cross-Validation.
        n_boot (int): Number of bootstrap iterations.
        n_perm (int): Number of permutation runs for significance testing (Must be > 0).
        metric (str): The scoring metric to use (e.g., 'accuracy', 'f1_macro').
        seed (int): Random seed for reproducibility.

    Returns:
        Dict: A dictionary containing all computed artifacts.
    """
    results = {}
    classes = np.unique(y)
    results["classes"] = classes.tolist()
    results["feature_names"] = feature_names

    # Calculate Majority Baseline
    unique, counts = np.unique(y, return_counts=True)
    majority_baseline = float(np.max(counts) / len(y))
    results["majority_baseline"] = majority_baseline

    # 1. Cross-Validation (Observed)
    print(f"   > Running {n_splits}-Fold CV...")
    
    cv_mean, cv_preds, cv_scores = evaluate_model_cv(pipeline, X, y, n_splits, seed, metric)
    
    results["cv_mean"] = cv_mean
    results["cv_scores"] = cv_scores.tolist() 
    results["cv_preds"] = cv_preds.tolist() 
    
    # Calculate Comprehensive Metrics
    acc = accuracy_score(y, cv_preds)
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y, cv_preds, average='macro', zero_division=0)
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(y, cv_preds, average='weighted', zero_division=0)
    
    results["metrics"] = {
        "accuracy": acc,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "precision_macro": p_macro,
        "recall_macro": r_macro,
        "precision_weighted": p_weighted,
        "recall_weighted": r_weighted
    }
    
    print(f"     CV Accuracy: {acc:.3f} | F1 Macro: {f1_macro:.3f}")

    # Bootstrap the OOF Predictions
    print(f"   > Bootstrapping OOF predictions ({n_boot} iter)...")
    rng = np.random.default_rng(seed)
    boot_scores = np.empty(n_boot, dtype=float)
    
    if metric == "accuracy":
        scorer = accuracy_score
    else:
        scorer = lambda yt, yp: f1_score(yt, yp, average="macro")

    for b in range(n_boot):
        idx = stratified_resample_indices(y, rng)
        boot_scores[b] = scorer(y[idx], cv_preds[idx])
        
    results["boot_scores"] = boot_scores.tolist()

    # Calculate 95% Confidence Intervals
    alpha = 0.05
    results["ci_low"] = float(np.percentile(boot_scores, 100.0 * alpha / 2.0))
    results["ci_high"] = float(np.percentile(boot_scores, 100.0 * (1.0 - alpha / 2.0)))

    # Compute Confusion Matrix
    cm = confusion_matrix(y, cv_preds, labels=classes)
    results["confusion_matrix"] = cm.tolist() 

    # 2. Bootstrap Coefficients (Feature Stability)
    print(f"   > Bootstrapping coefficients (Model Weights)...")
    
    coef_mean, coef_error = compute_bootstrap_coefficients(pipeline, X, y, n_boot, seed)
    results["coef_mean"] = coef_mean.tolist()
    results["coef_error"] = coef_error.tolist()

    # 3. Permutation (Significance Testing)
    if n_perm <= 0:
        print(f"[WARN] n_perm is {n_perm}. Skipping Permutation Test.")
        results["perm_mean"] = None
        results["perm_pvalue"] = None
        results["perm_scores"] = []
    else:
        print(f"   > Running {n_perm} Permutation Tests...")
        perm_mean, p_value, perm_scores = run_permutation_test(pipeline, X, y, n_perm, n_splits, seed, metric)
        
        results["perm_mean"] = perm_mean
        results["perm_pvalue"] = p_value
        results["perm_scores"] = perm_scores.tolist()
        
        print(f"     Permutation P-value: {p_value:.4f} (Null Baseline: {perm_mean:.3f})")

    return results


def evaluate_model_cv(pipeline: Pipeline, X: np.ndarray, y: np.ndarray, 
                      n_splits: int, random_seed: int, metric: str = "accuracy") -> Tuple[float, np.ndarray, np.ndarray]:
    """
    Evaluates the model using Stratified K-Fold cross-validation.
    
    Returns:
        - Mean Score (float)
        - Predictions (np.ndarray) - useful for Confusion Matrix later
        - Raw Scores (np.ndarray) - useful for Distribution Plots
    """
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_seed)
    
    # 1. Get the Out-Of-Fold Predictions (for confusion matrix)
    # This simulates what the model predicts for data it hasn't seen.
    y_pred = cross_val_predict(pipeline, X, y, cv=cv, n_jobs=-1)
    
    # 2. Get the Scores (for robust mean/std calculation)
    # We use 'cross_val_score' because it handles scoring metrics (like 'macro_f1') strictly.
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring=metric, n_jobs=-1)
    
    mean_score = float(np.mean(scores))
    
    return mean_score, y_pred, scores


def compute_bootstrap_coefficients(pipeline: Pipeline, X: np.ndarray, y: np.ndarray, 
                                   n_boot: int, random_seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Estimates model coefficients and their uncertainty using non-parametric bootstrap resampling.
    
    Returns:
        - base_coefs: The mean coefficient values across all bootstraps.
        - coef_errors: The 95% Confidence Interval (margin of error).
    """
    # 1. Fit the "Base" model on the full original dataset (Ground Truth)
    pipeline.fit(X, y)
    
    # Determine shapes
    # If binary, coef_ is (1, n_features). If multiclass, (n_classes, n_features).
    if hasattr(pipeline['clf'], 'coef_'):
         original_coefs = pipeline['clf'].coef_
    else:
        # Fallback for models that don't expose coef_ directly, though LogReg does.
        raise ValueError("Classifier must have .coef_ attribute (e.g. LogisticRegression)")

    n_classes = original_coefs.shape[0]
    n_features = original_coefs.shape[1]
    
    # 2. Bootstrap Loop
    boot_coefs = np.zeros((n_boot, n_classes, n_features))
    
    # Fix seed for reproducibility of the whole loop
    rng = np.random.RandomState(random_seed)
    
    for i in range(n_boot):
        # Resample articles with replacement
        # We use a different seed for every iteration derived from the main rng
        iter_seed = rng.randint(0, 100000)
        X_res, y_res = resample(X, y, replace=True, random_state=iter_seed)
        
        # Fit model on resampled data
        pipeline.fit(X_res, y_res)
        
        # Store coefficients
        boot_coefs[i] = pipeline['clf'].coef_

    # 3. Calculate Statistics
    # Mean of bootstraps (should be close to original, but helps smooth noise)
    mean_coefs = np.mean(boot_coefs, axis=0)
    
    # Standard Deviation of the coefficients
    std_coefs = np.std(boot_coefs, axis=0)
    
    # 95% Confidence Interval = 1.96 * Standard Error
    coef_errors = 1.96 * std_coefs
    
    return mean_coefs, coef_errors


def run_permutation_test(pipeline: Pipeline, X: np.ndarray, y: np.ndarray, 
                         n_perm: int, n_splits: int, random_seed: int, metric: str = "accuracy") -> Tuple[float, float, np.ndarray]:
    """
    Performs a label-shuffling permutation test to establish a null baseline.
    
    Returns:
        - perm_mean: Average score of the "random" models.
        - p_value: Probability that the real model is better than random chance.
        - perm_scores: The array of all permutation scores (for plotting).
    """
    if n_perm <= 0:
        return 0.0, 1.0, np.array([])

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_seed)
    
    # scikit-learn has a built-in efficient function for this
    score, perm_scores, pvalue = permutation_test_score(
        pipeline, 
        X, 
        y, 
        cv=cv, 
        n_permutations=n_perm, 
        scoring=metric, 
        n_jobs=-1, 
        random_state=random_seed
    )
    
    perm_mean = float(np.mean(perm_scores))
    
    return perm_mean, float(pvalue), perm_scores

# ---------------------------------------------------------------------------
# Serialization & IO
# ---------------------------------------------------------------------------

class NumpyEncoder(json.JSONEncoder):
    """ Helper to serialize Numpy arrays to JSON """
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super(NumpyEncoder, self).default(obj)

def save_model_artifacts(out_dir: Path, prefix: str, results: Dict) -> Path:
    """
    Serializes the ENTIRE statistical results dictionary to JSON.
    This enables full caching: we can skip the model run entirely if this exists.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{prefix}_artifacts.json"
    
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            # Use the custom encoder to handle all numpy arrays inside the dict automatically
            json.dump(results, f, indent=4, cls=NumpyEncoder)
        print(f"   > Artifacts saved to: {out_path}")
    except Exception as e:
        sys.exit(f"[ERR] Failed to save artifacts: {e}")
        
    return out_path

def load_model_artifacts(artifact_path: Path) -> Dict:
    """
    Loads the full results dictionary from JSON.
    """
    if not artifact_path.exists():
        sys.exit(f"[ERR] Artifact file not found: {artifact_path}")
        
    with open(artifact_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Convert lists back to Numpy arrays for the plotting functions
    # (Plotting functions expect arrays for math operations)
    keys_to_numpy = ["cv_scores", "perm_scores", "coef_mean", "coef_error", "confusion_matrix", "classes"]
    
    for k in keys_to_numpy:
        if k in data and data[k] is not None:
            data[k] = np.array(data[k])
            
    return data


def save_results_csv(results: Dict, out_path: Path, args: argparse.Namespace) -> None:
    """
    Saves a comprehensive summary CSV containing all key performance metrics.
    """
    # Extract the nested metrics dict we created in run_statistical_analysis
    m = results.get("metrics", {})
    
    summary = {
        "domains": " ".join(args.domains),
        
        # Main Performance Metrics
        "accuracy": m.get("accuracy", results.get("cv_mean")),
        "f1_macro": m.get("f1_macro"),
        "f1_weighted": m.get("f1_weighted"),
        "precision_macro": m.get("precision_macro"),
        "recall_macro": m.get("recall_macro"),
        
        # Confidence Intervals (for the main metric chosen)
        "ci_low": results.get("ci_low"),
        "ci_high": results.get("ci_high"),
        
        # Statistical Significance & Baselines
        "perm_pvalue": results.get("perm_pvalue") if results.get("perm_pvalue") is not None else "N/A",
        "majority_baseline": results.get("majority_baseline"),
        "chance_baseline": 1.0 / len(results.get("classes", [])),
        
        # Experiment Metadata
        "n_boot": args.n_boot,
        "n_perm": args.n_perm,
        "seed": args.seed
    }
    
    # Save to CSV
    pd.DataFrame([summary]).to_csv(out_path, index=False)
    print(f"   > Detailed Summary CSV saved to: {out_path}")

# ---------------------------------------------------------------------------
# Visualization (Decoupled)
# ---------------------------------------------------------------------------

def clean_feature_label(raw_feature_name: str) -> str:
    """
    Maps raw programmatic feature names to publication-ready human-readable labels.
    Updated to use explicit units (per 100 words, per Argument, per Quote).

    Args:
        raw_feature_name (str): The raw column name from the dataframe.

    Returns:
        str: A formatted string suitable for plot y-axes.
    """
    raw_name = raw_feature_name
    name = raw_name.lower()
    base = ""
    suffix = ""

    # 1. Determine Base Name
    if 'paraphrasedquote' in name: base = "Paraphrased Quotes"
    elif 'indirectquote' in name: base = "Indirect Quotes"
    elif 'directquote' in name: base = "Direct Quotes"
    
    elif 'overall_per_100' in name: base = "Total Bias" 
    
    elif 'distinctionbias' in name: base = "Technique: Distinction Bias"
    elif 'omissionbias' in name: base = "Technique: Omission Bias"
    elif 'negativitybias' in name: base = "Technique: Negativity Bias"
    elif 'narratedinstitution' in name: base = "Mentions: Institution"
    
    elif 'avg_pdc' in name: base = "Structural Complexity"
    
    elif 'avg_premises' in name: base = "Premises"
    elif 'avg_developments' in name: base = "Developments"
    elif 'avg_conclusions' in name: base = "Conclusions"
    elif 'arguments_per_100' in name: base = "Arguments"
    
    elif 'mentions' in name and 'narrated' in name:
        short = name.split('mentions_agent_type__')[-1] if 'mentions_agent_type__' in name else name
        short = short.replace('mentions', '').replace('quote__', '').replace('narrated', '')
        short = short.replace('_per_argument', '').replace('_per_quote', '').replace('_per_100', '')
        short = short.replace('_', ' ').strip()
        base = f"Mentions: {short.capitalize()}"
    else:
        # Generic fallback
        base = raw_name.replace('bias__', '').replace('quote__', '').replace('sem__', '')
        base = base.replace('_per_argument', '').replace('_per_quote', '').replace('_per_100', '')
        base = base.replace('_', ' ').strip().capitalize()

    # 2. Determine Suffix (Explicit Units)
    if '_per_quote' in raw_name:
        suffix = " (per Quote)"
    elif '_per_100' in raw_name:
        suffix = " (per 100 words)"
    elif '_per_argument' in raw_name:
        suffix = " (per Argument)"
    else:
        suffix = ""

    return f"{base}{suffix}"


def generate_signature_plot(stats_results: Dict, out_path: Path, n_top: int = 10) -> None:
    """
    Generates and saves the horizontal bar chart displaying the top predictive features 
    per class, complete with error bars.
    """
    print(f"   > Generating clean signature plot with ERROR BARS...")

    # --- UNPACK DATA ---
    feature_names = stats_results["feature_names"]
    classes = np.array(stats_results["classes"])
    coefs = np.array(stats_results["coef_mean"])
    errors = np.array(stats_results["coef_error"])

    # --- 1. PRE-CALCULATE GLOBAL LIMIT ---
    # We iterate through all classes first to find the single largest value (Coef + Error).
    # This ensures all subplots use the exact same x-axis scale for valid comparison.
    global_max = 0.0
    
    for i in range(len(classes)):
        # Create temp DF to find top N features for this class
        temp_df = pd.DataFrame({'Coef': coefs[i], 'Error': errors[i]})
        temp_df['abs'] = temp_df['Coef'].abs()
        top_n = temp_df.sort_values(by='abs', ascending=False).head(n_top)
        
        # Calculate max extent (bar length + error bar)
        current_max = (top_n['abs'] + top_n['Error']).max()
        if current_max > global_max:
            global_max = current_max
            
    # Add 15% padding
    global_limit = global_max * 1.15

    # --- 2. FIGURE SETUP ---
    fig_height = max(14, n_top * 2.0)
    fig, axes = plt.subplots(1, len(classes), figsize=(42, fig_height))

    if len(classes) == 1: 
        axes = [axes]

    for i, class_label in enumerate(classes):
        # --- DATA PREP ---
        coef_df = pd.DataFrame({
            'Feature': feature_names, 
            'Coef': coefs[i],
            'Error': errors[i] 
        })
        coef_df['abs'] = coef_df['Coef'].abs()
        
        # Filter top N by magnitude
        top_feats = coef_df.sort_values(by='abs', ascending=False).head(n_top)
        # Sort by actual value for plotting order (Negative -> Positive)
        top_feats = top_feats.sort_values(by='Coef')

        # --- LABEL CLEANING ---
        final_labels = []
        seen_labels = {} 

        for raw_name in top_feats['Feature']:
            label_candidate = clean_feature_label(raw_name)

            if label_candidate in seen_labels:
                seen_labels[label_candidate] += 1
                final_label = f"{label_candidate} ({seen_labels[label_candidate]})"
            else:
                seen_labels[label_candidate] = 1
                final_label = label_candidate
            
            final_labels.append(textwrap.fill(final_label, width=22))

        # --- PLOTTING ---
        ax = axes[i]
        colors = ['#d6604d' if c < 0 else '#4393c3' for c in top_feats['Coef']]

        ax.barh(final_labels, top_feats['Coef'], xerr=top_feats['Error'], 
                color=colors, edgecolor='black', height=0.75,
                capsize=8, error_kw={'elinewidth': 2.5, 'ecolor': 'black'})

        # Styling
        ax.set_title(f"OUTLET: {str(class_label).upper()}", fontsize=30, fontweight='bold', pad=40)
        ax.axvline(0, color='black', linewidth=2.5)
        ax.set_xlabel("Feature Influence (Standardized Beta)", fontsize=22, fontweight='bold', labelpad=20)

        ax.tick_params(axis='y', labelsize=25, pad=10)
        ax.tick_params(axis='x', labelsize=20)
        
        ax.grid(axis='x', linestyle='--', alpha=0.5, linewidth=1.5)
        
        # --- APPLY GLOBAL LIMITS & FORMATTING ---
        ax.set_xlim(-global_limit, global_limit)
        
        # Force consistent 2-decimal formatting (e.g. "1.00", "1.50")
        ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.2f'))

    # Final Layout Adjustments
    plt.subplots_adjust(left=0.20, right=0.98, wspace=0.6, top=0.90, bottom=0.15)

    # Save
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"   > Clean publication plot saved to: {out_path}")


def generate_cv_distribution_plot(observed_score: float, boot_scores: np.ndarray, 
                                  ci_low: float, ci_high: float,
                                  majority_baseline: float,
                                  perm_scores: np.ndarray, perm_pvalue: float,
                                  n_classes: int, n_splits: int, n_boot: int, 
                                  seed: int, metric: str, out_path: Path) -> None:
    """
    Generates a histogram comparing the model's performance distribution (CV) against 
    the null permutation distribution and chance baselines.

    Specs:
    1. Null Distribution (Gray): Shows scores obtained by random shuffling (Permutation Test).
    2. Model Distribution (Blue): Shows scores obtained by the real model (Cross-Validation).
    3. Baselines: Vertical lines for Random Chance (1/N) and Observed Mean Accuracy.
    4. Annotations: Displays the empirical P-value if permutation data is present.

    Args:
        observed_score (float): The mean CV score (the "Main" number).
        boot_scores (np.ndarray): Array of CV scores (representing model variance).
        perm_scores (np.ndarray): Array of permutation scores (representing null hypothesis).
        n_classes (int): Number of target domains (used for 1/N chance line).
        out_path (Path): Destination path.
    """
    print(f"   > Generating distribution plot (Model vs. Null)...")

    # Setup Figure
    plt.figure(figsize=(10.8, 6.2))
    
    # 1. Histograms (No KDE curves, just bars)
    plt.hist(boot_scores, bins=30, alpha=0.70, label="Bootstrap (resample articles from OOF predictions)")
    
    if len(perm_scores) > 0:
        plt.hist(perm_scores, bins=30, alpha=0.45, label="Permutation null (label shuffles)")

    # 2. Vertical Lines (Observed + CI)
    plt.axvline(observed_score, linewidth=2, label="Observed OOF CV score")
    plt.axvline(ci_low, linestyle="--", linewidth=1, label="Bootstrap CI low")
    plt.axvline(ci_high, linestyle="--", linewidth=1, label="Bootstrap CI high")

    # 3. Baselines (Chance + Majority)
    chance_uniform = 1.0 / float(n_classes)
    plt.axvline(chance_uniform, linestyle=":", linewidth=2, label=f"Uniform chance (1/K) = {chance_uniform:.3f}")

    # Plot Majority Baseline ---
    plt.axvline(majority_baseline, linestyle="-.", linewidth=2, label=f"Majority-class baseline = {majority_baseline:.3f}")


    # 4. Title & Labels
    conf = 95.0
    title = (
        "Domain predictability from semantic + bias + quote features\n"
        f"OOF {n_splits}-fold CV {metric}; bootstrap CI (conf={conf:.1f}, B={n_boot}, seed={seed})"
    )
    if perm_pvalue is not None:
        title += f"\nPermutation p-value (perm >= observed) = {perm_pvalue:.4f}"
        
    plt.title(title)
    plt.xlabel(f"Cross-validated {metric}")
    plt.ylabel("Frequency")
    plt.legend(loc="upper left", fontsize=9, frameon=False, ncol=1)
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=260)
    plt.close()
    print(f"   > Distribution plot saved to: {out_path}")


def plot_distributions(results: Dict, out_path: Path, args: argparse.Namespace) -> None:
    """
    Wrapper that unpacks the results dictionary and calls the plotting engine.
    """
    cv_mean = results["cv_mean"]
    
    # Safe check for boot_scores
    # We explicitly check 'is not None' and 'len > 0' to avoid ValueError 
    # if boot_scores is already a NumPy array.
    boot_data = results.get("boot_scores")
    if boot_data is not None and len(boot_data) > 0:
        boot_scores = np.array(boot_data)
    else:
        boot_scores = np.array(results["cv_scores"])
    
    # Safe check for perm_scores
    perm_data = results.get("perm_scores")
    if perm_data is not None and len(perm_data) > 0:
        perm_scores = np.array(perm_data)
    else:
        perm_scores = np.array([])
    
    ci_low = results.get("ci_low", cv_mean)
    ci_high = results.get("ci_high", cv_mean)
    perm_pvalue = results.get("perm_pvalue")
    
    # Calculate n_classes for chance baseline
    n_classes = len(results.get("classes", []))
    if n_classes == 0: n_classes = len(args.domains)

    # Get Majority Baseline
    majority_baseline = results.get("majority_baseline", 1.0/n_classes)

    generate_cv_distribution_plot(
        observed_score=cv_mean,
        boot_scores=boot_scores,
        ci_low=ci_low,
        ci_high=ci_high,
        majority_baseline=majority_baseline,
        perm_scores=perm_scores,
        perm_pvalue=perm_pvalue,
        n_classes=n_classes,
        n_splits=args.n_splits,
        n_boot=args.n_boot,
        seed=args.seed,
        metric=args.stat,
        out_path=out_path
    )


def main() -> None:
    """
    Orchestrates the full domain signature classification pipeline with Caching.
    """
    parser = argparse.ArgumentParser(description="Run domain signature classification with bootstrap validation.")
    
    # Input Data Paths
    parser.add_argument("--semantic", type=Path, default=Path("output/semantic/semantic_overview_per_article.csv"))
    parser.add_argument("--bias", type=Path, default=Path("output/bias/bias_overview_per_article.csv"))
    parser.add_argument("--quote", type=Path, default=Path("output/semantic/quote_agent_overview_per_article.csv"))
    
    # Output Configuration
    parser.add_argument("--out-dir", type=Path, default=Path("output/bias"))
    parser.add_argument("--out-prefix", type=str, default="signature_classifier")
    
    # Experiment Configuration
    parser.add_argument("--domains", nargs="+", required=True)
    parser.add_argument("--stat", type=str, choices=["accuracy", "macro_f1"], default="accuracy")
    parser.add_argument("--seed", type=int, default=42)
    
    # Statistical Parameters
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--n-perm", type=int, default=500)

    # Control Flags
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing artifacts and re-run analysis.")
    
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the Artifact Path early so we can check it
    artifact_path = args.out_dir / f"{args.out_prefix}_artifacts.json"

    stats_results = {}

    # --- CHECK CACHE ---
    # If file exists AND we didn't ask to force-recompute, load it.
    if artifact_path.exists() and not args.force:
        print(f"[INFO] Artifacts found at: {artifact_path}")
        print(f"[INFO] Skipping data loading and model training. Loading cached results...")
        stats_results = load_model_artifacts(artifact_path)
        print(f"[SUCCESS] Cache loaded. Proceeding to visualization.")
        
    else:
        # --- NO CACHE or FORCED: RUN EVERYTHING ---
        if args.force and artifact_path.exists():
            print(f"[INFO] --force flag detected. Overwriting existing artifacts.")

        if args.debug:
            print(f"[DEBUG] Arguments: {vars(args)}")

        # 1. DATA INGESTION
        print(f"[STEP 1/5] Loading data for domains: {args.domains}")
        df_raw = load_and_merge_datasets(args.semantic, args.bias, args.quote, args.debug)
        
        if args.debug:
            print(f"[DEBUG] Raw merged DataFrame shape: {df_raw.shape}")

        X, y, feature_names = build_feature_matrix(df_raw, args.domains)
        
        # Capture IDs immediately to ensure alignment
        # We replicate the exact filtering logic used inside build_feature_matrix
        # so we have the IDs corresponding exactly to row 0, 1, 2... of X.
        # This prevents misalignment if the dataframe order shifts later.
        target_ids = df_raw[df_raw["domain"].isin(args.domains)]["article_id"].values
        # -------------------------------------------------------------
        
        print(f"\n[SUCCESS] Matrix Built (N={X.shape[0]}, D={X.shape[1]})")

        # Feature Audit
        sem_cols = [f for f in feature_names if f.startswith("sem__")]
        bias_cols = [f for f in feature_names if f.startswith("bias__")]
        quote_cols = [f for f in feature_names if f.startswith("quote__")]
        print(f"   > Feature Composition:\n     - Semantic: {len(sem_cols)}\n     - Bias:     {len(bias_cols)}\n     - Quote:    {len(quote_cols)}")

        if args.debug:
            import json
            print(f"\n[DEBUG] Full Feature List:\n{json.dumps(feature_names, indent=2)}")

        # 2. MODELING
        print(f"[STEP 2/5] Running Model (CV={args.n_splits}, Boot={args.n_boot}, Perm={args.n_perm})...")
        pipeline = build_pipeline(seed=args.seed)
        
        stats_results = run_statistical_analysis(
            pipeline=pipeline,
            X=X, 
            y=y,
            feature_names=feature_names,
            n_splits=args.n_splits,
            n_boot=args.n_boot,
            n_perm=args.n_perm,
            metric=args.stat,
            seed=args.seed
        )

        # 3. SERIALIZATION
        print(f"[STEP 3/5] Serializing artifacts...")
        save_model_artifacts(args.out_dir, args.out_prefix, stats_results)
        
        results_csv_path = args.out_dir / f"{args.out_prefix}_results.csv"
        save_results_csv(stats_results, results_csv_path, args)

        # SAVE OOF PREDICTIONS ---
        if "cv_preds" in stats_results:
            print(f"   > Saving OOF Predictions...")
            
            # Using the SAFE target_ids captured earlier
            if len(target_ids) == len(stats_results["cv_preds"]):
                oof_df = pd.DataFrame({
                    "article_id": target_ids,
                    "true_domain": y, # y is already filtered and aligned
                    "pred_domain": stats_results["cv_preds"]
                })
                oof_path = args.out_dir / f"{args.out_prefix}_oof_predictions.csv"
                oof_df.to_csv(oof_path, index=False)
                print(f"   > OOF Predictions saved to: {oof_path}")
            else:
                print(f"[WARN] ID Mismatch: {len(target_ids)} vs {len(stats_results['cv_preds'])}. Skipping OOF CSV.")

    # --- DEBUG: INSPECT RESULTS (Works for both Cached and New runs) ---
    if args.debug:
        print(f"\n[DEBUG] --- RESULTS INSPECTION ---")
        cm = np.array(stats_results["confusion_matrix"])
        classes = stats_results["classes"]
        print(f"[DEBUG] Confusion Matrix:\n        {classes}\n{str(cm)}")
        
        if "perm_pvalue" in stats_results and stats_results["perm_pvalue"] is not None:
             print(f"[DEBUG] Permutation P-Value: {stats_results['perm_pvalue']:.4f}")

    # --- 4. VISUALIZATION ---
    print(f"[STEP 4/5] Generating Visualizations...")
    
    # Plot 1: Signatures
    generate_signature_plot(stats_results, args.out_dir / f"{args.out_prefix}_signatures.png")
    
    # Plot 2: Distributions (Call the wrapper)
    plot_distributions(
        results=stats_results,
        out_path=args.out_dir / f"{args.out_prefix}_bootstrap.png",
        args=args
    )
    
    # --- 5. LOGGING ---
    obs = stats_results.get("cv_mean", 0.0)
    lo = stats_results.get("ci_low", 0.0)
    hi = stats_results.get("ci_high", 0.0)
    perm_p = stats_results.get("perm_pvalue")
    
    print(f"\n[INFO] Domains: {args.domains} | n_features={len(stats_results.get('feature_names', []))}")
    print(f"[INFO] Observed OOF CV {args.stat}={obs:.4f} | CI[{lo:.4f}, {hi:.4f}]")
    
    if perm_p is not None:
        print(f"[INFO] Permutation p-value (perm >= observed) = {perm_p:.6f}")

    print(f"[DONE] All outputs saved to: {args.out_dir}")

if __name__ == "__main__":
    main()