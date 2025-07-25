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

def extract_technique_te0143(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0143 – Contrast Effect (Effet de contraste).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0143 – Contrast Effect (Effet de contraste) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0143 – Contrast Effect (Effet de contraste)
                → Communicators exploit our tendency to judge or perceive an object, idea, or experience not in isolation, but in comparison to another object, idea, or experience recently encountered. The perception or evaluation of something is shifted because of what it is compared with, making it appear better, worse, bigger, smaller, more valuable, etc.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the contrast effect.
                • Indicators of contrast effect include:
                  – Presenting two or more options, objects, people, or situations in close succession or side by side, so that the evaluation of one is influenced by direct comparison with the other(s).
                  – Arguments that explicitly or implicitly encourage the audience to compare, causing the perception of one item to shift (e.g., a price appears low after seeing a much higher price).
                  – Statements emphasizing differences or highlighting contrasts to alter impressions, judgments, or choices.
                  – The key is the relative comparison: something seems better/worse or more/less, not because of its intrinsic qualities but because of what it is compared to.
                • Do **not** count as contrast effect:
                  – Arguments where an item stands out simply by being isolated or visually distinctive, without explicit or implied comparison (this is the Von Restorff Effect).
                  – Cases where memory or attention is biased toward first or last information in a sequence (these are the Primacy or Recency Effects).
                  – Influence by an initial value or reference point that colors subsequent judgments (this is Anchoring Bias).
                  – Preference for or trust in something due to repeated exposure or familiarity, not due to contrast (this is the Mere Exposure Effect).
                  – Genuine, evidence-based evaluation of each option, not biased by context or comparison.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the contrast effect.
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
        print(f"[ERROR] Contrast-effect detection failed: {e}")
        return {}
