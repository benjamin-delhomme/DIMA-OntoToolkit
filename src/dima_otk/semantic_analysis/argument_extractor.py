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
from textwrap import dedent
from dima_otk.utils.gpt_client import call_gpt

def extract_arguments(text: str, model="gpt-4.1-mini") -> list[dict]:
    """
    Uses GPT-4o to extract all argument structures from a given text.

    Each argument can have:
    - one or more premises (supporting claims)
    - zero or more developments (reasoning, interpretation)
    - zero or more conclusions (final judgments)

    The result is a list of dictionaries with:
    - 'premises': list of strings
    - 'developments': list of strings
    - 'conclusions': list of strings
    """


    messages = [
        {
            "role": "system",
            "content": """
                You are a narrative reasoning assistant.

                Your task is to identify all distinct arguments present in a news article.

                An **argument** is any cluster of narrative claims that form a line of reasoning, judgment, or persuasion.
                Each argument may include:
                - **Premises** — factual claims, assumptions, or context-setting statements that support reasoning
                - **Developments** — interpretive or inferential steps that expand on premises or bridge to conclusions
                - **Conclusions** — final judgments, stances, or main claims the narrative wants to convey

                ---

                Reasoning Guidance:
                - A single article may contain multiple arguments — even if they refer to similar facts.
                - Some arguments may share the same premise or conclusion — that’s okay.
                - An argument can be as small as a premise and a conclusion, or span many developments.
                - If a sentence clearly plays a double role (e.g. it's both a development and a conclusion), include it in both arguments where relevant.

                ---

                For each argument, return a dictionary with exactly:
                - `"premises"`: a list of { "text": ... }
                - `"developments"`: a list of { "text": ... }
                - `"conclusions"`: a list of { "text": ... }

                Do **not** flatten components across arguments.
                Group them into distinct argument objects — one per line of reasoning.

                ---

                Example Output:

                ```json
                [
                  {
                    "premises": [
                      { "text": "The protest was held in response to a police shooting." }
                    ],
                    "developments": [
                      { "text": "Activists claimed the police had used excessive force." }
                    ],
                    "conclusions": [
                      { "text": "The shooting was unjustified and reform is needed." }
                    ]
                  },
                  {
                    "premises": [
                      { "text": "The mayor refused to comment on the investigation." }
                    ],
                    "developments": [],
                    "conclusions": [
                      { "text": "The administration is avoiding accountability." }
                    ]
                  }
                ]
                """
        },
        {
            "role": "user",
            "content": f"Extract the argument structure from the following article:\n\n{text}"
        }
    ]


    try:
        response = call_gpt(messages, temperature=0.3, model=model)
        if response.strip().startswith("```json"):
            response = response.strip().removeprefix("```json").removesuffix("```").strip()
        elif response.strip().startswith("```"):
            response = response.strip().removeprefix("```").removesuffix("```").strip()

        return json.loads(response)
    except Exception as e:
        print(f"[ERROR] Failed to extract arguments: {e}")
        return []
