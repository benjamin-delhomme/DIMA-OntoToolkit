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
from typing import Union, List, Tuple
from owlready2 import World, sync_reasoner_hermit, PREDEFINED_ONTOLOGIES
from rdflib import Namespace, URIRef

# Influence‑Mini
INFL_IRI = "https://stratcomcoe.org/influence-mini/ontology"
INFL_NS  = Namespace(f"{INFL_IRI}#")
INFL_PREF = "scim"

# DIMA‑bias
DIMA_IRI = "https://m82-project.org/dima-bias/ontology"
DIMA_NS  = Namespace(f"{DIMA_IRI}#")
DIMA_PREF = "dima"
DIMA_FILE_DEFAULT = Path("output/owl_dima/dima_full.owl")   # merged flat file


def query_flat_ontology(
    owl_file: Union[str, Path] = "output/owl_influence-mini/influence-mini_full.owl",
    sparql: str = "",
    *,
    reason: bool = True,
    hermit_debug: int = 0,
) -> List[Tuple]:
    """
    Query the flat Influence‑Mini ontology (+ DIMA if available).

    Parameters
    ----------
    owl_file : str | Path
        Path to influence-mini_full.owl
    sparql : str
        A full SPARQL query (can start with PREFIX).
    reason : bool
        Whether to run HermiT in-memory before querying.

    Returns
    -------
    list[tuple]
        Query result rows with QNames where possible.
    """
    infl_file = Path(owl_file).expanduser().resolve()
    if not infl_file.exists():
        raise FileNotFoundError(infl_file)

    # Register Influence‑Mini location
    PREDEFINED_ONTOLOGIES[INFL_IRI] = str(infl_file)

    # World and ontologies
    world = World()
    infl  = world.get_ontology(INFL_IRI).load()

    onto_list = [infl]

    # If DIMA merged file exists, load it too
    dima_file = DIMA_FILE_DEFAULT.expanduser().resolve()
    if dima_file.exists():
        PREDEFINED_ONTOLOGIES[DIMA_IRI] = str(dima_file)
        dima = world.get_ontology(DIMA_IRI).load()
        onto_list.append(dima)

    # Optional reasoning
    if reason:
        sync_reasoner_hermit(
            onto_list,
            infer_property_values=True,
            debug=hermit_debug,
        )

    # rdflib graph and namespace bindings
    g = world.as_rdflib_graph()
    nm = g.namespace_manager
    nm.bind(INFL_PREF, INFL_NS,  override=True)
    nm.bind(DIMA_PREF,  DIMA_NS, override=True)

    # Execute query (rdflib handles PREFIX correctly)
    rows = g.query(sparql.strip())

    # Pretty‑print QNames
    def pretty(cell):
        if isinstance(cell, URIRef):
            try:
                return nm.qname(cell)
            except Exception:
                return str(cell)
        return str(cell)

    return [tuple(pretty(c) for c in row) for row in rows]
