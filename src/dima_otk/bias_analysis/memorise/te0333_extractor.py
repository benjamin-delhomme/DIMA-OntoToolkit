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

#might be interesting to run this one at the article level (aggregate of motifs)
def extract_technique_te0333(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0333 – Primacy Effect (Effet de primauté).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0333 – Primacy Effect (Effet de primauté) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0333 – Primacy Effect (Effet de primauté)
                → Communicators exploit our tendency to give disproportionate weight or importance to the very first information we receive, which can strongly shape memory, judgments, or impressions about a topic or person. Primacy effect occurs when the earliest facts, statements, or framing color all subsequent perception—even if later content is equally or more relevant.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the primacy effect.
                • Indicators of primacy effect include:
                  – Highlighting, emphasizing, or repeating the very first facts, framing, or claims as the main influence on how all later information is understood or judged.
                  – Structuring arguments so that initial statements or introductions set the “frame” or “anchor” for all that follows, especially if later content is downplayed or interpreted through this initial lens.
                  – Explicit claims that first impressions, first statements, or how an issue is first introduced has lasting or dominant impact on perception or decision.
                  – Arguments that suggest it is difficult to overcome or correct initial information, even after subsequent facts are presented.
                • Do **not** count as primacy effect:
                  – Arguments that build preference or trust through repeated mention or familiarity over time, regardless of when the information first appears (this is the Mere Exposure Effect).
                  – Claims about emotional fading or diminished negativity of past experiences over time (that is Fading Affect Bias).
                  – Arguments that focus on the impact of the last or most recent information as especially important or memorable (this is the Recency Effect).
                  – Claims that rely on the logical progression or evidence presented throughout, not just the initial information.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the primacy effect.
                • Identify exactly which Premises / Developments / Conclusions do so.
                • Provide a concise justification and a couple of trigger excerpts.

                ======== OUTPUT =========================================================
                Return one JSON array — no code‑fence — where each element follows:

                {
                  "argument_id": "<id or index>",
                  "bias": true | false,
                  "premise_ids": ["premise_3", ...], # empty if none biased
                  "development_ids": ["development_0", ...],
                  "conclusion_ids": ["conclusion_1", ...],
                  "excerpts": ["...", "..."], # very short quotes
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
        print(f"[ERROR] Primacy-effect detection failed: {e}")
        return {}
