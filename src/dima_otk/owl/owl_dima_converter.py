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

from pathlib import Path
import json, types
from rdflib import Graph, OWL
from owlready2 import World, PREDEFINED_ONTOLOGIES, Thing


INFL_IRI = "https://stratcomcoe.org/influence-mini/ontology"
DIMA_IRI = "https://stratcomcoe.org/dima-bias/ontology"

DIMA_TBOX = Path("output/owl_dima/tbox.owl")
DIMA_DIR  = DIMA_TBOX.parent
DIMA_FULL = DIMA_DIR / "dima_full.owl"
INFL_OUT  = Path("output/owl_influence-mini/influence-mini_full.owl")

def _ttl_to_owl(ttl: Path, owl: Path, iri: str):
    owl.parent.mkdir(parents=True, exist_ok=True)
    g = Graph(); g.parse(ttl, format="turtle")
    g.serialize(owl, format="xml")
    PREDEFINED_ONTOLOGIES[iri] = str(owl.resolve())

def dima_initialize_tbox():
    _ttl_to_owl(Path("ontologies/dima-bias.ttl"), DIMA_TBOX, DIMA_IRI)
    DIMA_FULL.parent.mkdir(parents=True, exist_ok=True)
    if not DIMA_FULL.exists():
        DIMA_FULL.write_text("")

def _append_flat(src: Path, dest: Path, fmt: str = "xml"):
    g_dest = Graph()
    if dest.exists() and dest.stat().st_size:       # ← only parse if non‑empty
        g_dest.parse(dest, format=fmt)

    g_src = Graph()
    g_src.parse(src, format=fmt)

    g_dest += g_src
    g_dest.remove((None, OWL.imports, None))
    g_dest.serialize(dest, format=fmt)

def convert_dima_analysis_article(article_id: str) -> Path:
    """Link Influence‑Mini components to techniques via usesTechnique."""
    # 1. map IRIs to article‑specific Influence‑Mini file + DIMA TBox
    infl_tmp = Path(f"output/owl_influence-mini/tmp/{article_id}_abox_temp.owl")
    PREDEFINED_ONTOLOGIES[INFL_IRI] = str(infl_tmp.resolve())
    PREDEFINED_ONTOLOGIES[DIMA_IRI] = str(DIMA_TBOX.resolve())

    # 2. load ontologies
    world = World()
    infl  = world.get_ontology(INFL_IRI).load()
    dima  = world.get_ontology(DIMA_IRI).load()

    usesTechnique = dima.usesTechnique

    # 3. read bias JSON (new structure)
    path = Path(f"output/bias_analysis/article_biases_{article_id}.json")
    data = json.loads(path.read_text())
    pref = f"{article_id}_"

    # 4. process techniques
    with dima:
        for _phase, tech_dict in data.items():
            if not isinstance(tech_dict, dict):
                continue  # skip empty lists        # Detect / Inform / ...
            for tech_code, item_list in tech_dict.items():
                # ensure the technique individual exists
                tech_ind = dima.__dict__.get(tech_code)
                if tech_ind is None:
                    tech_ind = dima.Technique(tech_code)

                for item in item_list:
                    # argument explanation
                    arg_iri = f"{INFL_IRI}#{pref}{item['argument_id']}"
                    arg_ind = infl.world.get(arg_iri)
                    if arg_ind:
                        usesTechnique[arg_ind].append(tech_ind)
                        if "explanation" in item:
                            arg_ind.hasExplanation.append(item["explanation"])

                    # other components
                    for cid in item.get("premise_ids", []) + \
                               item.get("development_ids", []) + \
                               item.get("conclusion_ids", []):
                        comp = infl.world.get(f"{INFL_IRI}#{pref}{cid}")
                        if comp:
                            usesTechnique[comp].append(tech_ind)

    # 5. save DIMA temp ABox (TBox + new links)
    tmp = Path(f"output/owl_dima/tmp/{article_id}_abox_temp.owl")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    dima.save(file=str(tmp))

    # 6. merge into cumulative flat files
    _append_flat(tmp, DIMA_FULL)
    _append_flat(tmp, INFL_OUT)
    return tmp
