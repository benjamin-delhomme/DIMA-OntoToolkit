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
from dima_otk.utils.gpt_client import call_gpt

def extract_technique_te0141(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0141 – Von Restorff Effect (Effet d'Isolation).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0141 – Von Restorff Effect (Effet d'Isolation) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0141 – Von Restorff Effect (Effet d'Isolation)
                → Communicators exploit our tendency to notice, remember, or give extra importance to an item, message, or element that stands out or is isolated from its surrounding context. This effect is produced by making something distinct or contrasting—visually, structurally, or conceptually—even if the content itself is ordinary or expected.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the Von Restorff Effect.
                • Indicators of Von Restorff Effect include:
                  – An element (fact, statement, phrase, or feature) is made distinctive by its presentation, such as color, formatting, unusual positioning, or by breaking an established pattern.
                  – The isolation or difference draws attention or makes the element more memorable, regardless of whether the content itself is unusual or significant.
                  – The argument emphasizes how something is “different from the rest,” “stands out,” or “catches the eye,” whether by visual, conceptual, or contextual contrast.
                • Do **not** count as Von Restorff Effect:
                  – Cases where the standout item is inherently bizarre, absurd, or illogical (this is the Bizarreness Effect: the weirdness comes from *what it is*).
                  – Cases where an element is remembered or noticed because it is the first (Primacy Effect) or the last (Recency Effect) in a sequence.
                  – Situations where perception of one thing is altered *because of direct comparison* with another (Contrast Effect: perception is shifted by comparison, not by isolation).
                  – Arguments where repetition or growing familiarity explains preference or memory (Mere Exposure Effect).
                  – Normal highlighting for clarity or emphasis, unless specifically used to isolate and differentiate.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the Von Restorff Effect.
                • Identify exactly which Premises / Developments / Conclusions do so.
                • Provide a concise justification and a couple of trigger excerpts.

                ======== OUTPUT =========================================================
                Return one JSON array — no code‑fence — where each element follows:

                {
                  "argument_id": "<id or index>",
                  "bias": true | false,
                  "premise_ids": ["premise_3", ...],   # empty if none biased
                  "development_ids": ["development_0", ...],
                  "conclusion_ids": ["conclusion_1", ...],
                  "excerpts": ["...", "..."],           # very short quotes
                  "explanation": "one‑sentence rationale"
                }

                • Omit any ID list that would be empty.
                • Do not output a top‑level “bias_detected” field.
                • Do not add any keys or narrative outside the JSON array.
            """
        },
        {
            "role": "user",
            "content": f"Argument text:\n```\n{argument_text}\n```"
        }
    ]


    try:
        response = call_gpt(messages, temperature=0.0, model=model)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.lstrip("`").rstrip("`").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"[ERROR] Von Restorff Effect detection failed: {e}")
        return {}
