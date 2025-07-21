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
from owlready2 import World, PREDEFINED_ONTOLOGIES


INFL_IRI = "https://stratcomcoe.org/influence-mini/ontology"
DIMA_IRI = "https://m82-project.org/dima-bias/ontology"

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

def get_or_create_tech_usage(world, dima, tech_id: str,
                             technique_class_name: str,
                             explanation: str):
    """
    Create or fetch a TechniqueUsage individual,
    and link it to the punning class/individual of the technique.
    """
    full_iri = f"{dima.base_iri}{tech_id}"
    usage_ind = world.get(full_iri)
    if usage_ind:
        return usage_ind

    with dima:
        usage_ind = dima.TechniqueUsage(tech_id)  # Create the TechniqueUsage individual

        # Link to the *existing punning individual/class* (e.g., dima.NegativityBias)
        technique = dima[technique_class_name]
        usage_ind.instantiatesTechnique = [technique]

        if explanation:
            usage_ind.hasExplanation.append(explanation)

    return usage_ind

def convert_dima_analysis_article(article_id: str) -> Path:
    """Link Influence‑Mini components to techniques via usesTechnique."""
    # map IRIs to article‑specific Influence‑Mini file + DIMA TBox
    infl_tmp = Path(f"output/owl_influence-mini/tmp/{article_id}_abox_temp.owl")
    PREDEFINED_ONTOLOGIES[INFL_IRI] = str(infl_tmp.resolve())
    PREDEFINED_ONTOLOGIES[DIMA_IRI] = str(DIMA_TBOX.resolve())

    # load ontologies
    world = World()
    infl  = world.get_ontology(INFL_IRI).load()
    dima  = world.get_ontology(DIMA_IRI).load()

    usesTechnique = dima.usesTechnique

    # read bias JSON (new structure)
    path = Path(f"output/bias_analysis/article_biases_{article_id}.json")
    data = json.loads(path.read_text())
    pref = f"{article_id}_"


    # process techniques
    with dima:
        for _phase, tech_dict in data.items():
            if not isinstance(tech_dict, dict):
                continue

            for tech_name, item_list in tech_dict.items():
                tech_lc = tech_name.lower()

                for item in item_list:
                    arg_num  = item["argument_id"].split("_")[-1]
                    tech_id  = f"{article_id}_{tech_lc}_{arg_num}"  # New TechniqueUsage individual

                    # Create a TechniqueUsage instance linked to the punned Technique class/individual
                    tech_usage = get_or_create_tech_usage(
                        world, dima,
                        tech_id,
                        tech_name,  # Must match the class/individual name (e.g., "NegativityBias")
                        item.get("explanation", "")
                    )

                    # ARGUMENT
                    arg_ind = infl.world.get(f"{INFL_IRI}#{pref}{item['argument_id']}")
                    if arg_ind:
                        usesTechnique[arg_ind].append(tech_usage)

                    # OTHER COMPONENTS
                    for cid in (item.get("premise_ids", []) +
                                item.get("development_ids", []) +
                                item.get("conclusion_ids", [])):
                        comp = infl.world.get(f"{INFL_IRI}#{pref}{cid}")
                        if comp:
                            usesTechnique[comp].append(tech_usage)

    # save DIMA temp ABox (TBox + new links)
    tmp = Path(f"output/owl_dima/tmp/{article_id}_abox_temp.owl")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    dima.save(file=str(tmp))

    # merge into cumulative flat files
    _append_flat(tmp, DIMA_FULL)
    _append_flat(tmp, INFL_OUT)
    return tmp
