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

def extract_technique_te0433(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0433 – Information Overload (Saturation informationnelle).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0433 – Information Overload (Saturation informationnelle) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0433 – Information Overload (Saturation informationnelle)
                → Communicators exploit the target's limited capacity to process information by overwhelming them with a large volume, variety, or complexity of messages. Information overload can lead to analysis paralysis—delays, indecision, confusion, or missed opportunities due to overload. The goal is often to hinder clear decision-making, increase stress, or make it harder to distinguish important from irrelevant details.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit information overload.
                • Indicators of information overload include:
                  – Presenting an excessive amount or complexity of information, facts, data, or arguments, making it hard for the audience to process or prioritize.
                  – Using a rapid succession of updates, statistics, claims, or contradictory details that can paralyze decision-making or create confusion.
                  – Arguments that highlight or result in “paralysis by analysis,” increased hesitation, stress, or missed decisions due to information overload.
                  – Intentional mixing of relevant and irrelevant details to obscure the key message or overwhelm the audience’s attention.
                • Do **not** count as information overload:
                  – Arguments that present information clearly, concisely, or in a manageable amount, even if there are several points.
                  – Complexity or nuance that helps genuine understanding or supports careful, reasoned decision-making.
                  – Cases where the focus is on the *quality* of information rather than on overwhelming with *quantity*.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits information overload.
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
        print(f"[ERROR] Information Overload detection failed: {e}")
        return {}
