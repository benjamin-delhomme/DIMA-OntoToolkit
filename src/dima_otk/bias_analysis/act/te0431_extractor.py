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

def extract_technique_te0431(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0431 – Omission Bias (Biais d'omission).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0431 – Omission Bias (Biais d'omission) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0431 – Omission Bias (Biais d'omission)
                → Communicators exploit our tendency to judge harmful outcomes resulting from actions as worse or more blameworthy than similar outcomes resulting from inaction. Omission bias leads people to view harms caused by doing something as less acceptable than harms caused by doing nothing, even if the results are equally bad or worse.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit omission bias.
                • Indicators of omission bias include:
                  – Judging or portraying harmful outcomes caused by *actions* as more serious, immoral, or risky than similar outcomes caused by *inaction*.
                  – Arguments where people are discouraged from acting or making changes because acting is seen as more blameworthy, even if doing nothing could cause equal or greater harm.
                  – Statements that excuse or minimize the impact of negative consequences when they result from inaction.
                  – Emphasis on the risks or moral implications of doing something, without equal consideration for the risks of doing nothing.
                • Do **not** count as omission bias:
                  – Arguments where actions and inactions are evaluated fairly, or where the best choice is justified by evidence, not by simply favoring inaction.
                  – Preference for inaction due to clear evidence or rational decision-making, not just because action is viewed as inherently worse.
                  – Arguments based on risk assessment or cost-benefit analysis, not on the moral or emotional weight of action versus inaction.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits omission bias.
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
        print(f"[ERROR] Omission-bias detection failed: {e}")
        return {}
