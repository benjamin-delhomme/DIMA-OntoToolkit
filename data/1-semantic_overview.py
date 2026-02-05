#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, Any, Iterable, Optional, List
from urllib.parse import urlparse
from statistics import mean, median, stdev

# ---------------- Paths ----------------
BASE_DIR = Path(__file__).resolve().parent
ARTICLES_DIR = BASE_DIR.parent / "articles"
SEMANTIC_DIR = BASE_DIR.parent/ "output" / "semantic_analysis"
OUTPUT_DIR = BASE_DIR / "output" / "semantic"

ID_FROM_NAME = re.compile(r"_(?P<id>[^_/]+)\.json$", re.IGNORECASE)


def iter_article_files() -> Iterable[Path]:
    for p in sorted(ARTICLES_DIR.glob("*_*.json")):
        if ID_FROM_NAME.search(p.name):
            yield p


def get_id_from_name(name: str) -> Optional[str]:
    m = ID_FROM_NAME.search(name)
    return m.group("id") if m else None


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def word_count(text: Optional[str]) -> int:
    if not isinstance(text, str) or not text:
        return 0
    return len(text.split())


def norm_domain(url: Optional[str]) -> str:
    if not url or not isinstance(url, str):
        return ""
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def safe_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def comp_article_semantics(sem: Dict[str, Any]) -> Dict[str, int]:
    """
    Returns raw counts for one article_processed JSON:
      - total_arguments, premises, developments, conclusions
    """
    motifs = sem.get("motifs", []) or []

    total_args = 0
    total_prem = 0
    total_dev = 0
    total_conc = 0

    for motif in motifs:
        for arg in (motif.get("arguments") or []):
            total_args += 1
            total_prem += len(arg.get("premises", []) or [])
            total_dev += len(arg.get("developments", []) or [])
            total_conc += len(arg.get("conclusions", []) or [])

    return dict(
        total_arguments=total_args,
        premises=total_prem,
        developments=total_dev,
        conclusions=total_conc,
    )


def safe_stats(values: List[Optional[float]]) -> Dict[str, Optional[float]]:
    vals = [float(v) for v in values if isinstance(v, (int, float))]
    if not vals:
        return dict(mean=None, median=None, std=None, min=None, max=None, count=0)
    return dict(
        mean=float(mean(vals)),
        median=float(median(vals)),
        std=float(stdev(vals)) if len(vals) > 1 else 0.0,  # sample std
        min=float(min(vals)),
        max=float(max(vals)),
        count=len(vals),
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Collect exploitable IDs + fallback word counts + context fields (viewpoint, domain)
    exploitable_ids = set()
    raw_wc: Dict[str, int] = {}
    viewpoints: Dict[str, str] = {}
    domains: Dict[str, str] = {}

    for ap in iter_article_files():
        try:
            art = load_json(ap)
        except Exception as e:
            print(f"[WARN] Could not read {ap.name}: {e}")
            continue
        if not art.get("exploitable", False):
            continue

        aid = get_id_from_name(ap.name) or art.get("id")
        if not aid:
            continue

        exploitable_ids.add(aid)
        raw_wc[aid] = word_count(art.get("text", ""))
        viewpoints[aid] = (art.get("viewpoint_country") or "").strip() or "UNKNOWN"
        domains[aid] = norm_domain(art.get("url")) or "UNKNOWN"

    # 2) Build per-article rows
    rows: List[Dict[str, Any]] = []
    # For aggregates
    metrics_for_agg: Dict[str, List[Optional[float]]] = {}

    def record_metric(name: str, value: Optional[float]):
        metrics_for_agg.setdefault(name, []).append(value)

    for aid in sorted(exploitable_ids):
        sem_path = SEMANTIC_DIR / f"article_processed_{aid}.json"
        if not sem_path.exists():
            print(f"[WARN] Missing semantic file for article_id={aid}")
            continue
        try:
            sem = load_json(sem_path)
        except Exception as e:
            print(f"[WARN] Could not read {sem_path.name}: {e}")
            continue

        headline = sem.get("headline", "")
        wc_sem = safe_int(sem.get("word_count"), 0)
        wc = wc_sem if wc_sem > 0 else raw_wc.get(aid, 0)

        counts = comp_article_semantics(sem)

        # Convenience
        P = counts["premises"]
        D = counts["developments"]
        C = counts["conclusions"]
        T = P + D + C

        # Per-100 metrics
        def per100(x: int) -> Optional[float]:
            return (100.0 * x / wc) if wc and wc > 0 else None

        # Per-argument averages
        def per_arg(x: int) -> Optional[float]:
            a = counts["total_arguments"]
            return (x / a) if a and a > 0 else None

        # Composition ratios (shares within P+D+C)
        def ratio(x: int, total: int) -> Optional[float]:
            return (x / total) if total and total > 0 else None

        row = {
            "article_id": aid,
            "headline": headline,
            "viewpoint_country": viewpoints.get(aid, "UNKNOWN"),
            "domain": domains.get(aid, "UNKNOWN"),
            "word_count": wc if wc > 0 else None,
            "total_arguments": counts["total_arguments"],
            "premises": P,
            "developments": D,
            "conclusions": C,
            # averages per argument
            "avg_premises_per_argument": per_arg(P),
            "avg_developments_per_argument": per_arg(D),
            "avg_conclusions_per_argument": per_arg(C),
            "avg_pdc_per_argument": per_arg(T),
            # composition ratios
            "premise_ratio": ratio(P, T),
            "development_ratio": ratio(D, T),
            "conclusion_ratio": ratio(C, T),
            # per 100 words
            "arguments_per_100": per100(counts["total_arguments"]),
            "premises_per_100": per100(P),
            "developments_per_100": per100(D),
            "conclusions_per_100": per100(C),
        }
        rows.append(row)

        # Collect for aggregates
        for key in [
            "total_arguments",
            "premises",
            "developments",
            "conclusions",
            "avg_premises_per_argument",
            "avg_developments_per_argument",
            "avg_conclusions_per_argument",
            "avg_pdc_per_argument",
            "premise_ratio",
            "development_ratio",
            "conclusion_ratio",
            "arguments_per_100",
            "premises_per_100",
            "developments_per_100",
            "conclusions_per_100",
        ]:
            record_metric(key, row[key])

    # 3) Write per-article CSV (overwrite)
    per_article_csv = OUTPUT_DIR / "semantic_overview_per_article.csv"
    with per_article_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows[0].keys()) if rows else [
            "article_id",
            "headline",
            "viewpoint_country",
            "domain",
            "word_count",
            "total_arguments",
            "premises",
            "developments",
            "conclusions",
            "avg_premises_per_argument",
            "avg_developments_per_argument",
            "avg_conclusions_per_argument",
            "avg_pdc_per_argument",
            "premise_ratio",
            "development_ratio",
            "conclusion_ratio",
            "arguments_per_100",
            "premises_per_100",
            "developments_per_100",
            "conclusions_per_100",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # 4) Write aggregates CSV (overwrite) in long format (one row per metric)
    agg_csv = OUTPUT_DIR / "semantic_overview_aggregates.csv"
    with agg_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "mean", "median", "std", "min", "max", "count"])
        for metric_name in sorted(metrics_for_agg.keys()):
            s = safe_stats(metrics_for_agg[metric_name])
            writer.writerow([metric_name, s["mean"], s["median"], s["std"], s["min"], s["max"], s["count"]])

    print(f"[OK] Wrote {per_article_csv} ({len(rows)} articles)")
    print(f"[OK] Wrote {agg_csv} ({len(metrics_for_agg)} metrics)")


if __name__ == "__main__":
    main()

