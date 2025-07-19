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

from typing import List, Dict
from pathlib import Path
import json

from dima_otk.semantic_analysis.quote_extractor import extract_quote_shells, assign_quote_agents, link_quotes_to_components
from dima_otk.utils.cache import load_or_compute_cache

def process_quotes(motif_text, motif_id, agents, components) -> List[dict]:
    print(f"🗣️ Extracting quotes for {motif_id}...")

    # Step 1: extract quote shells
    quotes = extract_quote_shells(motif_text)
    print(f"🔍 Found {len(quotes)} quote shells in {motif_id}")

    # Step 2: assign attribution and mentions
    quotes = assign_quote_agents(motif_text, quotes, agents)

    # Step 3: link quotes to narrative components
    quotes = link_quotes_to_components(motif_text, quotes, components)

    return quotes

def get_quotes_for_article(motifs: list[dict], agents: list[dict], article: dict) -> list[dict]:
    """
    Process and extract quotes per motif using GPT in 3 modular stages:
    1. Extract quote shell (text, type, status)
    2. Assign speaker attribution and mentions
    3. Link quotes to narrative components

    Caches results per motif and assigns global quote IDs.
    Returns a flat list of all quotes in the article.
    """

    article_id = article["id"]
    all_quotes = []
    quote_counter = 0

    for motif in motifs:
        motif_id = motif["motif_id"]
        motif_text = motif["text"]

        # Extract narrative components from this motif
        components = []
        for arg in motif.get("arguments", []):
            for section in ["premises", "developments", "conclusions"]:
                for comp in arg.get(section, []):
                    components.append({
                        "id": comp["id"],
                        "text": comp["text"]
                    })

        cache_result = load_or_compute_cache(
            cache_key=f"article_{article_id}-motif_{motif_id}_quotes",
            cache_type="quotes_cache",
            compute_fn=lambda: {"quotes": process_quotes(motif_text, motif_id, agents, components)},
            verbose_label=f"quotes in {motif_id}"
        )

        quotes = cache_result["quotes"]

        # Assign global quote ID and motif context
        for quote in quotes:
            quote["quote_id"] = f"quote_{quote_counter}"
            quote["motif_id"] = motif_id
            quote_counter += 1

        all_quotes.extend(quotes)

    print(f"[INFO] Extracted {len(all_quotes)} quotes across {len(motifs)} motifs.")
    return all_quotes
