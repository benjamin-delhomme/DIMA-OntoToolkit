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

def extract_technique_te0151(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0151 – Distinction Bias (Biais de distinction).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0151 – Distinction Bias (Biais de distinction) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0151 – Distinction Bias
                → Communicators exploit our tendency to overvalue the differences between two or more options when they are presented together (joint evaluation), making distinctions appear larger or more important than they would seem if each option were considered separately.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit distinction bias.
                • Indicators of distinction bias include:
                  – Presenting two or more options, products, or situations side by side for direct comparison, focusing on small or subtle differences.
                  – Suggesting that even minor differences are crucial or decisive, when these differences would be much less important if options were evaluated alone.
                  – Arguments in which the act of *simultaneous* comparison exaggerates how different the options really are.
                • Do **not** count as distinction bias:
                  – Arguments that involve perception shifted by comparison with a reference point, anchor, or a previous/surrounding context (this is the Contrast Effect).
                  – Situations where the evaluation is about how something *seems better or worse because of* what it’s compared to, regardless of whether options are side-by-side or in sequence (again, this is Contrast Effect, not distinction bias).
                  – Arguments where real, meaningful differences are present and would matter in both joint and separate evaluation.
                  – Cases where differences are highlighted for practical, evidence-based decision-making, not for the sake of comparison itself.
                  – Influence due to isolation or standing out from a group (Von Restorff Effect).
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits distinction bias.
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
        print(f"[ERROR] Distinction bias detection failed: {e}")
        return {}
