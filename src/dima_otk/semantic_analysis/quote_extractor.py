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

from typing import List, Dict
import json
from dima_otk.utils.gpt_client import call_gpt


def extract_quote_shells(motif_text: str, model: str = "gpt-4.1") -> list[dict]:
    """
    Step 1: Extracts basic quote information:
    - text
    - type (DirectQuote, IndirectQuote, etc.)
    - status (rhetorical role)

    Does NOT assign agents or link to components.
    """

    messages = [
        {
            "role": "system",
            "content": """
            You are a quote extraction assistant for narrative analysis.

            Your task is to extract all **semantically meaningful quotes** from a paragraph of news-style text. These include:

            - Verbatim speech in quotation marks
            - Paraphrased or indirectly reported statements attributed to individuals, officials, institutions
            - Interpretations, judgments, or rhetorical claims presented narratively, even without clear attribution

            A **quote** is any statement in the text that expresses a judgment, report, belief, policy, or rhetorical position — whether directly stated or implied through narrative framing.

            For each quote you identify, return a JSON object with the following fields:

            1. **"text"** – The full content of the quote.
               - If it’s a direct quote, reproduce it word-for-word.
               - If it’s indirect or paraphrased, reconstruct the full semantic content of the claim.
            2. **"type"** – One of:
               - `"DirectQuote"`: Verbatim citation, often in quotation marks.
               - `"IndirectQuote"`: Paraphrased but attributed (e.g., “he said the country is at risk”).
               - `"ParaphrasedQuote"`: Summary or interpretation without explicit attribution.
            3. **"status"** – The rhetorical or narrative role of the quote. Choose one of:
               - `"ReportedStatement"` – Neutral factual claim.
               - `"OfficialPosition"` – Formal stance of an institution or representative.
               - `"PersonalOpinion"` – Subjective view of an individual.
               - `"InterpretiveStatement"` – Reworded or inferred interpretation.
               - `"HypotheticalStatement"` – Imagined or speculative scenario.
               - `"Contradiction"` – Disagreement or negation of another idea.
               - `"CallToAction"` – Demand, request, or push for change.
               **Fallback**
                - If the status is ambiguous or unclear, return: `"status": "UndecidedStatement"`

            Return a list of quote dictionaries as valid raw JSON (no markdown, no explanations, no natural language). If no quotes are found, return an empty array `[]`.

            ---

            ### Examples:

            ```json
            [
              {
                "text": "We will not tolerate this kind of behavior.",
                "type": "DirectQuote",
                "status": "OfficialPosition"
              },
              {
                "text": "The minister said the protests were incited by foreign agents.",
                "type": "IndirectQuote",
                "status": "ReportedStatement"
              },
              {
                "text": "Massive events were banned, including gatherings at Times Square.",
                "type": "ParaphrasedQuote",
                "status": "InterpretiveStatement"
              }
            ]

            """
        },
        {
            "role": "user",
            "content": f"""Paragraph:
            {motif_text}

            Extract all quotes as structured JSON with the 3 fields described above."""
        }
    ]

    try:
        response = call_gpt(messages, temperature=0.3, model=model)

        if response.strip().startswith("```json"):
            response = response.strip().removeprefix("```json").removesuffix("```").strip()
        elif response.strip().startswith("```"):
            response = response.strip().removeprefix("```").removesuffix("```").strip()

        return json.loads(response)

    except Exception as e:
        print(f"❌ Failed to extract quotes (step 1): {e}")
        return []


