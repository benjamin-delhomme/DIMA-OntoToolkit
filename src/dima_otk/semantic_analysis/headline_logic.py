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

from .headline_extractor import extract_headline
from dima_otk.utils.cache import load_or_compute_cache

def get_article_headline(input_text: str, article_id: str) -> tuple[str, str]:
    """
    Extracts or generates a headline from the input text using GPT,
    and returns (headline, content). If the headline was originally
    part of the text, it is removed from the content.

    Args:
        input_text (str): The full article text, possibly including a headline.

    Returns:
        Tuple[str, str]: (headline, cleaned_content)
    """

    # Step 1: Extract or Retrieve Headline
    cache_result = load_or_compute_cache(
        cache_key=article_id,
        cache_type="headline_cache",
        compute_fn=lambda: {"headline": extract_headline(input_text)},
        verbose_label="headline and content"
    )

    headline = cache_result["headline"]
    normalized_headline = headline.strip().lower()

    # Step 2: Split original input by lines (preserving original line structure)
    original_lines = input_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Step 3: If the headline is present near the top, remove it — but keep blank lines
    cleaned_lines = []
    found = False
    for i, line in enumerate(original_lines):
        line_clean = line.strip().lower()
        if not found and line_clean == normalized_headline and i <= 2:
            found = True
            continue  # skip the headline line
        cleaned_lines.append(line)

    cleaned_content = "\n".join(cleaned_lines).strip()
    return headline, cleaned_content
