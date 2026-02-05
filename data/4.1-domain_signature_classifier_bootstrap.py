#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path
import json
import re
from typing import Dict, List, Tuple

import numpy as np
import textwrap
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix


# -----------------------
# Utilities
# -----------------------
def norm_domain(x: object) -> str:
    s = str(x) if x is not None else ""
    s = s.strip().lower()
    s = re.sub(r"^www\.", "", s)
    return s


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def build_model(seed: int) -> Pipeline:
    """
    Build a logistic regression pipeline compatible with older/newer sklearn.
    """
    base_kwargs = dict(
        solver="lbfgs",
        max_iter=5000,
        random_state=seed,
    )
    try:
        clf = LogisticRegression(multi_class="multinomial", **base_kwargs)
    except TypeError:
        clf = LogisticRegression(**base_kwargs)

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler(with_mean=True, with_std=True)),
            ("clf", clf),
        ]
    )


def stratified_resample_indices(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Resample indices within each class to preserve class sizes."""
    out: List[int] = []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        if idx.size == 0:
            continue
        out.extend(rng.choice(idx, size=idx.size, replace=True).tolist())
    return np.array(out, dtype=int)


def score_from_labels(y_true: np.ndarray, y_pred: np.ndarray, stat: str) -> float:
    if stat == "accuracy":
        return float(accuracy_score(y_true, y_pred))
    if stat == "macro_f1":
        return float(f1_score(y_true, y_pred, average="macro"))
    raise ValueError(f"Unsupported stat: {stat}")


# Data loading / feature assembly
def load_and_merge(semantic_csv: Path, bias_csv: Path, quote_csv: Path) -> pd.DataFrame:
    if not semantic_csv.exists():
        raise SystemExit(f"[ERR] Missing: {semantic_csv}")
    if not bias_csv.exists():
        raise SystemExit(f"[ERR] Missing: {bias_csv}")
    if not quote_csv.exists():
        raise SystemExit(f"[ERR] Missing: {quote_csv}")

    sem = pd.read_csv(semantic_csv, dtype={"article_id": str})
    bias = pd.read_csv(bias_csv, dtype={"article_id": str})
    q = pd.read_csv(quote_csv, dtype={"article_id": str})

    for df in (sem, bias, q):
        if "domain" in df.columns:
            df["domain"] = df["domain"].apply(norm_domain)

    # Merge backbone = semantic (it must contain total_arguments)
    df = sem.merge(bias, on="article_id", how="left", suffixes=("", "__bias"))
    df = df.merge(q, on="article_id", how="left", suffixes=("", "__quote"))

    # Ensure a usable domain column
    if "domain" not in df.columns or df["domain"].isna().all():
        for cand in ("domain__bias", "domain__quote"):
            if cand in df.columns:
                df["domain"] = df[cand]
                break
    if "domain" not in df.columns:
        raise SystemExit("[ERR] No domain column after merging.")

    df["domain"] = df["domain"].apply(norm_domain)
    return df


def select_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    feats: Dict[str, pd.Series] = {}

    # 1. Semantic features (if present)
    semantic_cols = [
        "avg_premises_per_argument",
        "avg_developments_per_argument",
        "avg_conclusions_per_argument",
        "avg_pdc_per_argument",
        "premise_ratio",
        "development_ratio",
        "conclusion_ratio",
        "arguments_per_100",
    ]
    for col in semantic_cols:
        if col in df.columns:
            feats[f"sem__{col}"] = pd.to_numeric(df[col], errors="coerce")

    if "total_arguments" not in df.columns:
        raise SystemExit("[ERR] semantic_overview_per_article.csv must include 'total_arguments'.")

    denom = pd.to_numeric(df["total_arguments"], errors="coerce").where(lambda s: s > 0, np.nan)

    # 2. Bias per argument derived from COUNT columns in bias_overview_per_article.csv
    bias_exclude = {
        "article_id", "headline", "viewpoint_country", "domain", "word_count",
        "overall_total", "overall_per_100",
    }

    for col in df.columns:
        # STRICT FILTER: If it contains 'attribution', SKIP IT regardless of where it came from
        if "attribution" in col.lower():
            continue

        if col in bias_exclude:
            continue
        if col.endswith("_per_100"):
            continue
        if col.endswith("__bias") or col.endswith("__quote"):
            continue
        if col in {"total_arguments", "premises", "developments", "conclusions"}:
            continue
        if col.startswith("avg_") or col.endswith("_ratio") or col.endswith("_per_argument"):
            continue

        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() == 0:
            continue

        feats[f"bias__{col}_per_argument"] = s / denom

    # 3. Quote-agent: include numeric *_per_argument columns
    for col in df.columns:
        # STRICT FILTER: Strict removal of 'attributions' again
        if "attribution" in col.lower():
            continue

        # Must be a per-argument numeric column
        if not col.endswith("_per_argument"):
            continue
        
        # Skip averages and overall summaries
        if col.startswith("avg_") or col == "overall_per_argument":
            continue

        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() == 0:
            continue
        feats[f"quote__{col}"] = s

    Xdf = pd.DataFrame(feats)
    return Xdf, list(Xdf.columns)


def plot_top_features(pipeline, Xdf, y, out_dir, n_top=10):
    print(f"[INFO] Generating clean signature plot for publication...")

    # 1. Fit the model to get the final coefficients
    pipeline.fit(Xdf.to_numpy(), y)
    model = pipeline.named_steps['clf']
    feature_names = Xdf.columns
    classes = model.classes_
    coefficients = model.coef_

    fig_height = max(10, n_top * 1.4)
    fig, axes = plt.subplots(1, len(classes), figsize=(32, fig_height))

    if len(classes) == 1: axes = [axes]

    for i, class_label in enumerate(classes):
        coef_df = pd.DataFrame({'Feature': feature_names, 'Coef': coefficients[i]})
        coef_df['abs'] = coef_df['Coef'].abs()

        top_feats = coef_df.sort_values(by='abs', ascending=False).head(n_top)
        top_feats = top_feats.sort_values(by='Coef')

        # --- THE CLEANING LOOP IS HERE (RESTORED TO ORIGINAL) ---
        clean_labels = []
        for l in top_feats['Feature']:
            # A. Remove technical prefixes
            display_name = l.replace('bias__', '').replace('semantic__', '').replace('quote__', '').replace('sem__', '')

            # B. Remove common suffixes and underscores
            display_name = display_name.replace('_per_argument', '').replace('_', ' ')

            # C. Specific fix for the density feature (Per 100 words/sentences)
            if 'arguments per 100' in display_name.lower():
                display_name = 'Argument density'

            # D. Final formatting
            display_name = display_name.strip().capitalize()
            clean_labels.append(textwrap.fill(display_name, width=22))
        # ----------------------------------

        ax = axes[i]
        colors = ['#d6604d' if c < 0 else '#4393c3' for c in top_feats['Coef']]

        # Plot the thick bars (the 'boxes')
        ax.barh(clean_labels, top_feats['Coef'], color=colors, edgecolor='black', height=0.7)

        ax.set_title(f"OUTLET: {class_label.upper()}", fontsize=26, fontweight='bold', pad=35)
        ax.axvline(0, color='black', linewidth=2)
        ax.set_xlabel("Feature Influence (Beta Coefficient)", fontsize=18, labelpad=15)

        ax.tick_params(axis='y', labelsize=15, pad=10)
        ax.grid(axis='x', linestyle=':', alpha=0.6)

        # Ensure the 'box' stays wide by setting consistent x-limits
        limit = max(abs(top_feats['Coef'])) * 1.1
        ax.set_xlim(-limit, limit)

    plt.subplots_adjust(left=0.22, right=0.97, wspace=0.7, top=0.88, bottom=0.1)

    feat_path = out_dir / "signature_feature_importance_FINAL.png"
    fig.savefig(feat_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] Clean publication plot saved to: {feat_path}")


# -----------------------
# Main
# -----------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semantic", default="output/semantic/semantic_overview_per_article.csv", help="Semantic overview CSV.")
    ap.add_argument("--bias", default="output/bias/bias_overview_per_article.csv", help="Bias overview CSV (counts + per_100).")
    ap.add_argument("--quote", default="output/semantic/quote_agent_overview_per_article.csv", help="Quote-agent overview CSV.")
    ap.add_argument("--domains", nargs="+", required=True, help="Domains to include (2+).")

    ap.add_argument("--out-dir", default="output/bias", help="Output directory.")
    ap.add_argument("--out-prefix", default="signature_classifier", help="Output file prefix.")

    ap.add_argument("--stat", choices=["accuracy", "macro_f1"], default="accuracy", help="Performance statistic.")
    ap.add_argument("--n-splits", type=int, default=5, help="Number of CV folds.")
    ap.add_argument("--seed", type=int, default=42, help="Random seed.")

    ap.add_argument("--n-boot", type=int, default=2000, help="Bootstrap resamples for CI.")
    ap.add_argument("--alpha", type=float, default=0.05, help="Alpha for CI interval.")
    ap.add_argument("--n-perm", type=int, default=500, help="Permutation runs (0 disables).")

    args = ap.parse_args()

    semantic_csv = Path(args.semantic)
    bias_csv = Path(args.bias)
    quote_csv = Path(args.quote)

    out_dir = Path(args.out_dir)
    safe_mkdir(out_dir)

    df = load_and_merge(semantic_csv, bias_csv, quote_csv)

    domains = [norm_domain(d) for d in args.domains]
    if len(domains) < 2:
        raise SystemExit("[ERR] Provide at least 2 domains.")

    df = df[df["domain"].isin(domains)].copy()
    if df.empty:
        raise SystemExit(f"[ERR] No rows after filtering to domains={domains}")
    
    # Feature selection (Includes the strict attribution filter)
    Xdf, feature_names = select_features(df)
    y = df["domain"].astype(str).apply(norm_domain).to_numpy()
    X = Xdf.to_numpy(dtype=float)

    n_per_domain = {d: int((y == d).sum()) for d in domains}
    n_total = int(len(y))

    if any(n_per_domain[d] < args.n_splits for d in domains):
        raise SystemExit("[ERR] A domain has fewer samples than n_splits; reduce --n-splits or add data.")

    model = build_model(seed=args.seed)
    cv = StratifiedKFold(n_splits=args.n_splits, shuffle=True, random_state=args.seed)

    # Observed out-of-fold predictions
    y_pred_oof = cross_val_predict(model, X, y, cv=cv)
    obs = score_from_labels(y, y_pred_oof, args.stat)

    labels_sorted = sorted(list({str(v) for v in y}))
    cm = confusion_matrix(y, y_pred_oof, labels=labels_sorted)

    # Bootstrap CI by resampling ARTICLE indices from OOF predictions
    rng = np.random.default_rng(args.seed)
    boot_scores = np.empty(args.n_boot, dtype=float)
    for b in range(args.n_boot):
        idx = stratified_resample_indices(y, rng)
        boot_scores[b] = score_from_labels(y[idx], y_pred_oof[idx], args.stat)

    lo = float(np.percentile(boot_scores, 100.0 * args.alpha / 2.0))
    hi = float(np.percentile(boot_scores, 100.0 * (1.0 - args.alpha / 2.0)))
    boot_mean = float(np.mean(boot_scores))
    boot_std = float(np.std(boot_scores, ddof=1)) if boot_scores.size > 1 else 0.0

    # Permutation test
    perm_scores = []
    perm_p = None
    perm_mean = None
    perm_std = None
    if args.n_perm and args.n_perm > 0:
        for _ in range(args.n_perm):
            y_perm = y.copy()
            rng.shuffle(y_perm)
            y_pred_perm = cross_val_predict(model, X, y_perm, cv=cv)
            perm_scores.append(score_from_labels(y_perm, y_pred_perm, args.stat))
        perm_scores = np.asarray(perm_scores, dtype=float)
        perm_mean = float(np.mean(perm_scores))
        perm_std = float(np.std(perm_scores, ddof=1)) if perm_scores.size > 1 else 0.0
        perm_p = float((np.sum(perm_scores >= obs) + 1.0) / (perm_scores.size + 1.0))

    # Write results summary
    results_path = out_dir / f"{args.out_prefix}_results.csv"
    summary = {
        "stat": args.stat,
        "obs_cv": obs,
        "ci95_low": lo,
        "ci95_high": hi,
        "boot_mean": boot_mean,
        "boot_std": boot_std,
        "n_boot": int(args.n_boot),
        "alpha": float(args.alpha),
        "seed": int(args.seed),
        "n_splits": int(args.n_splits),
        "n_total": n_total,
        "domains": json.dumps(domains),
        "n_per_domain": json.dumps(n_per_domain),
        "n_features": int(len(feature_names)),
        "perm_n": int(args.n_perm),
        "perm_mean": perm_mean,
        "perm_std": perm_std,
        "perm_pvalue_ge_obs": perm_p,
    }
    pd.DataFrame([summary]).to_csv(results_path, index=False)

    # Write samples
    samples_path = out_dir / f"{args.out_prefix}_samples.csv"
    rows = [{"kind": "bootstrap", "iteration": i, "score": float(s)} for i, s in enumerate(boot_scores)]
    if args.n_perm and args.n_perm > 0:
        rows += [{"kind": "permutation", "iteration": i, "score": float(s)} for i, s in enumerate(perm_scores)]
    pd.DataFrame(rows).to_csv(samples_path, index=False)

    # Confusion matrix
    cm_path = out_dir / f"{args.out_prefix}_confusion_matrix.csv"
    cm_df = pd.DataFrame(cm, index=[f"true__{l}" for l in labels_sorted], columns=[f"pred__{l}" for l in labels_sorted])
    cm_df.to_csv(cm_path, index=True)

    plot_top_features(model, Xdf, y, out_dir=out_dir, n_top=10)

    # -----------------------
    # Plot (publication-friendly) - ORIGINAL STYLING RESTORED
    # -----------------------
    png_path = out_dir / f"{args.out_prefix}_bootstrap.png"
    fig, ax = plt.subplots(figsize=(10.8, 6.2))

    ax.hist(boot_scores, bins=30, alpha=0.70, label="Bootstrap (resample articles from OOF predictions)")
    if args.n_perm and args.n_perm > 0:
        ax.hist(perm_scores, bins=30, alpha=0.45, label="Permutation null (label shuffles)")

    ax.axvline(obs, linewidth=2, label="Observed OOF CV score")
    ax.axvline(lo, linestyle="--", linewidth=1, label="Bootstrap CI low")
    ax.axvline(hi, linestyle="--", linewidth=1, label="Bootstrap CI high")

    maj = max(n_per_domain.values()) / float(n_total)
    chance_uniform = 1.0 / float(len(domains))

    # Distinguish the two baselines clearly
    ax.axvline(chance_uniform, linestyle=":", linewidth=2, label=f"Uniform chance (1/K) = {chance_uniform:.3f}")
    ax.axvline(maj, linestyle="-.", linewidth=2, label=f"Majority-class baseline = {maj:.3f}")

    conf = (1.0 - float(args.alpha)) * 100.0
    title = (
        "Domain predictability from semantic + bias + quote features\n"
        f"OOF {args.n_splits}-fold CV {args.stat}; bootstrap CI (conf={conf:.1f}, B={args.n_boot}, seed={args.seed})"
    )
    if args.n_perm and args.n_perm > 0:
        title += f"\nPermutation p-value (perm >= observed) = {perm_p:.4f}"
    ax.set_title(title)

    ax.set_xlabel(f"Cross-validated {args.stat}")
    ax.set_ylabel("Frequency")

    ax.legend(loc="upper left", fontsize=9, frameon=False, ncol=1)
    fig.tight_layout()
    fig.savefig(png_path, dpi=260)
    plt.close(fig)

    print(f"[OK] Wrote: {results_path}")
    print(f"[OK] Wrote: {samples_path}")
    print(f"[OK] Wrote: {cm_path}")
    print(f"[OK] Wrote: {png_path}")
    print(f"[INFO] Domains: {domains} | n_per_domain={n_per_domain} | n_features={len(feature_names)}")
    print(f"[INFO] Observed OOF CV {args.stat}={obs:.4f} | CI[{lo:.4f}, {hi:.4f}]")
    if args.n_perm and args.n_perm > 0:
        print(f"[INFO] Permutation p-value (perm >= observed) = {perm_p:.6f}")


if __name__ == "__main__":
    main()
