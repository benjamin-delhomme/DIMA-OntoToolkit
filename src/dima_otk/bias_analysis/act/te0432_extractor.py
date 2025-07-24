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

def extract_technique_te0432(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0432 – Status Quo Bias (Biais du statu quo).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0432 – Status Quo Bias (Biais du statu quo) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0432 – Status Quo Bias (Biais du statu quo)
                → Communicators exploit our tendency to prefer things to stay the same, seeing any change as riskier, less desirable, or more harmful than maintaining the current state—even when change could bring equal or greater benefits. Status quo bias leads people to resist change, often overestimating the potential downsides and underestimating the possible advantages of new options.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit status quo bias.
                • Indicators of status quo bias include:
                  – Arguments that frame keeping things as they are as the safest, least risky, or most natural choice, without objectively weighing the pros and cons of alternatives.
                  – Statements that emphasize the dangers or inconveniences of change, while downplaying or ignoring the risks or problems of maintaining the current situation.
                  – Preference for current practices, systems, or policies simply because they are familiar or established, not because they are clearly superior.
                  – Claims that reinforce inertia or resistance to change, treating it as inherently negative or threatening.
                • Do **not** count as status quo bias:
                  – Arguments that support the current situation based on evidence, clear benefits, or rational analysis, not just because it is the default.
                  – Preference for the status quo that is justified by new information, necessity, or legitimate risk assessment.
                  – Arguments that propose change and analyze its impacts fairly, without unjustified preference for inaction.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits status quo bias.
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
        print(f"[ERROR] Status-quo bias detection failed: {e}")
        return {}
