#!/usr/bin/env python3

# Copyright 2025 Benjamin Delhomme, NATO Strategic Communications Centre of Excellence
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
DIMA‑OTK command‑line interface
───────────────────────────────
Adds **-q / --query** so you can:
  • run extraction on a text (‑t) or a folder of articles (‑a), **then**
  • immediately fire a SPARQL query against the merged ontology, or
  • run a query alone if no input is provided.

Examples
~~~~~~~~
Analyse a single text and query:
    dima-otk -t "Foo" -q "SELECT * WHERE { ?s ?p ?o } LIMIT 5"

Batch‑process the ./articles folder (first 50 files) then query:
    dima-otk -a --limit 50 -q "ASK { ?x a <IRI#Motif> }"

Just query an existing ontology:
    dima-otk -q "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"
"""

import argparse
import sys
from pathlib import Path

from tabulate import tabulate

from dima_otk import DimaOTK
from dima_otk.owl.owl_influencemini_query import query_flat_ontology

MERGED_OWL_PATH = Path("output/owl_influence-mini/influence-mini_full.owl")


def _print_query_results(rows, max_width: int = 40):
    """Render SPARQL SELECT / ASK results as a clean table.

    * Uses *tabulate*'s ``maxcolwidths`` feature when available (tabulate ≥ 0.9)
      to auto‑truncate wide cells.
    * Falls back to a manual truncation routine on older versions bundled in
      the Docker image.
    """

    if isinstance(rows, bool):  # ASK queries
        print("Result:", rows)
        return

    if not rows:
        print("[No results]")
        return

    # Column headers (rdflib returns ResultRow with .labels)
    headers = rows[0].labels if hasattr(rows[0], "labels") else [f"col{i}" for i in range(len(rows[0]))]
    table   = [[str(cell) for cell in row] for row in rows]

    try:
        # tabulate ≥ 0.9 supports maxcolwidths
        print(
            tabulate(
                table,
                headers=headers,
                tablefmt="grid",
                maxcolwidths=max_width,  # type: ignore[arg-type]
                disable_numparse=True,
            )
        )
    except TypeError:
        # Older tabulate: manual truncation
        def shorten(text: str) -> str:
            return text if len(text) <= max_width else text[: max_width - 1] + "…"

        table = [[shorten(cell) for cell in row] for row in table]
        print(tabulate(table, headers=headers, tablefmt="grid", disable_numparse=True))

def run_articles_mode(directory: Path, limit: int | None, extractor: DimaOTK):
    if not directory.is_dir():
        print("Error: 'articles/' directory not found.", file=sys.stderr)
        sys.exit(1)

    txt_files = sorted(directory.glob("*.txt"))
    if limit:
        txt_files = txt_files[: limit]

    if not txt_files:
        print("No .txt files found in 'articles/' directory.", file=sys.stderr)
        sys.exit(1)

    for path in txt_files:
        text = path.read_text(encoding="utf-8").strip()
        if text:
            print(f"[FILE] Processing: {path}")
            extractor.run(text)
        else:
            print(f"Warning: File '{path}' is empty, skipping.")


def main():
    parser = argparse.ArgumentParser(description="DIMA‑OTK: Bias Extraction Tool")

    # Input modes (text and/or articles). They remain mutually exclusive.
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--text", help="Input text to analyze")
    group.add_argument(
        "-a",
        "--articles",
        action="store_true",
        help="Analyze all .txt files in the 'articles/' directory",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to process (only valid with --articles)",
    )

    # SPARQL query (optional, can be combined with text/articles or used alone)
    parser.add_argument(
        "-q",
        "--query",
        metavar="SPARQL",
        help="Run a SPARQL query on the flat merged ontology after processing",
    )

    args = parser.parse_args()

    # run extractor if requested
    ran_extractor = False
    extractor = None

    if args.text or args.articles:
        extractor = DimaOTK()

    if args.text:
        input_text = args.text.strip()
        if not input_text:
            print("Error: Input text is empty.", file=sys.stderr)
            sys.exit(1)
        extractor.run(input_text)
        ran_extractor = True

    elif args.articles:
        run_articles_mode(Path("articles"), args.limit, extractor)
        ran_extractor = True

    # run sparql query if requested
    if args.query is not None:
        # Ensure the merged ontology exists (it should if extractor just ran)
        if not MERGED_OWL_PATH.exists():
            print(
                f"Error: merged ontology '{MERGED_OWL_PATH}' not found. "
                "Run extraction first (‑t or ‑a) to generate it.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            rows = query_flat_ontology(MERGED_OWL_PATH, args.query, reason=True)
            _print_query_results(rows)
        except Exception as exc:
            print(f"SPARQL query failed: {exc}", file=sys.stderr)
            sys.exit(1)

    # If the user specified neither input nor query, show help
    if not (args.text or args.articles or args.query):
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
