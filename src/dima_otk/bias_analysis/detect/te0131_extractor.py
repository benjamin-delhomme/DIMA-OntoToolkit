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

def extract_technique_te0131(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0131 – Bizarreness Effect Bias.
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0131 – Bizarreness Effect in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0131 – Bizarreness Effect
                → Communicators exploit our tendency to notice and remember information that is strange, outlandish, illogical, or highly implausible—not simply different or distinctive.
                → The “bizarreness effect” comes from the inherent weirdness or improbability of the content itself, not from how it is presented or set apart.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                – Premises : factual claims, assumptions, or context‑setting statements that support reasoning.
                – Developments : interpretive or inferential steps bridging premises to conclusions.
                – Conclusions : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the bizarreness effect.
                • Indicators of the bizarreness effect include:
                – Emphasis on events, examples, or claims that are highly unusual, implausible, impossible, or absurd given the context.
                – Use of vivid, bizarre, or surreal details that would strike most audiences as strange or illogical.
                – Analogies or comparisons that highlight oddity or absurdity.
                – The “attention-grabbing” quality is due to what is being described, not merely because it’s isolated or contrasted.
                • Do not count as bizarreness:
                – Arguments that simply stand out because of formatting, color, or structural contrast (see Von Restorff Effect instead).
                – Arguments that are merely different in opinion or style, unless the content itself is weird or outlandish.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the bizarreness effect.
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
        print(f"[ERROR] Negativity‑bias detection failed: {e}")
        return {}
