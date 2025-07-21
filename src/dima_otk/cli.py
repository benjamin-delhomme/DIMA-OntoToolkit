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

import argparse
import os
import sys
from pathlib import Path

from dima_otk import DimaOTK

def main():
    parser = argparse.ArgumentParser(description="DIMA-OTK: Bias Extraction Tool")

    '''
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Force rebuilding TTL graph cache."
    )
    '''

    # Mutually exclusive input group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-t", "--text",
        help="Input text to analyze"
    )
    group.add_argument(
        "-a", "--articles",
        action="store_true",
        help="Analyze all .txt files in the 'articles/' directory"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to process (only valid with --articles)"
    )

    args = parser.parse_args()

    # Instantiate the class
    # rebuild cache not implemented extractor = DimaOTK(rebuild_cache=args.rebuild_cache)
    dimaotk = DimaOTK()

    if args.text:
        input_text = args.text.strip()
        if input_text:
            extractor.run(input_text)
        else:
            print("Error: Input text is empty.", file=sys.stderr)
            sys.exit(1)

    elif args.articles:
        articles_dir = Path("articles")
        if not articles_dir.exists() or not articles_dir.is_dir():
            print("Error: 'articles/' directory not found.", file=sys.stderr)
            sys.exit(1)

        txt_files = sorted(articles_dir.glob("*.txt"))
        if args.limit:
            txt_files = txt_files[:args.limit]

        if not txt_files:
            print("No .txt files found in 'articles/' directory.", file=sys.stderr)
            sys.exit(1)

        for path in txt_files:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                print(f"[FILE] Processing: {path}")
                dimaotk.run(text)
            else:
                print(f"Warning: File '{path}' is empty, skipping.")


if __name__ == "__main__":
    main()
