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

def extract_technique_te0142(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0142 – Anchoring Bias (Biais d’ancrage).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0142 – Anchoring Bias (Biais d’ancrage) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0142 – Anchoring Bias (Biais d’ancrage)
                → Communicators exploit our tendency to rely too heavily on the first piece of information offered (the "anchor") when making decisions or judgments. Subsequent evaluations are biased toward this initial value, reference point, or impression, even if new information is provided later.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit anchoring bias.
                • Indicators of anchoring bias include:
                  – Presenting a first value, fact, estimate, or opinion that serves as a reference point for all subsequent judgments, regardless of its actual relevance or accuracy.
                  – Arguing that later estimates or perceptions are shifted toward this initial anchor, even when additional information is available.
                  – Statements or framing that make it difficult to adjust away from an initial impression or number, leading to persistent influence over time.
                  – Use of arbitrary or even obviously incorrect starting points that nevertheless sway subsequent reasoning.
                • Do **not** count as anchoring bias:
                  – Arguments that simply emphasize the *first* information as memorable or shaping overall perception (this is the Primacy Effect, which is about memory, not reference point).
                  – Cases where judgments change appropriately as new evidence is considered, showing adjustment away from the initial value.
                  – Influence due to direct comparison with another item just observed (this is the Contrast Effect, not anchoring).
                  – Arguments that rely on cumulative information or overall evaluation, not a single reference point.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits anchoring bias.
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
        print(f"[ERROR] Anchoring-bias detection failed: {e}")
        return {}
