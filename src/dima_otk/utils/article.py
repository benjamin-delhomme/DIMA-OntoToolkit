# dima_otk/utils/article.py

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

import html
import re
import hashlib
from ftfy import fix_text

def print_article_summary(article_id: str, headline: str, content: str):
    label_width = 8
    preview = content[:200].strip() + ("..." if len(content) > 200 else "")

    print("[ARTICLE]")
    print(f"{'ID'.ljust(label_width)}: {article_id}")
    print(f"{'Headline'.ljust(label_width)}: {headline}")
    print(f"{'Preview'.ljust(label_width)}: {preview}")

def get_article_id(text: str, length: int = 10, sample_size: int = 100) -> str:
    """
    Generate a short ID for an article based on a hash of its first `sample_size` characters.

    Args:
        text (str): Article content.
        length (int): Length of the returned hash. Default: 10.
        sample_size (int): Number of characters to hash. Default: 100.

    Returns:
        str: Truncated SHA-256 hash as article ID.
    """
    snippet = text[:sample_size]
    hash_obj = hashlib.sha256(snippet.encode("utf-8"))
    return hash_obj.hexdigest()[:length]

def clean_text(text: str) -> str:
    """
    Clean and normalize article text using ftfy and other post-processing.
    """
    if not text:
        return ""

    # Fix encoding issues
    text = fix_text(text)

    # Decode HTML entities (e.g., &amp;)
    text = html.unescape(text)

    # Convert _x000D_ markers to paragraph breaks
    text = re.sub(r'_x000D_', '\n\n', text)

    # Remove any bad replacement characters
    text = re.sub(r'[�]+', '', text)

    # Collapse only spaces and tabs — keep newlines
    text = re.sub(r'[ \t]+', ' ', text)

    return text.strip()
