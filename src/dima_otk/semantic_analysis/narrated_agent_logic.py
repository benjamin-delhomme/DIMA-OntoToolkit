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

from dima_otk.semantic_analysis.narrated_agent_extractor import extract_narrated_agents
from dima_otk.utils.cache import load_or_compute_cache

def process_agents(motifs: list[dict]) -> List[dict]:
    full_text = "\n\n".join(m["text"] for m in motifs)
    return extract_narrated_agents(full_text)

def get_narrated_agents(motifs: list[dict], article: dict) -> List[dict]:
    """
    Concatenates motifs into a single article text and extracts narrative agents.
    Uses GPT + caching. Assigns stable IDs: agent_0, agent_1, ...
    """
    article_id = article["id"]

    cache_result = load_or_compute_cache(
        cache_key=f"article_{article_id}-agents",
        cache_type="agents_cache",
        compute_fn=lambda: {"raw_agents": process_agents(motifs)},
        verbose_label="narrated agents"
    )

    raw_agents = cache_result["raw_agents"]

    agents = []
    for i, agent in enumerate(raw_agents):
        name = agent.get("name", "").strip() or "unknown"
        agent_type = agent.get("type", "Unknown")
        agents.append({
            "agent_id": f"agent_{i}",
            "name": name,
            "type": agent_type
        })

    return agents
