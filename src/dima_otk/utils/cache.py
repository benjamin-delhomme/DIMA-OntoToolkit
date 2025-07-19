# dima_otk/utils/cache.py

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
from pathlib import Path
from typing import Optional

#Docker build set working dir in /app
defaultPath = Path("output")

def get_cache_path(filename: str, cache_type: str) -> Path:
    path = defaultPath / cache_type
    Path(path).mkdir(parents=True, exist_ok=True)
    return path / f"{filename}.json"

def load_json_cache(filename: str, cache_type: str) -> Optional[dict]:
    path = get_cache_path(filename, cache_type)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_json_cache(filename: str, cache_type: str, dict_object: dict):
    path = get_cache_path(filename, cache_type)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict_object, f, indent=2, ensure_ascii=False)

def load_or_compute_cache(
    cache_key: str,
    cache_type: str,
    compute_fn: Callable[[], dict],
    verbose_label: Optional[str] = None
) -> dict:
    """
    Loads a cached result if available; otherwise computes it and saves to cache.

    Args:
        cache_key (str): Unique key for the cache entry. (filename)
        cache_type (str): Cache subfolder/type.
        compute_fn (Callable): Function that returns the data to be cached.
        verbose_label (str): Optional label for logging (e.g. motif_id).

    Returns:
        dict: Cached or computed result.
    """
    cached = load_json_cache(cache_key, cache_type)

    if cached:
        if verbose_label:
            print(f"[INFO] Loaded cached result for {verbose_label}")
        return cached
    else:
        if verbose_label:
            print(f"[INFO] Computing result for {verbose_label} via GPT...")
        result = compute_fn()
        save_json_cache(cache_key, cache_type, result)
        return result
