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
def extract_technique_te0332(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0332 – Mere Exposure Effect (Effet de simple exposition).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0332 – Mere Exposure Effect (Effet de simple exposition) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0332 – Mere Exposure Effect (Effet de simple exposition)
                → Communicators exploit our tendency to develop a preference or positive feeling for something simply because we have been exposed to it repeatedly over time, regardless of its actual quality or value. The effect is about growing familiarity and comfort through repeated exposure, not about recency or first impressions.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the mere exposure effect.
                • Indicators of mere exposure effect include:
                  – Repeated mention, appearance, or reference to a concept, product, person, or idea, making it feel increasingly familiar, trustworthy, or likable to the audience.
                  – Claims or implications that something is good, safe, or preferable simply because it has been seen or heard often, or is “what people are used to.”
                  – Appeals to positive feelings or trust based only on frequent exposure, not on evidence, novelty, or unique merit.
                  – Slogans, brands, people, or messages presented many times, or highlighted as “always present” or “regularly seen.”
                • Do **not** count as mere exposure effect:
                  – Arguments that make the most recent or last-presented information seem especially important or decisive, regardless of how often it was mentioned (this is the Recency Effect).
                  – Arguments that claim the first or initial information received has a lasting or anchoring effect on perception or judgment (this is the Primacy Effect).
                  – Preference for something because of evidence, novelty, uniqueness, or a rational comparison, not because of growing familiarity.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the mere exposure effect.
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
        print(f"[ERROR] Mere-exposure effect detection failed: {e}")
        return {}
