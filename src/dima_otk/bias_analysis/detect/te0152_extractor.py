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

def extract_technique_te0152(argument_text: str, model: str = "gpt-4.1") -> dict:
    """
    Detects TE0152 – Weber-Fechner Law (Loi de Weber-Fechner).
    Returns a JSON verdict with bias_detected / excerpts / explanation.
    """

    messages = [
        {
            "role": "system",
            "content": """
                You are an influence‑operations analyst.
                Your single mission: detect Technique TE0152 – Weber-Fechner Law (Loi de Weber-Fechner) in each argument provided.

                ======== WHAT TO DETECT =================================================
                Technique TE0152 – Weber-Fechner Law (Loi de Weber-Fechner)
                → Communicators exploit our tendency to perceive differences not in absolute terms, but as proportional to the intensity or magnitude of the original stimulus. The bigger or stronger the context, the greater the change required for us to notice a difference. This law is often used to hide changes or make adjustments seem less significant by raising the overall intensity.

                ======== KEY ELEMENTS ===================================================
                • Motif — In a text, the equivalent of a paragraph: a recurring theme or idea that groups one or more arguments.
                • Argument — A cluster of narrative claims forming a line of reasoning, judgment, or persuasion. An argument may include:
                  – Premises      : factual claims, assumptions, or context‑setting statements that support reasoning.
                  – Developments  : interpretive or inferential steps bridging premises to conclusions.
                  – Conclusions   : final judgments, stances, or main claims the narrative wishes to convey.

                ======== REASONING GUIDANCE =============================================
                • Judge each argument independently; multiple arguments in the same motif may or may not exploit the Weber-Fechner law.
                • Indicators of Weber-Fechner law usage include:
                  – Emphasizing how differences or changes become less perceptible as the overall level (price, sound, intensity, etc.) increases.
                  – Arguments that minimize or “hide” changes or negative impacts by embedding them within a larger, more intense, or more complex context.
                  – Use of messaging that suggests “a small change won’t be noticed” because the baseline is already high or intense.
                  – Techniques that manipulate the scale or intensity of information, so incremental changes feel less dramatic.
                • Do **not** count as Weber-Fechner law:
                  – Arguments focused on comparing differences between options as more or less important (Distinction Bias).
                  – Influence due to a previous reference point or explicit comparison (Contrast Effect or Anchoring).
                  – Preference created by repetition or familiarity (Mere Exposure Effect).
                  – Cases where the change is clearly and equally perceptible at any scale.
                • An argument without these indicators should be marked as no‑bias even if neighbouring arguments are biased.

                ======== TASK ===========================================================

                The user will supply one motif whose arguments are already grouped (each with its own Premises, Developments, Conclusions).

                For every argument:
                • Decide whether it exploits the Weber-Fechner law.
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
        print(f"[ERROR] Weber-Fechner law detection failed: {e}")
        return {}
