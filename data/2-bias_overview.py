#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Dict, Any, Optional, Tuple, List

import pandas as pd


# paths
BASE_DIR = Path(__file__).resolve().parent

SEM_OUT_DIR = BASE_DIR / "output" / "semantic"
OVERVIEW_CSV = SEM_OUT_DIR / "semantic_overview_per_article.csv"

BIAS_JSON_DIR = BASE_DIR.parent / "output" / "bias_analysis"  # as requested: ../output/bias_analysis
BIAS_OUT_DIR = BASE_DIR / "output" / "bias"

BIAS_GLOB = "article_biases_*.json"
ID_RE = re.compile(r"article_biases_(?P<id>[A-Za-z0-9]+)\.json$", re.IGNORECASE)


def read_overview() -> pd.DataFrame:
    if not OVERVIEW_CSV.exists():
        raise SystemExit(f"[ERR] Missing overview file: {OVERVIEW_CSV}")

    df = pd.read_csv(OVERVIEW_CSV, dtype={"article_id": str})
    need = ["article_id", "headline", "viewpoint_country", "domain", "word_count"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise SystemExit(f"[ERR] {OVERVIEW_CSV} missing columns: {missing}")

    df["domain"] = (
        df["domain"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"^www\.", "", regex=True)
    )
    return df[need].copy()


def find_bias_files() -> List[Path]:
    if not BIAS_JSON_DIR.exists():
        raise SystemExit(f"[ERR] Bias dir does not exist: {BIAS_JSON_DIR}")
    return sorted(BIAS_JSON_DIR.glob(BIAS_GLOB))


def _count_bias_types_from_obj(obj: Any, counts: Dict[str, int]) -> None:
    """
    Recursively accumulate bias-type counts from either:
      - {bias_type: [instances...], ...}
      - {group: {bias_type: [instances...], ...}, ...}
    We count items only when value is a list.
    """
    if not isinstance(obj, dict):
        return

    # Case A: direct mapping bias_type -> list
    for k, v in obj.items():
        if isinstance(v, list):
            counts[k] = counts.get(k, 0) + len(v)

    # Case B: nested dicts (e.g., categories or other grouping)
    for _, v in obj.items():
        if isinstance(v, dict):
            _count_bias_types_from_obj(v, counts)


def parse_bias_json(path: Path) -> Tuple[Optional[str], Dict[str, int]]:
    """Return (article_id, bias_type_counts)."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[WARN] Could not read {path}: {e}")
        return None, {}

    m = ID_RE.search(path.name)
    aid = m.group("id") if m else None

    counts: Dict[str, int] = {}
    _count_bias_types_from_obj(data, counts)
    return aid, counts


def safe_per_100(count: Any, wc: Any):
    try:
        c = float(count)
        w = float(wc)
        return 100.0 * c / w if w > 0 else None
    except Exception:
        return None


def safe_stats(series: pd.Series) -> Dict[str, Any]:
    """
    Return mean/median/std/min/max/count for numeric series,
    ignoring NaNs.
    """
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"mean": None, "median": None, "std": None, "min": None, "max": None, "count": 0}
    return {
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
        "min": float(s.min()),
        "max": float(s.max()),
        "count": int(s.shape[0]),
    }

def main() -> None:
    meta = read_overview()
    print(f"[READ] {OVERVIEW_CSV} (rows={len(meta):,})")

    files = find_bias_files()
    if not files:
        raise SystemExit(f"[ERR] No bias files found at: {BIAS_JSON_DIR / BIAS_GLOB}")
    print(f"[INFO] Found {len(files)} bias JSON files in {BIAS_JSON_DIR}")

    # Pass 1: parse and union all bias type names
    all_types = set()
    parsed = []
    for p in files:
        aid, counts = parse_bias_json(p)
        parsed.append((p, aid, counts))
        all_types.update(counts.keys())

    type_list = sorted(all_types)
    rows = []
    missing_meta = 0

    for p, aid, counts in parsed:
        if not aid:
            print(f"[WARN] Skip {p.name}: no article_id")
            continue

        m = meta[meta["article_id"] == aid]
        if m.empty:
            missing_meta += 1
            head = view = dom = None
            wc = None
        else:
            r = m.iloc[0]
            head, view, dom, wc = r["headline"], r["viewpoint_country"], r["domain"], r["word_count"]

        overall_total = int(sum(int(v) for v in counts.values()))

        row = {
            "article_id": aid,
            "headline": head,
            "viewpoint_country": view,
            "domain": dom,
            "word_count": wc,
            "overall_total": overall_total,
        }

        # bias-type counts
        for t in type_list:
            row[t] = int(counts.get(t, 0))

        # per-100 (overall + each type)
        row["overall_per_100"] = safe_per_100(row["overall_total"], row["word_count"])
        for t in type_list:
            row[f"{t}_per_100"] = safe_per_100(row[t], row["word_count"])

        rows.append(row)

    if missing_meta:
        print(f"[WARN] {missing_meta} bias files had no matching row in {OVERVIEW_CSV}.")

    # Column ordering (per-article)
    cols_id = ["article_id", "headline", "viewpoint_country", "domain", "word_count"]
    cols_overall = ["overall_total"]
    cols_types = type_list
    cols_overall100 = ["overall_per_100"]
    cols_types100 = [f"{t}_per_100" for t in type_list]

    df = (
        pd.DataFrame(rows, columns=cols_id + cols_overall + cols_types + cols_overall100 + cols_types100)
        .sort_values("article_id")
    )

    # Write per-article CSV
    BIAS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_csv = BIAS_OUT_DIR / "bias_overview_per_article.csv"
    df.to_csv(out_csv, index=False)
    print(f"[OK] Wrote {out_csv} (rows={len(df):,}, cols={len(df.columns)})")

    # -----------------------------
    # Per-domain aggregates (long)
    # -----------------------------
    if "domain" not in df.columns:
        raise SystemExit("[ERR] Cannot aggregate by domain: missing 'domain' column.")

    # Metrics to aggregate: totals + per_100s
    metrics_to_agg = ["overall_total"] + type_list + ["overall_per_100"] + cols_types100

    agg_rows = []
    for dom, g in df.groupby("domain", dropna=False):
        dom_name = (str(dom).strip().lower().replace("www.", "") if dom is not None else "UNKNOWN")
        for metric in metrics_to_agg:
            if metric not in g.columns:
                continue
            s = safe_stats(g[metric])
            agg_rows.append(
                {
                    "domain": dom_name,
                    "metric": metric,
                    "mean": s["mean"],
                    "median": s["median"],
                    "std": s["std"],
                    "min": s["min"],
                    "max": s["max"],
                    "count": s["count"],
                }
            )

    agg_df = pd.DataFrame(agg_rows).sort_values(["domain", "metric"])

    out_agg_csv = BIAS_OUT_DIR / "bias_overview_aggregates_per_domain.csv"
    agg_df.to_csv(out_agg_csv, index=False)
    print(f"[OK] Wrote {out_agg_csv} (rows={len(agg_df):,}, domains={agg_df['domain'].nunique()})")


if __name__ == "__main__":
    main()

