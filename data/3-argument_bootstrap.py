#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# BOOTSTRAP FUNCTION
def bootstrap_mean_ci(values, n_boot=5000, alpha=0.05, random_state=42):
    rng = np.random.default_rng(random_state)
    data = np.asarray(values, dtype=float)
    data = data[~np.isnan(data)]
    n = data.size

    if n == 0:
        return {"mean": np.nan, "ci_lower": np.nan, "ci_upper": np.nan, "n": 0}

    samples = rng.choice(data, size=(n_boot, n), replace=True)
    means = samples.mean(axis=1)
    lo, up = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"mean": float(data.mean()), "ci_lower": float(lo), "ci_upper": float(up), "n": int(n)}


def normalize_domain(x) -> str:
    s = str(x) if x is not None else ""
    s = s.strip().lower()
    s = re.sub(r"^www\.", "", s)
    return s or "UNKNOWN"

# PLOT
def make_comparison_plot(results_df, output_png, domains, title_prefix):
    variables = list(dict.fromkeys(results_df["variable"].tolist()))
    y_base = np.arange(len(variables))
    offsets = np.linspace(-0.18, 0.18, num=len(domains)) if len(domains) > 1 else [0.0]

    lookup = {(r["domain"], r["variable"]): r for _, r in results_df.iterrows()}

    # one n per domain for title (max across variables)
    n_by_domain = {}
    for dom in domains:
        ns = pd.to_numeric(results_df.loc[results_df["domain"] == dom, "n"], errors="coerce").dropna()
        n_by_domain[dom] = int(ns.max()) if len(ns) else 0

    title = f"{title_prefix} — {domains[0]} (n={n_by_domain[domains[0]]}), {domains[1]} (n={n_by_domain[domains[1]]})"

    fig, ax = plt.subplots(figsize=(13, max(4, 0.6 * len(variables))))

    for i, dom in enumerate(domains):
        ys = y_base + offsets[i]
        means, lo, up = [], [], []

        for var in variables:
            row = lookup.get((dom, var))
            if row is None:
                means.append(np.nan); lo.append(np.nan); up.append(np.nan)
            else:
                means.append(float(row["mean"]))
                lo.append(float(row["ci_lower"]))
                up.append(float(row["ci_upper"]))

        means = np.asarray(means, dtype=float)
        lo = np.asarray(lo, dtype=float)
        up = np.asarray(up, dtype=float)

        xerr = np.vstack([means - lo, up - means])

        ax.errorbar(means, ys, xerr=xerr, fmt="o", capsize=5, linewidth=1, label=dom)

    ax.set_yticks(y_base)
    ax.set_yticklabels(variables)
    ax.invert_yaxis()
    ax.set_xlabel("Mean (per argument)")
    ax.set_title(title)
    ax.legend(loc="upper right")

    plt.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to semantic_overview_per_article.csv")
    ap.add_argument(
        "--domains",
        nargs='+',
        default=["kyivpost", "sputnikglobe", "bbc.co.uk"],
        help="Domains to compare (default: kyivpost sputnikglobe bbc.co.uk)",
    )
    ap.add_argument("--n-boot", type=int, default=5000)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--output-prefix", default="semantic_bootstrap_pdc_per_argument")
    ap.add_argument(
        "--variables",
        nargs="*",
        default=None,
        help="Optional explicit list of columns (defaults to premise/dev/conclusion per argument).",
    )
    args = ap.parse_args()

    input_path = Path(args.input)
    df = pd.read_csv(input_path, dtype={"article_id": str})

    if "domain" not in df.columns:
        raise SystemExit("[ERR] Input CSV must contain a 'domain' column.")

    df["domain"] = df["domain"].apply(normalize_domain)
    domains = [normalize_domain(d) for d in args.domains]

    df = df[df["domain"].isin(domains)].copy()
    if df.empty:
        raise SystemExit(f"[ERR] No rows found for domains={domains}. Check your domain strings in the CSV.")

    # Default set: premise/development/conclusion per argument (plus total P+D+C per argument)
    selected_cols = args.variables or [
        "avg_premises_per_argument",
        "avg_developments_per_argument",
        "avg_conclusions_per_argument",
        "avg_pdc_per_argument",
    ]

    # Validate presence
    selected_cols = [c for c in selected_cols if c in df.columns]
    if not selected_cols:
        raise SystemExit("[ERR] None of the requested per-argument columns exist in the input CSV.")

    # Bootstrap per domain per variable
    results = []
    for dom in domains:
        ddf = df[df["domain"] == dom]
        for col in selected_cols:
            stats = bootstrap_mean_ci(
                pd.to_numeric(ddf[col], errors="coerce").values,
                n_boot=args.n_boot,
                alpha=args.alpha,
                random_state=42,
            )
            results.append(
                {
                    "domain": dom,
                    "variable": col,
                    "n": stats["n"],
                    "mean": stats["mean"],
                    "ci_lower": stats["ci_lower"],
                    "ci_upper": stats["ci_upper"],
                }
            )

    results_df = pd.DataFrame(results).sort_values(["variable", "domain"])

    out_dir = input_path.parent
    out_csv = out_dir / f"{args.output_prefix}.csv"
    out_png = out_dir / f"{args.output_prefix}.png"

    results_df.to_csv(out_csv, index=False)

    make_comparison_plot(
        results_df,
        out_png,
        domains=domains,
        title_prefix="Premise / development / conclusion per argument (bootstrap mean ± 95% CI)",
    )

    print(f"[OK] Wrote: {out_csv}")
    print(f"[OK] Wrote: {out_png}")


if __name__ == "__main__":
    main()

