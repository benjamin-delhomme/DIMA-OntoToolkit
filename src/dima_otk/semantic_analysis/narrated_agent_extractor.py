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

from typing import List
import json
from dima_otk.utils.gpt_client import call_gpt

def extract_narrated_agents(full_text: str, model="gpt-4.1-mini") -> List[dict]:
    """
    Uses GPT to extract narrative agents mentioned in the article.
    Each agent will have:
    - "name": string (or "unknown")
    - "type": string (TBD categorization)
    """

    messages = [
        {
            "role": "system",
            "content": """
            You are a narrative structure assistant.

            Your task is to extract all **narrative agents** from the full article text.

            A **narrative agent** is any person, group, institution, or organization that:
            - Performs actions,
            - Is quoted or attributed speech,
            - Is described as responsible for something,
            - Is mentioned in the story as a social or institutional actor.

            This includes explicit names (e.g., “Joe Biden”), group terms (e.g., “police”, “activists”), or vague referents (“a woman”, “an employee”).

            For each agent you detect, return a JSON dictionary with:
            1. **"name"** – the textual phrase used to refer to this agent in the article.
               - If the name is unknown, use the best surface form in the text (e.g., “an unnamed official”, “a man”, “the driver”).
            2. **"type"** – choose **exactly one** from the following controlled ontology classes:

            ---

            **Human Agents**
            - `NarratedPerson` — generic individual
            - `NarratedPolitician` — elected, governing, or policy-setting figure
            - `NarratedJournalist` — reporter, editor, correspondent
            - `NarratedActivist` — protester, advocate, campaigner
            - `NarratedBusinessLeader` — CEO, manager, business owner
            - `NarratedAcademic` — professor, researcher, expert
            - `NarratedMilitaryFigure` — general, commander, soldier (individual)
            - `NarratedGeneralPublic` — ordinary person without notable role
               - `NarratedBystander`
               - `NarratedGeneralWorker`
            - `NarratedCriminal` — individual accused or described as criminal
            - `NarratedCelebrity` — artist, influencer, famous personality

            **Collective / Institutional Agents**
            - `NarratedOrganization` — general term for any group or entity
            - `NarratedCorporation` — commercial entity, business, or brand
            - `NarratedMediaOrganization` — newspaper, news agency, publisher
            - `NarratedGovernment` — governing body, administration
            - `NarratedInstitution` — school, hospital, court, non-profit
            - `NarratedNGO` — non-governmental advocacy group
            - `NarratedMilitary` — army, military institution (as a whole)
            - `NarratedCriminalOrganization` — gang, drug cartel, mafia
            - `NarratedTerroristOrganization` — extremist group using violence
            - `NarratedInternationalOrganization` — UN, NATO, WHO, etc.
            - `NarratedState` — geopolitical or state-level actor (e.g., “Russia”, “the US”)

            **Fallback**
            - If the role is ambiguous or unclear, return: `"type": "NarratedAgentUndecided"`

            ---

            Only include agents that play a role in the article’s events, claims, or speech acts.

            Return only a valid raw **JSON array** — one dictionary per agent.
            Do not include explanations, summaries, or markdown.
            If no agents are found, return an empty array `[]`.

            ---

            ### Example Output

            ```json
            [
              {
                "name": "Joe Biden",
                "type": "NarratedPolitician"
              },
              {
                "name": "a protester",
                "type": "NarratedActivist"
              },
              {
                "name": "New York Police Department",
                "type": "NarratedGovernment"
              },
              {
                "name": "the Times",
                "type": "NarratedMediaOrganization"
              }
            ]
            """
        },
        {
            "role": "user",
            "content": f"""Extract all narrative agents from the article below:

{full_text}"""
        }
    ]

    try:
        response = call_gpt(messages, temperature=0.3, model=model)

        # Clean response if wrapped in markdown
        if response.strip().startswith("```json"):
            response = response.strip().removeprefix("```json").removesuffix("```").strip()
        elif response.strip().startswith("```"):
            response = response.strip().removeprefix("```").removesuffix("```").strip()

        return json.loads(response)

    except Exception as e:
        print(f"❌ Failed to extract narrative agents: {e}")
        return []
