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


IRI     = "https://stratcomcoe.org/influence-mini/ontology"
NS      = Namespace(f"{IRI}#")
PREFIX  = "scim"


def query_flat_ontology(
    owl_file: Union[str, Path],
    sparql: str,
    *,
    reason: bool = True,
    hermit_debug: int = 0
) -> List[Tuple]:
    owl_file = Path(owl_file).expanduser().resolve()
    if not owl_file.exists():
        raise FileNotFoundError(owl_file)

    # Register local file for the real ontology IRI
    PREDEFINED_ONTOLOGIES[IRI] = str(owl_file)

    world = World()
    onto  = world.get_ontology(IRI).load()

    if reason:
        sync_reasoner_hermit(
            [onto],
            infer_property_values=True,
            debug=hermit_debug,
        )

    # rdflib ConjunctiveGraph with all triples
    g = world.as_rdflib_graph()

    # Bind friendly prefix
    g.namespace_manager.bind(PREFIX, NS, override=True)

    rows = g.query(sparql)

    # ── Convert every URIRef to its QName (im:xxx) ───────────────────
    def pretty(cell):
        if isinstance(cell, URIRef):
            try:
                return g.namespace_manager.qname(cell)
            except Exception:
                return str(cell)
        return str(cell)

    return [tuple(pretty(c) for c in row) for row in rows]
