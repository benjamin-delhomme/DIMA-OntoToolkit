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

def extract_technique_te0251(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0251 – False Consensus Effect (Effet de faux consensus).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0251 – False Consensus Effect (Effet de faux consensus) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0251 – False Consensus Effect (Effet de faux consensus)
                → Communicators exploit our tendency to assume that our own beliefs, opinions, or behaviors are more widely shared or “normal” than they really are.
                → The technique exaggerates the extent to which a particular viewpoint, value, or action is common, natural, or universally accepted—often to legitimize the claim or marginalize dissent.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the false consensus effect.
                • Indicators of the false consensus effect include:
                  – Phrases suggesting that most people, “everyone,” or the majority agree with the viewpoint (e.g., “everyone knows,” “most people believe,” “as we all think,” “naturally, people support...”).
                  – Assumptions that the audience already agrees or that dissent is rare or illegitimate.
                  – Implying that the described belief or behavior is widespread, typical, or “normal,” even without supporting evidence.
                  – Appeals to conformity or group identity to reinforce the speaker’s perspective.
                • Do **not** count as false consensus effect:
                  – Claims based on actual cited evidence (e.g., polls, surveys, statistics).
                  – Recognizing diversity of opinion or explicitly stating minority views.
                  – Statements limited to “some people think...” or “it’s possible that...”
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the false consensus effect.
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
        print(f"[ERROR] False consensus detection failed: {e}")
        return {}
