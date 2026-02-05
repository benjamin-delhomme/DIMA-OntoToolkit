#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REQUIRED_COLS = {"domain", "variable", "n", "mean", "ci_lower", "ci_upper"}

def normalize_domain(x) -> str:
    s = str(x) if x is not None else ""
    s = s.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = s.split('/')[0]
    return s or "UNKNOWN"

def clean_label(source, var):
    """Refines technical names into intuitive descriptions."""
    v = str(var).lower()
    
    # Specific framing for PDC and Semantic segments
    if "pdc" in v:
        v = "Argument Structure: Total Density (P+D+C Sum)"
    elif "avg_premises" in v:
        v = "Argument Structure: Premise Density"
    elif "avg_developments" in v:
        v = "Argument Structure: Development Density"
    elif "avg_conclusions" in v:
        v = "Argument Structure: Conclusion Density"
    else:
        # General cleaning for everything else
        v = v.replace("_per_argument", "").replace("_per_quote", "")
        v = v.replace("avg_", "").replace("_refs_per_100_words", "")
        v = v.replace("__", ": ").replace("_", " ")
        v = re.sub(r'\s+', ' ', v).strip().title()
    
    source_prefix = "SEMANTIC" if source.lower() == "semantic" else "QUOTE"
    return f"{source_prefix}: {v}"

def load_bootstrap_csv(path_str, source: str) -> pd.DataFrame:
    if not path_str or not Path(path_str).exists():
        return pd.DataFrame()
    df = pd.read_csv(path_str)
    df["domain"] = df["domain"].apply(normalize_domain)
    df["source"] = source
    df = df[~df["variable"].str.startswith("attributions_")]
    for c in ["n", "mean", "ci_lower", "ci_upper"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Collapse duplicates: one row per domain/variable
    df = df.sort_values("n", ascending=False).groupby(["domain", "variable"], as_index=False).first()
    return df

def make_comparison_plot(results_df, output_png, domains, title_prefix):
    variables = sorted(results_df["variable"].unique().tolist())
    y_base = np.arange(len(variables))
    offsets = np.linspace(-0.35, 0.35, num=len(domains))
    
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = ['#1f77b4', '#d62728', '#2ca02c'] 

    # Determine n per domain for the legend labels
    n_by_domain = {}
    for dom in domains:
        ns = pd.to_numeric(results_df.loc[results_df["domain"] == dom, "n"], errors="coerce").dropna()
        n_by_domain[dom] = int(ns.max()) if len(ns) else 0

    for i, dom in enumerate(domains):
        subset = results_df[results_df["domain"] == dom].set_index("variable")
        means, lows, highs = [], [], []
        for v in variables:
            if v in subset.index:
                row = subset.loc[v]
                # Ensure we handle potential duplicate index issues
                m = row["mean"].iloc[0] if isinstance(row["mean"], pd.Series) else row["mean"]
                l = row["ci_lower"].iloc[0] if isinstance(row["ci_lower"], pd.Series) else row["ci_lower"]
                h = row["ci_upper"].iloc[0] if isinstance(row["ci_upper"], pd.Series) else row["ci_upper"]
                means.append(float(m))
                lows.append(float(l))
                highs.append(float(h))
            else:
                means.append(np.nan); lows.append(np.nan); highs.append(np.nan)
        
        means, lows, highs = np.array(means), np.array(lows), np.array(highs)
        xerr = [np.maximum(0, means - lows), np.maximum(0, highs - means)]
        
        legend_label = f"{dom} (n={n_by_domain[dom]})"
        ax.errorbar(means, y_base + offsets[i], xerr=xerr, fmt="o", 
                    capsize=5, label=legend_label, color=colors[i % len(colors)], markersize=8)

    ax.set_yticks(y_base)
    ax.set_yticklabels(variables, fontsize=11)
    ax.invert_yaxis()
    ax.set_title(title_prefix, fontsize=15, fontweight='bold', pad=20)
    ax.set_xlabel("Bootstrap Mean Value (95% CI)", fontsize=12)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    ax.legend(title="Domains (Sample Size)", frameon=True, loc='best', fontsize=11)
    
    plt.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quote-agent", help="Quote agent CSV")
    ap.add_argument("--semantic", help="Semantic CSV")
    ap.add_argument("--bias", help="Bias CSV")
    ap.add_argument("--domains", nargs="+", default=["kyivpost.com", "sputnikglobe.com", "bbc.co.uk"])
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--output-prefix", default="top10_comparison_final")
    args = ap.parse_args()

    out_dir = Path("output/semantic")
    out_dir.mkdir(parents=True, exist_ok=True)

    domains = [normalize_domain(d) for d in args.domains]
    
    dfs = []
    if args.quote_agent: dfs.append(load_bootstrap_csv(args.quote_agent, "QUOTE"))
    if args.semantic:    dfs.append(load_bootstrap_csv(args.semantic, "SEMANTIC"))
    if args.bias:        dfs.append(load_bootstrap_csv(args.bias, "BIAS"))
    
    if not dfs:
        print("[ERR] No input files found.")
        return

    combined = pd.concat(dfs, ignore_index=True)
    df = combined[combined["domain"].isin(domains)].copy()

    # Calculate Relevance Score
    scored_vars = []
    for (source, var), g in df.groupby(["source", "variable"]):
        if g["domain"].nunique() < len(domains): continue
        relevance_score = g["mean"].max() - g["mean"].min()
        scored_vars.append({"source": source, "variable": var, "score": relevance_score})

    if not scored_vars:
        print(f"[WARN] No variables found present in all domains.")
        return

    # Select Top N
    top_df = pd.DataFrame(scored_vars).sort_values("score", ascending=False).head(args.top_n)
    final_df = df.merge(top_df[['source', 'variable']], on=['source', 'variable'])
    
    # APPLY CLEAN LABELS
    final_df["variable"] = final_df.apply(lambda r: clean_label(r["source"], r["variable"]), axis=1)
    
    # Deduplicate after cleaning to ensure the plot doesn't crash on array shape
    final_df = final_df.groupby(["domain", "variable"], as_index=False).first()
    
    out_csv = out_dir / f"{args.output_prefix}.csv"
    out_png = out_dir / f"{args.output_prefix}.png"
    
    final_df.to_csv(out_csv, index=False)
    make_comparison_plot(final_df, out_png, domains, f"Top {args.top_n} Differences Among Domains")

    print(f"[OK] Saved CSV: {out_csv}")
    print(f"[OK] Saved Plot: {out_png}")

if __name__ == "__main__":
    main()
