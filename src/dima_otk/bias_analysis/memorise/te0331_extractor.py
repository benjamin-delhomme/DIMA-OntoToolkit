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
def extract_technique_te0331(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0331 – Recency Effect (Effet de récence).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0331 – Recency Effect (Effet de récence) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0331 – Recency Effect (Effet de récence)
                → Communicators exploit our tendency to give disproportionate weight or importance to the most recent information received. Recency effect occurs when the last facts, statements, or events presented are treated as the most influential on memory, judgments, or decisions—often overshadowing or crowding out earlier information, even if the earlier content is equally relevant.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the recency effect.
                • Indicators of recency effect include:
                  – Highlighting, emphasizing, or repeating the most recent facts, events, or opinions as decisive, while minimizing or omitting earlier information.
                  – Structuring arguments so that the last claim, update, or dramatic point is presented as the most significant or persuasive.
                  – Explicit references to "the latest," "most recent," or "just announced" information being more important for judgment or action.
                  – Suggesting that what comes last should guide decisions or impressions, regardless of prior content.
                • Do **not** count as recency effect:
                  – Arguments that build preference for an idea, brand, or concept because the audience has seen or heard it frequently over time, creating a sense of familiarity or trust through repeated exposure (this is known as the Mere Exposure Effect).
                  – Arguments about the fading or disappearance of negative emotions or memories over time (that is Fading Affect Bias, not recency).
                  – Cases where all information is summarized or compared fairly, or where a chronological sequence is presented without giving special importance to the latest item.
                  – Arguments where the *first* information presented is described as having a lasting or disproportionate impact on perception or memory, shaping the audience’s view because it came first (this is known as the Primacy Effect).
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.


                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the recency effect.
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
        print(f"[ERROR] Recency-effect detection failed: {e}")
        return {}
