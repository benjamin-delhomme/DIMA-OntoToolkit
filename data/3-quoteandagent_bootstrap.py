#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

def normalize_domain(x) -> str:
    s = str(x) if x is not None else ""
    s = s.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.rstrip("/")
    return s or "UNKNOWN"

def bootstrap_mean_ci(values, n_boot=5000, alpha=0.05, random_state=42):
    rng = np.random.default_rng(random_state)
    data = np.asarray(values, dtype=float)
    data = data[~np.isnan(data)]
    n = data.size

    if n == 0:
        return {"n": 0, "mean": np.nan, "ci_lower": np.nan, "ci_upper": np.nan}

    # Vectorized resampling (Much faster than the loop)
    samples = rng.choice(data, size=(n_boot, n), replace=True)
    means = samples.mean(axis=1)
    
    # Percentile method
    lo, up = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    
    return {"n": int(n), "mean": float(data.mean()), "ci_lower": float(lo), "ci_upper": float(up)}

def make_comparison_plot(results_df, output_png, domains, title_prefix):
    variables = sorted(list(results_df["variable"].unique()))
    y_base = np.arange(len(variables))
    offsets = np.linspace(-0.3, 0.3, num=len(domains))
    
    fig, ax = plt.subplots(figsize=(12, max(5, 0.6 * len(variables))))
    
    for i, dom in enumerate(domains):
        subset = results_df[results_df["domain"] == dom].set_index("variable")
        # Use simple list comprehensions to handle missing data safely
        means = [subset.loc[v, "mean"] if v in subset.index else np.nan for v in variables]
        lows = [subset.loc[v, "ci_lower"] if v in subset.index else np.nan for v in variables]
        highs = [subset.loc[v, "ci_upper"] if v in subset.index else np.nan for v in variables]
        
        means, lows, highs = np.array(means), np.array(lows), np.array(highs)
        
        # Calculate errors for errorbar (distance from mean)
        xerr = [np.maximum(0, means - lows), np.maximum(0, highs - means)]
        
        ax.errorbar(means, y_base + offsets[i], xerr=xerr, fmt="o", capsize=3, label=dom)

    ax.set_yticks(y_base)
    ax.set_yticklabels(variables)
    ax.invert_yaxis()
    ax.set_title(title_prefix)
    ax.legend()
    plt.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to quote_agent_overview_per_article.csv")
    ap.add_argument("--domains", nargs="+", default=["kyivpost.com", "sputnikglobe.com", "bbc.co.uk"])
    ap.add_argument("--mode", choices=["argument", "quote", "both"], default="both")
    ap.add_argument("--n-boot", type=int, default=5000)
    ap.add_argument("--output-prefix", default="quote_agent_bootstrap_arg_quote")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    df["domain"] = df["domain"].apply(normalize_domain)
    
    target_domains = sorted(list(set(normalize_domain(d) for d in args.domains)))
    df = df[df["domain"].isin(target_domains)].copy()

    suffixes = []
    if args.mode in ("argument", "both"): suffixes.append("_per_argument")
    if args.mode in ("quote", "both"):    suffixes.append("_per_quote")

    selected_cols = []
    for c in df.columns:
        if any(c.endswith(s) for s in suffixes) and not c.startswith("attributions_"):
            if c not in selected_cols:
                selected_cols.append(c)

    if not selected_cols:
        print("[ERR] No columns found matching criteria.")
        return

    results = []
    for dom in target_domains:
        ddf = df[df["domain"] == dom]
        for col in selected_cols:
            stats = bootstrap_mean_ci(
                ddf[col].dropna().values, 
                n_boot=args.n_boot, 
                random_state=42
            )
            results.append({
                "domain": dom,
                "variable": col,
                "n": stats["n"],
                "mean": stats["mean"],
                "ci_lower": stats["ci_lower"],
                "ci_upper": stats["ci_upper"]
            })

    results_df = pd.DataFrame(results)
    
    out_dir = Path(args.input).parent
    out_csv = out_dir / f"{args.output_prefix}.csv"
    results_df.to_csv(out_csv, index=False)
    
    make_comparison_plot(results_df, out_dir / f"{args.output_prefix}.png", target_domains, "Quote & Agent Metrics")
    print(f"[OK] Wrote results to {out_csv}")

if __name__ == "__main__":
    main()