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
from typing import List, Dict

from dima_otk.bias_analysis.detect.te0131_extractor import extract_technique_te0131
from dima_otk.utils.cache import load_or_compute_cache


def get_technique_te0131(article: Dict) -> List[Dict]:
    """
    Scan every motif in an article for Technique TE0132 – Negativity Bias,
    using caching to avoid repeated GPT calls.

    Returns a flat list of argument‑level verdicts with the motif_id attached.
    """
    results: List[Dict] = []

    article_id = article["article_id"]

    for motif in article.get("motifs", []):
        motif_id = motif["motif_id"]

        cache_key = f"article_{article_id}-motif_{motif_id}-TE0131"
        verbose_label = f"Detect - TE0131 Extraction in {motif_id}"

        cache_result = load_or_compute_cache(
            cache_key=cache_key,
            cache_type="detect_cache",
            compute_fn=lambda m=motif: {
                "rows": extract_technique_te0131(m)
            },
            verbose_label=verbose_label
        )

        motif_rows = cache_result.get("rows", [])

        for row in cache_result.get("rows", []):
            # Only push the result that are detected as bias (the explanation for non bias can be found in the cache)
            if row.get("bias") is True:
                row["motif_id"] = motif_id
                results.append(row)

    return results
