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

from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict

from dima_otk.semantic_analysis.argument_extractor import extract_arguments
from dima_otk.utils.cache import load_or_compute_cache

def is_similar(text1: str, text2: str, threshold: float = 0.95) -> bool:
    """
    Determines if two texts are similar enough based on a similarity ratio.
    Ignores capitalization and minor differences.
    """
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() >= threshold


def assign_component_id(text: str, component_map: dict, prefix: str, counters: list) -> str:
    """
    Assigns a stable ID to a narrative component (e.g., premise, development, conclusion)
    based on fuzzy similarity.

    Args:
        text: The component text
        component_map: A dict {existing_text: id}
        prefix: String prefix for the ID (e.g., 'premise')
        counter: A list [n] tracking the current index

    Returns:
        A stable ID for the component
    """
    for known_text, cid in component_map.items():
        if is_similar(text, known_text):
            return cid
    new_id = f"{prefix}_{counters[prefix]}"
    counters[prefix] += 1
    component_map[text] = new_id
    return new_id

def process_arguments(text: str):
    print(f"🔎 Processing motif {motif_id}: {text[:80]}...")
    return extract_arguments(text)

def get_arguments_from_motifs(motifs: list[dict], article: dict):
    """
    Identify arguments (premises, developments, conclusions) from each motif in an article.
    Assigns IDs and reuses cache if available.
    Returns a list of motif dicts with their arguments.
    """
    # Deduplication maps and counters
    premise_map, development_map, conclusion_map = {}, {}, {}
    counters = {
        "premise": 0,
        "development": 0,
        "conclusion": 0,
        "argument": 0
    }

    article_id = article["id"]
    result = []

    for motif in motifs:
        motif_id = motif["id"]
        text = motif["text"]

        cache_result = load_or_compute_cache(
            cache_key=f"article_{article_id}-motif_{motif_id}",
            cache_type="arguments_cache",
            compute_fn=lambda: {"arguments": process_arguments(text)},
            verbose_label=f"arguments in {motif_id}"
        )

        arguments = cache_result["arguments"]

        # Assign unique IDs
        for arg in arguments:
            arg["argument_id"] = f"argument_{counters['argument']}"
            counters["argument"] += 1

            for section, prefix, cmap in [
                ("premises", "premise", premise_map),
                ("developments", "development", development_map),
                ("conclusions", "conclusion", conclusion_map),
            ]:
                for component in arg.get(section, []):
                    component["id"] = assign_component_id(component["text"], cmap, prefix, counters)

        result.append({
            "motif_id": motif_id,
            "text": text,
            "arguments": arguments
        })

    return result