def assign_quote_agents(motif_text: str, quote_list: list[dict], agents: list[dict], model: str = "gpt-4.1") -> list[dict]:
    """
    Step 2: For each quote in the list, add:
    - "attributed_to": agent IDs who made the quote
    - "mentions": agent IDs referenced in the quote

    Returns a new list with updated quote dictionaries.
    """

    # Format agents
    agent_list = "\n".join(
        f"- {agent['name']} (id: {agent['agent_id']})"
        for agent in agents
        if agent['name'].lower() != "unknown"
    )

    # Format quotes for display
    quote_texts = "\n".join(
        f"- Quote {i+1}: {q['text']}" for i, q in enumerate(quote_list)
    )

    messages = [
        {
            "role": "system",
            "content": """
                You are a narrative intelligence assistant.

                Your task is to analyze quotes and assign agent-level metadata using the list of known agents.

                For each quote, return:

                1. attributed_to": ID(s) of the agent(s) who provided or delivered the quote.

                   - A quote is attributed to the person or organization who explicitly **said, claimed, reported, stated, or was cited** as the source.
                   - Attribution cues may appear **before or after** the quote.
                     > e.g., "The mayor said..." (before), or "...the Post reported, citing the sheriff." (after)
                   - If a quote is introduced with “the Post reported, citing Sheriff Fucito”, it should be attributed to Sheriff Fucito, not the Post.
                   - If no such cues are present, leave "attributed_to" empty.


                2. "mentions": agent IDs who are referenced or discussed inside the quote
                   - These are agents the quote talks about, criticizes, describes, or names.
                   - Do not confuse mentions with attribution. An agent performing an action in the sentence is usually a mention, unless they are explicitly quoted.

                Use only the IDs from the provided list of agents.

                Return a raw JSON list — one dictionary per quote — in the same order.

                If no attribution or mention applies, return empty lists.

                Do not include any markdown, headings, or explanatory text — only the JSON.

                ---

                ### Examples:

                ```json
                [
                  {
                    "attributed_to": ["agent_2"],  // The Post
                    "mentions": ["agent_1"]        // Sheriff Fucito
                  },
                  {
                    "attributed_to": ["agent_1"],  // Sheriff Fucito
                    "mentions": ["agent_0"]        // police
                  }
                ]
            """
        },
        {
            "role": "user",
            "content": f"""Paragraph:
            {motif_text}

            Known agents:
            {agent_list}

            Quotes:
            {quote_texts}

            Return one result per quote in order.
            """
        }
    ]

    try:
        response = call_gpt(messages, temperature=0.3, model=model)

        if response.strip().startswith("```json"):
            response = response.strip().removeprefix("```json").removesuffix("```").strip()
        elif response.strip().startswith("```"):
            response = response.strip().removeprefix("```").removesuffix("```").strip()

        # Parse result
        agent_maps = json.loads(response)

        # Merge attribution into each quote
        for i, quote in enumerate(quote_list):
            quote["attributed_to"] = agent_maps[i].get("attributed_to", [])
            quote["mentions"] = agent_maps[i].get("mentions", [])


    except Exception as e:
        print(f"❌ Failed to assign quote agents: {e}")

    return quote_list


def link_quotes_to_components(motif_text: str, quote_list: list[dict], components: list[dict],model: str = "gpt-4.1") -> list[dict]:
    """
    Step 3: For each quote, determine which narrative components
    it refers to, paraphrases, contradicts, or supports.

    Updates each quote in-place with:
    - "maps_to_arg_components": list of narrative component IDs
    """

    if not components:
        for q in quote_list:
            q["maps_to_arg_components"] = []
        return quote_list

    component_list = "\n".join(
        f"- {c['id']}: {c['text']}" for c in components
    )

    quote_texts = "\n".join(
        f"- Quote {i+1}: {q['text']}" for i, q in enumerate(quote_list)
    )

    messages = [
        {
            "role": "system",
            "content": """
                You are a narrative reasoning assistant.

                Your task: For each QUOTE, identify which ARGUMENT COMPONENTS from the paragraph it
                **conveys, paraphrases, supports, disputes, or restates** (semantic match, not word match).

                **Argument components** = the structured narrative building blocks extracted from the paragraph:
                - Premises
                - Developments
                - Conclusions
                Each component has a unique ID (e.g., "premise_3", "development_2").

                **Mapping rule:**
                Link a quote to a component if the quote:
                • states the same claim (even with different wording),
                • paraphrases or summarizes it,
                • clearly supports or strengthens it, or
                • clearly contradicts / disputes it (negates, rejects, challenges).

                If the quote touches **multiple** components, include all relevant IDs.
                If no component meaningfully matches, return an empty list.

                **Output format:** Raw JSON array, *one object per quote, in the same order as given*.
                Each object MUST have the key `"maps_to_arg_components"` whose value is a list of component IDs (strings).

                Example:
                [
                  { "maps_to_arg_components": ["premise_1"] },
                  { "maps_to_arg_components": [] },
                  { "maps_to_arg_components": ["development_2", "conclusion_1"] }
                ]

                Return ONLY JSON. No commentary.

            """
        },
        {
            "role": "user",
            "content": f"""Paragraph:
                {motif_text}

                Narrative components:
                {component_list}

                Quotes:
                {quote_texts}

                Return a JSON array of "maps_to_arg_components" mappings, one per quote.
                """
        }
    ]

    try:
        response = call_gpt(messages, temperature=0.2, model=model)

        if response.strip().startswith("```json"):
            response = response.strip().removeprefix("```json").removesuffix("```").strip()
        elif response.strip().startswith("```"):
            response = response.strip().removeprefix("```").removesuffix("```").strip()

        links = json.loads(response)

        for i, quote in enumerate(quote_list):
            quote["maps_to_arg_components"] = links[i].get("maps_to_arg_components", [])

    except Exception as e:
        print(f"❌ Failed to link quotes to components: {e}")
        for quote in quote_list:
            quote["maps_to_arg_components"] = []

    return quote_list
