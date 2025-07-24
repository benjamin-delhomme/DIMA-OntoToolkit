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

def extract_technique_te0261(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0261 – Hindsight Bias (Biais rétrospectif).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0261 – Hindsight Bias (Biais rétrospectif) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0261 – Hindsight Bias (Biais rétrospectif)
                → Communicators exploit our tendency to view past events as more predictable than they actually were. After an event, people claim that the outcome was obvious or that they “knew it all along,” even if it was not clear beforehand.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit hindsight bias.
                • Indicators of hindsight bias include:
                  – Statements that present outcomes as having been predictable or inevitable after the fact.
                  – Claims that warning signs, signals, or patterns were clear and should have led to a different decision or response.
                  – Use of phrases suggesting that the result was “obvious,” “foreseeable,” or “should have been expected.”
                  – Overestimation of one’s ability (or the audience’s ability) to have known or predicted the event’s outcome in advance.
                  – In conspiracy narratives, emphasis on supposedly ignored “signs” or “clues” that are highlighted only after the event.
                • Do not count as hindsight bias:
                  – Genuine foresight, if it can be demonstrated to have been expressed before the event.
                  – Claims based on newly available information that was not accessible before the outcome.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits hindsight bias.
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
        print(f"[ERROR] Hindsight-bias detection failed: {e}")
        return {}
