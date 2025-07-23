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

import json
from typing import List, Dict, Callable

from dima_otk.utils.cache import load_or_compute_cache

def get_act_techniques(processed_article: dict) -> dict:
    return {
        # "xxxxxxxxxx": get_act_technique(processed_article,"texxxx",extract_technique_texxxx),
        # Add more techniques as needed
    }

def get_act_technique(article: Dict, technique_code: str, extract_fn: Callable[[Dict], List[Dict]]) -> List[Dict]:
    """
    Scan every motif in an article for a given technique using caching to avoid repeated GPT calls.
    Returns a flat list of argument-level verdicts with the motif_id attached.
    """
    results: List[Dict] = []

    article_id = article["article_id"]

    tech_code = technique_code.upper()

    for motif in article.get("motifs", []):
        motif_id = motif["motif_id"]

        cache_key = f"article_{article_id}-motif_{motif_id}-{tech_code}"
        verbose_label = f"Act - {tech_code} Extraction in {motif_id}"

        cache_result = load_or_compute_cache(
            cache_key=cache_key,
            cache_type="act_cache",
            compute_fn=lambda m=motif: {
                "rows": extract_fn(m)
            },
            verbose_label=verbose_label
        )

        motif_rows = cache_result.get("rows", [])

        for row in motif_rows:
            # Only push results that are detected as bias
            if row.get("bias") is True:
                row["motif_id"] = motif_id
                results.append(row)

    return results
