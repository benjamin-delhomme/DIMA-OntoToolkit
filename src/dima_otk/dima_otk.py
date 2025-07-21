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
from pathlib import Path

from dima_otk.utils.article import get_article_id, print_article_summary

from dima_otk.semantic_analysis.headline_logic import get_article_headline
from dima_otk.semantic_analysis.motif_logic import get_motifs_from_article
from dima_otk.semantic_analysis.argument_logic import get_arguments_from_motifs
from dima_otk.semantic_analysis.narrated_agent_logic import get_narrated_agents
from dima_otk.semantic_analysis.quote_logic import get_quotes_for_article

from dima_otk.bias_analysis.biases_logic import get_biases_from_article

from dima_otk.owl.owl_influencemini_converter import influencemini_initialize_tbox, convert_semantic_analysis_article

from dima_otk.owl.owl_dima_converter import dima_initialize_tbox, convert_dima_analysis_article

def clean_flat_ontology_files():
    """
    Delete the contents of the flat merged OWL files to prevent
    duplication across runs.
    """
    paths = [
        Path("output/owl_dima/dima_full.owl"),
        Path("output/owl_influence-mini/influence-mini_full.owl"),
    ]

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")  # clears file content

def save_json(data, output_dir, filename_prefix, article_id, step_description):
    output_path = Path(output_dir) / f"{filename_prefix}_{article_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[{step_description}] JSON saved to: {output_path}")
    return output_path

class DimaOTK:
    def __init__(self, rebuild_cache: bool = False):
        self.rebuild_cache = rebuild_cache
        print(f"[INIT] DimaOTK initialized (rebuild_cache={self.rebuild_cache})")
        clean_flat_ontology_files()
        influencemini_initialize_tbox()
        dima_initialize_tbox()

    def run(self, input_text: str):
        """
        Orchestrates the bias extraction and OWL generation pipeline.

        Args:
            input_text (str): Raw text input to analyze

        Returns:
            str: Path to generated OWL file
        """
        print("[INFO] Starting bias extraction pipeline...")

        # Step 0: Generate a unique article ID, extract (or generate) the headline and separate it from the main content if present.
        article_id = get_article_id(input_text)
        headline, content = get_article_headline(input_text, article_id)

        article = {
            "id": article_id,
            "headline": headline,
            "content": content
        }

        print_article_summary(article_id, headline, content)

        # Step 1: Extract semantic motifs (paragraphs)
        print("[STEP 1] Extracting semantic motifs from article...")
        motifs = get_motifs_from_article(article)
        print(f"[STEP 1] Found {len(motifs)} motifs.")

        # Step 2: Extract arguments (Premises, Developments, Conclusions)
        print("[STEP 2] Extracting arguments from motifs...")
        motif_argument_data = get_arguments_from_motifs(motifs, article)
        print(f"[STEP 2] Extracted arguments for {len(motif_argument_data)} motifs.")

        # Step 3: Extract narrated agents
        print("[STEP 3] Extracting narrated agents...")
        agents = get_narrated_agents(motif_argument_data, article)
        print(f"[STEP 3] Identified {len(agents)} narrated agents.")

        # Step 4: Extract quotes
        print("[STEP 4] Extracting quotes...")
        quotes = get_quotes_for_article(motif_argument_data, agents, article)
        print(f"[STEP 4] Found {len(quotes)} quotes.")

        print("[STEP 5] Merging Semantic Analysis Results...")
        # Step 5: Save structured result
        processed_article = {
            "article_id": article_id,
            "headline": headline,
            "motifs": motif_argument_data,
            "narrated_agents": agents,
            "quotes": quotes
        }

        save_json(processed_article, "output/semantic_analysis", "article_processed", article_id, "STEP 5")

        # Step 6: Extract biases
        print("[STEP 6] Extracting DIMA Biases...")
        biases = get_biases_from_article(processed_article)

        save_json(biases, "output/bias_analysis", "article_biases", article_id, "STEP 6")

        # Step 7  :  Convert semantic‑analysis JSON ➜ OWL Influence Mini ABox
        print("[STEP 7] Converting semantic analysis to OWL ABox…")
        influence_mini_abox_file = convert_semantic_analysis_article(article_id)
        print(f"[STEP 7] Article {article_id} ABox written to {influence_mini_abox_file}")

        # Step 8  :  Convert dima JSON ➜ OWL Dima ABox + OWL Influence Mini ABox
        print("[STEP 8] Converting semantic analysis to OWL ABox and merging with the InfluenceMini OWL…")
        convert_dima_analysis_article(article_id)
