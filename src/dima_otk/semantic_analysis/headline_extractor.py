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
from textwrap import dedent
from dima_otk.utils.gpt_client import call_gpt

def extract_headline(text: str, model="gpt-4.1-mini") -> str:
    """
    Uses GPT to extract or generate a headline from an article.

    The model should:
    - Return the headline if one is clearly present in the article.
    - Otherwise, generate a concise and neutral headline.
    """

    messages = [
        {
            "role": "system",
            "content": dedent("""
                You are a headline extraction assistant.

                Given the full text of a news article, your job is to return the article's headline.

                If the article includes an actual headline at the top, return it exactly as written.

                If no explicit headline is present, generate a neutral, concise headline that reflects the main idea of the article. Keep it under 15 words.

                Only return the headline — do not include explanations or formatting.
            """)
        },
        {
            "role": "user",
            "content": f"Extract the headline from the following article:\n\n{text}"
        }
    ]

    try:
        response = call_gpt(messages, temperature=0.3, model=model)
        return response.strip().split("\n")[0]
    except Exception as e:
        print(f"[ERROR] Failed to extract headline: {e}")
        return "Untitled Article"
