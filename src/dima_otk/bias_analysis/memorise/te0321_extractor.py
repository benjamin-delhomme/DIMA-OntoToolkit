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

def extract_technique_te0321(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0321 – Implicit Stereotype (Stéréotype implicite).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0321 – Implicit Stereotype (Stéréotype implicite) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0321 – Implicit Stereotype (Stéréotype implicite)
                → Communicators exploit the audience’s unconscious, automatic associations between social groups (race, gender, profession, nationality, etc.) and specific traits or behaviors—even if those associations are not overtly stated or explicitly endorsed.
                → The key feature is the presence of implied, background assumptions about a group, operating without conscious awareness and not presented as explicit or reasoned claims.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit implicit stereotypes.
                • Indicators of implicit stereotype include:
                  – Statements or framing that suggest a trait, behavior, or characteristic is typical of a group, without explicit claim or argument.
                  – Descriptions or narratives that guide the audience to unconsciously associate a group with specific qualities (positive or negative) through context, word choice, or example selection.
                  – Reliance on learned social associations or patterns, rather than overt generalizations or deliberate prejudice.
                  – The effect is subtle, indirect, and usually not acknowledged by the communicator.
                • Do **not** count as implicit stereotype:
                  – Explicitly stated, acknowledged, or argued group stereotypes or prejudices (these are explicit stereotypes/prejudices, not implicit).
                  – Reasoned discussion of group differences with supporting data and transparent argumentation.
                  – Open advocacy of negative or positive qualities about a group.
                  – General positive or negative framing about events or policies, unless it relies on hidden group assumptions.
                  – Any direct mention of conscious belief, explicit bias, or overt endorsement of a stereotype.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits implicit stereotype.
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
        print(f"[ERROR] Implicit stereotype detection failed: {e}")
        return {}
