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
SEMANTIC_DIR = BASE_DIR.parent / "output" / "semantic_analysis"
OUTPUT_DIR = BASE_DIR / "output" / "semantic"

ID_FROM_NAME = re.compile(r"_(?P<id>[^_/]+)\.json$", re.IGNORECASE)


# ---------------- IO helpers ----------------
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


def safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


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


# ---------------- Core computation ----------------
def count_total_arguments(sem: Dict[str, Any]) -> int:
    motifs = sem.get("motifs", []) or []
    total = 0
    for motif in motifs:
        if not isinstance(motif, dict):
            continue
        args = motif.get("arguments") or []
        if isinstance(args, list):
            total += len(args)
    return total


def comp_quotes_agents(sem: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dict with:
      - total_arguments
      - quotes_total
      - quote_type_counts: Dict[str,int]
      - quote_status_counts: Dict[str,int]
      - unique_agents
      - agent_type_unique_count
      - agent_type_counts: Dict[str,int]  (counts narrated_agents by type)
      - mentions_total, attributions_total
      - mentions_by_agent_type: Dict[str,int]
      - attributions_by_agent_type: Dict[str,int]
    """
    quotes = sem.get("quotes", []) or []
    agents = sem.get("narrated_agents", []) or []
    total_arguments = count_total_arguments(sem)

    # agent_id -> agent_type
    agent_id_to_type: Dict[str, str] = {}
    agent_type_counts: Dict[str, int] = {}
    for a in agents:
        if not isinstance(a, dict):
            continue
        aid = a.get("agent_id")
        atype = a.get("type") or "UNKNOWN"
        if isinstance(aid, str) and aid:
            agent_id_to_type[aid] = str(atype)
        agent_type_counts[str(atype)] = agent_type_counts.get(str(atype), 0) + 1

    unique_agents = len(agent_id_to_type) if agent_id_to_type else (len(agents) if isinstance(agents, list) else 0)
    agent_type_unique_count = len(set(agent_type_counts.keys())) if agent_type_counts else 0

    # quotes: types + statuses
    quote_type_counts: Dict[str, int] = {}
    quote_status_counts: Dict[str, int] = {}

    mentions_total = 0
    attributions_total = 0
    mentions_by_agent_type: Dict[str, int] = {}
    attributions_by_agent_type: Dict[str, int] = {}

    for q in quotes:
        if not isinstance(q, dict):
            continue

        qtype = q.get("type") or "UNKNOWN"
        qstatus = q.get("status") or "UNKNOWN"
        quote_type_counts[str(qtype)] = quote_type_counts.get(str(qtype), 0) + 1
        quote_status_counts[str(qstatus)] = quote_status_counts.get(str(qstatus), 0) + 1

        mentioned = q.get("mentions", []) or []
        attributed = q.get("attributed_to", []) or []

        if isinstance(mentioned, list):
            mentions_total += len(mentioned)
            for mid in mentioned:
                if not isinstance(mid, str):
                    continue
                mtype = agent_id_to_type.get(mid, "UNKNOWN")
                mentions_by_agent_type[mtype] = mentions_by_agent_type.get(mtype, 0) + 1

        if isinstance(attributed, list):
            attributions_total += len(attributed)
            for aid in attributed:
                if not isinstance(aid, str):
                    continue
                atype = agent_id_to_type.get(aid, "UNKNOWN")
                attributions_by_agent_type[atype] = attributions_by_agent_type.get(atype, 0) + 1

    return dict(
        total_arguments=total_arguments,
        quotes_total=len(quotes),
        quote_type_counts=quote_type_counts,
        quote_status_counts=quote_status_counts,
        unique_agents=unique_agents,
        agent_type_unique_count=agent_type_unique_count,
        agent_type_counts=agent_type_counts,
        mentions_total=mentions_total,
        attributions_total=attributions_total,
        mentions_by_agent_type=mentions_by_agent_type,
        attributions_by_agent_type=attributions_by_agent_type,
    )


# ---------------- Main ----------------
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

    if not exploitable_ids:
        print("[WARN] No exploitable articles found. Nothing to do.")
        return

    # 2) First semantic pass to collect dynamic categories (quote types/statuses/agent types)
    per_article_cache: Dict[str, Dict[str, Any]] = {}
    all_quote_types = set()
    all_quote_statuses = set()
    all_agent_types = set()

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

        counts = comp_quotes_agents(sem)
        per_article_cache[aid] = {"sem": sem, "counts": counts}

        all_quote_types.update((counts.get("quote_type_counts") or {}).keys())
        all_quote_statuses.update((counts.get("quote_status_counts") or {}).keys())
        all_agent_types.update((counts.get("agent_type_counts") or {}).keys())
        all_agent_types.update((counts.get("mentions_by_agent_type") or {}).keys())
        all_agent_types.update((counts.get("attributions_by_agent_type") or {}).keys())

    quote_types = sorted(all_quote_types)
    quote_statuses = sorted(all_quote_statuses)
    agent_types = sorted(all_agent_types)

    # 3) Build per-article rows
    rows: List[Dict[str, Any]] = []
    metrics_for_agg: Dict[str, List[Optional[float]]] = {}

    def record_metric(name: str, value: Optional[float]):
        metrics_for_agg.setdefault(name, []).append(value)

    def per100(x: int, wc: int) -> Optional[float]:
        return (100.0 * x / wc) if wc and wc > 0 else None

    def per_arg(x: int, n_args: int) -> Optional[float]:
        return (x / n_args) if n_args and n_args > 0 else None

    def per_quote(x: int, n_quotes: int) -> Optional[float]:
        return (x / n_quotes) if n_quotes and n_quotes > 0 else None

    for aid in sorted(per_article_cache.keys()):
        sem = per_article_cache[aid]["sem"]
        counts = per_article_cache[aid]["counts"]

        headline = sem.get("headline", "")
        wc_sem = safe_int(sem.get("word_count"), 0)
        wc = wc_sem if wc_sem > 0 else raw_wc.get(aid, 0)

        n_args = int(counts.get("total_arguments", 0) or 0)
        n_quotes = int(counts.get("quotes_total", 0) or 0)

        # Base row/meta
        row: Dict[str, Any] = {
            "article_id": aid,
            "headline": headline,
            "viewpoint_country": viewpoints.get(aid, "UNKNOWN"),
            "domain": domains.get(aid, "UNKNOWN"),
            "word_count": wc if wc > 0 else None,
            "total_arguments": n_args if n_args > 0 else 0,
        }

        # ---- Quotes totals + per100 + per_argument ----
        row["quotes_total"] = n_quotes
        row["quotes_per_100"] = per100(n_quotes, wc)
        row["quotes_per_argument"] = per_arg(n_quotes, n_args)

        # Quote types
        q_type_counts: Dict[str, int] = counts.get("quote_type_counts") or {}
        for qt in quote_types:
            v = int(q_type_counts.get(qt, 0))
            row[f"quote_type__{qt}"] = v
            row[f"quote_type__{qt}_per_100"] = per100(v, wc)
            row[f"quote_type__{qt}_per_argument"] = per_arg(v, n_args)

        # Quote statuses
        q_status_counts: Dict[str, int] = counts.get("quote_status_counts") or {}
        for qs in quote_statuses:
            v = int(q_status_counts.get(qs, 0))
            row[f"quote_status__{qs}"] = v
            row[f"quote_status__{qs}_per_100"] = per100(v, wc)
            row[f"quote_status__{qs}_per_argument"] = per_arg(v, n_args)

        # ---- Agents totals + per100 + per_argument ----
        unique_agents = int(counts.get("unique_agents", 0) or 0)
        unique_agent_types = int(counts.get("agent_type_unique_count", 0) or 0)

        row["unique_agents"] = unique_agents
        row["unique_agents_per_100"] = per100(unique_agents, wc)
        row["unique_agents_per_argument"] = per_arg(unique_agents, n_args)

        row["unique_agent_types"] = unique_agent_types
        row["unique_agent_types_per_100"] = per100(unique_agent_types, wc)
        row["unique_agent_types_per_argument"] = per_arg(unique_agent_types, n_args)

        # ---- Mentions & attributions totals ----
        mentions_total = int(counts.get("mentions_total", 0) or 0)
        attributions_total = int(counts.get("attributions_total", 0) or 0)

        row["mentions_total"] = mentions_total
        row["mentions_per_100"] = per100(mentions_total, wc)
        row["mentions_per_argument"] = per_arg(mentions_total, n_args)
        row["mentions_per_quote"] = per_quote(mentions_total, n_quotes)

        row["attributions_total"] = attributions_total
        row["attributions_per_100"] = per100(attributions_total, wc)
        row["attributions_per_argument"] = per_arg(attributions_total, n_args)
        row["attributions_per_quote"] = per_quote(attributions_total, n_quotes)

        # ---- Mentions by agent type (counts + per100 + per_argument + per_quote) ----
        mentions_by_type: Dict[str, int] = counts.get("mentions_by_agent_type") or {}
        for at in agent_types:
            v = int(mentions_by_type.get(at, 0))
            row[f"mentions_agent_type__{at}"] = v
            row[f"mentions_agent_type__{at}_per_100"] = per100(v, wc)
            row[f"mentions_agent_type__{at}_per_argument"] = per_arg(v, n_args)
            row[f"mentions_agent_type__{at}_per_quote"] = per_quote(v, n_quotes)

        # ---- Attributions by agent type (counts + per100 + per_argument + per_quote) ----
        attrs_by_type: Dict[str, int] = counts.get("attributions_by_agent_type") or {}
        for at in agent_types:
            v = int(attrs_by_type.get(at, 0))
            row[f"attributions_agent_type__{at}"] = v
            row[f"attributions_agent_type__{at}_per_100"] = per100(v, wc)
            row[f"attributions_agent_type__{at}_per_argument"] = per_arg(v, n_args)
            row[f"attributions_agent_type__{at}_per_quote"] = per_quote(v, n_quotes)

        rows.append(row)

        # Collect for aggregates: every numeric metric (skip ids/text)
        for k, v in row.items():
            if k in {"article_id", "headline", "viewpoint_country", "domain"}:
                continue
            record_metric(k, safe_float(v))

    # 4) Write per-article CSV
    per_article_csv = OUTPUT_DIR / "quote_agent_overview_per_article.csv"
    fieldnames = list(rows[0].keys()) if rows else []
    with per_article_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # 5) Write aggregates CSV (long format)
    agg_csv = OUTPUT_DIR / "quote_agent_overview_aggregates.csv"
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

