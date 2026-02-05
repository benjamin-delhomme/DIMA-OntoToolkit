#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# BOOTSTRAP FUNCTION
def bootstrap_mean_ci(values, n_boot=5000, alpha=0.05, random_state=42):
    """
    Nonparametric bootstrap CI for the mean (NaNs dropped).
    Returns dict: mean, ci_lower, ci_upper, n
    """
    rng = np.random.default_rng(random_state)
    data = np.asarray(values, dtype=float)
    data = data[~np.isnan(data)]
    n = data.size

    if n == 0:
        return {"mean": np.nan, "ci_lower": np.nan, "ci_upper": np.nan, "n": 0}

    samples = rng.choice(data, size=(n_boot, n), replace=True)
    means = samples.mean(axis=1)

    lower, upper = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])

    return {"mean": data.mean(), "ci_lower": lower, "ci_upper": upper, "n": n}


# PLOT FUNCTION
def make_comparison_plot(results_df, output_png, domains, title_prefix="Bootstrap 95% CI by domain"):
    """
    Horizontal error-bar plot with two domains per variable.
    """
    # Keep variable order as in results_df appearance (or sort if you want)
    variables = list(dict.fromkeys(results_df["variable"].tolist()))

    # Build lookup: (domain, variable) -> stats row
    lookup = {}
    for _, row in results_df.iterrows():
        lookup[(row["domain"], row["variable"])] = row

    # Positions: one row per variable, with small vertical offset per domain
    y_base = np.arange(len(variables))
    offsets = np.linspace(-0.18, 0.18, num=len(domains)) if len(domains) > 1 else [0.0]

    fig, ax = plt.subplots(figsize=(12, max(4, 0.6 * len(variables))))

    # Plot each domain as its own series (matplotlib will auto-color)
    for d_i, dom in enumerate(domains):
        ys = y_base + offsets[d_i]

        means = []
        lo = []
        up = []
        ns = []

        for var in variables:
            row = lookup.get((dom, var))
            if row is None:
                means.append(np.nan)
                lo.append(np.nan)
                up.append(np.nan)
                ns.append(0)
            else:
                means.append(float(row["mean"]))
                lo.append(float(row["ci_lower"]))
                up.append(float(row["ci_upper"]))
                ns.append(int(row["n"]))

        means = np.asarray(means, dtype=float)
        lo = np.asarray(lo, dtype=float)
        up = np.asarray(up, dtype=float)

        # asymmetric xerr
        xerr = np.vstack([means - lo, up - means])

        ax.errorbar(
            means,
            ys,
            xerr=xerr,
            fmt="o",
            capsize=5,
            linewidth=1,
            label=f"{dom}",
        )

    ax.set_yticks(y_base)
    ax.set_yticklabels([v.replace("_per_100", "") for v in variables])
    ax.invert_yaxis()
    ax.set_xlabel("Mean value (per 100)")
    ax.set_title(f"{title_prefix}\n(Mean ± 95% Confidence Interval)")
    ax.legend(loc="best")

    plt.tight_layout()
    fig.savefig(output_png, dpi=200)
    plt.close(fig)


# MAIN
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Path to bias_overview_per_article.csv")
    parser.add_argument(
        "--domains",
        nargs='+', 
        default=["kyivpost", "sputnikglobe", "bbc.co.uk"],
        help="Domains to compare (default: kyivpost sputnikglobe bbc.co.uk)",
    )
    parser.add_argument("--output-prefix", type=str, default="bootstrap_ci_domains_selected")
    parser.add_argument("--n-boot", type=int, default=5000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--variables",
        nargs="*",
        default=None,
        help="Optional list of *_per_100 columns to analyze. If omitted, uses a default list.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    df = pd.read_csv(input_path)

    if "domain" not in df.columns:
        raise SystemExit("[ERR] Input CSV must have a 'domain' column.")

    # normalize domains similarly to your other scripts
    df["domain"] = (
        df["domain"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"^www\.", "", regex=True)
    )

    domains = [d.strip().lower().replace("www.", "") for d in args.domains]
    df = df[df["domain"].isin(domains)].copy()
    if df.empty:
        raise SystemExit(f"[ERR] No rows found for domains={domains}. Check the domain values in the CSV.")

    # Default variables (same as your original selection)
    selected_cols = args.variables or [
        #"overall_per_100",
        "BizarrenessEffect_per_100",
        "ContrastEffect_per_100",
        "DistinctionBias_per_100",
        "NegativityBias_per_100",
        "OmissionBias_per_100",
        "VonRestorffEffect_per_100",
    ]

    # Compute bootstrap per domain per variable
    results = []
    for dom in domains:
        ddf = df[df["domain"] == dom]
        for col in selected_cols:
            if col not in ddf.columns:
                print(f"WARNING: Column not found for domain={dom}: {col}")
                continue

            stats = bootstrap_mean_ci(
                ddf[col].values,
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

    # Save table (long format)
    output_csv = input_path.parent / f"{args.output_prefix}.csv"
    results_df.to_csv(output_csv, index=False)

    # Save plot
    output_png = input_path.parent / f"{args.output_prefix}.png"
    make_comparison_plot(results_df, output_png, domains=domains, title_prefix="Bias (per 100) — Kyivpost vs Sputnik")

    print(f"Saved results to: {output_csv}")
    print(f"Saved plot to:    {output_png}")


if __name__ == "__main__":
    main()

