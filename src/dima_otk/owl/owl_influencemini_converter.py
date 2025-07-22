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
from rdflib import Graph, OWL
from pathlib import Path
from owlready2 import PREDEFINED_ONTOLOGIES, get_ontology, World

def influencemini_initialize_tbox():
    """
    Initialize the TBox by loading the Influence-Mini ontology from the turtle file,
    serializing it to both a temporary XML file and a full owl file.
    Also updates the PREDEFINED_ONTOLOGIES dictionary with the IRI of the ontology.
    """
    g = Graph()
    g.parse("ontologies/influence-mini.ttl", format="turtle")
    xml_out_file = Path("output/owl_influence-mini/tbox.owl")
    xml_out_file.parent.mkdir(parents=True, exist_ok=True)
    full_file = Path("output/owl_influence-mini/influence-mini_full.owl")
    full_file.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(xml_out_file), format="xml")
    g.serialize(destination=str(full_file), format="xml")

    # Set the IRI for Influence-Mini ontology in the PREDEFINED_ONTOLOGIES dictionary
    # More detail at: https://owlready2.readthedocs.io/en/v0.48/onto.html#loading-an-ontology-from-owl-files
    IRI = "https://stratcomcoe.org/influence-mini/ontology"
    PREDEFINED_ONTOLOGIES[IRI] = str(xml_out_file.resolve())

def append_to_rdf_file(rdf_fragment_path: Path, output_file: Path, format: str = "xml"):
    """
    Merges a fragment of RDF data into an output file and removes owl:imports to ensure
    the resulting file is self-contained.

    Parameters:
    rdf_fragment_path: Path to the RDF fragment to be appended.
    output_file: Path to the file where the fragment should be added.
    format: The format in which the RDF is serialized, default is 'xml'.
    """
    from rdflib import Graph

    g_main = Graph()
    if output_file.exists():
        g_main.parse(output_file, format=format) # Parse the existing output file if it exists

    g_new = Graph()
    g_new.parse(rdf_fragment_path, format=format)  # Parse the new RDF fragment

    g_main += g_new  # Merge the new fragment into the main graph

    # Remove all owl:imports triples to ensure the file is self-contained
    # Key element to avoid ontology loading issue, notably on protege (https://protege.stanford.edu/)
    g_main.remove((None, OWL.imports, None))

    # Serialize the updated graph to the output file
    g_main.serialize(destination=str(output_file), format=format)


def convert_semantic_analysis_article(article_id: str) -> Path:
    """
    Converts the semantic analysis data of an article into ABox individuals and merges
    them into the flat ontology file (influence-mini_full.owl).
    """
    IRI = "https://stratcomcoe.org/influence-mini/ontology"

    # Load the TBox once; we will add individuals directly to it
    world = World()
    tbox   = world.get_ontology(IRI).load()

    # Read the JSON produced by your semantic analysis
    data = json.loads(
        Path(f"output/semantic_analysis/article_processed_{article_id}.json")
        .read_text() # Load the article's processed semantic analysis data
    )
    art_id = data["article_id"]
    pref   = f"{art_id}_" # Prefix used for generating unique IDs for individuals (when merging everything together)

    # Create individuals inside the TBox ontology, TBOX for Terminology Box
    with tbox:
        # ARTICLE
        article = tbox.Article(f"{art_id}_article")
        article.hasId.append(f"{art_id}_article")
        article.hasHeadline.append(data["headline"])

        comp_index  = {} # Index to store components like premises, developments, conclusions
        motif_index = {}
        agent_index = {}
        quote_index = {}

        # Process the motifs and their associated arguments
        for m in data["motifs"]:
            m_ind = tbox.Motif(pref + m["motif_id"])
            m_ind.hasId.append(pref + m["motif_id"])
            m_ind.hasText.append(m["text"])
            article.hasMotif.append(m_ind)
            motif_index[m["motif_id"]] = m_ind

            for a in m["arguments"]:
                a_ind = tbox.Argument(pref + a["argument_id"])
                a_ind.hasId.append(pref + a["argument_id"])
                m_ind.hasArgument.append(a_ind)

                for p in a["premises"]:
                    p_ind = tbox.Premise(pref + p["id"])
                    p_ind.hasId.append(pref + p["id"])
                    p_ind.hasText.append(p["text"])
                    a_ind.hasPremise.append(p_ind)
                    comp_index[p["id"]] = p_ind

                for d in a["developments"]:
                    d_ind = tbox.Development(pref + d["id"])
                    d_ind.hasId.append(pref + d["id"])
                    d_ind.hasText.append(d["text"])
                    a_ind.hasDevelopment.append(d_ind)
                    comp_index[d["id"]] = d_ind

                for c in a["conclusions"]:
                    c_ind = tbox.Conclusion(pref + c["id"])
                    c_ind.hasId.append(pref + c["id"])
                    c_ind.hasText.append(c["text"])
                    a_ind.hasConclusion.append(c_ind)
                    comp_index[c["id"]] = c_ind

        # Process the quotes and link them to components and agents
        for q in data["quotes"]:
            q_cls = getattr(tbox, q["type"], tbox.Quote)
            q_ind = q_cls(pref + q["quote_id"])
            q_ind.hasText.append(q["text"])
            q_ind.hasId.append(pref + q["quote_id"])
            quote_index[q["quote_id"]] = q_ind

            # Set the quote's status if applicable
            status_ind = tbox.__dict__.get(q["status"])
            if status_ind:
                q_ind.hasQuoteStatus.append(status_ind)

            # Link quote to components if applicable
            for cid in q["maps_to_arg_components"]:
                if cid in comp_index:
                    comp_index[cid].hasQuote.append(q_ind)

            # Link quote to agents if applicable
            for aid in q["attributed_to"]:
                if aid in agent_index:
                    q_ind.isAttributedTo.append(agent_index[aid])

            # Link quote to agents that mention it
            for mid in q["mentions"]:
                if mid in agent_index:
                    q_ind.mentionsInQuote.append(agent_index[mid])

    # Save *only* the new triples to a temporary file
    temp_abox_file = Path(f"output/owl_influence-mini/tmp/{art_id}_abox_temp.owl")
    temp_abox_file.parent.mkdir(parents=True, exist_ok=True)
    tbox.save(file=str(temp_abox_file))          # includes TBox + new individuals

    # Merge the temporary ABox file into the master flat file and strip owl:imports
    append_to_rdf_file(
        rdf_fragment_path=temp_abox_file,
        output_file     = Path("output/owl_influence-mini/influence-mini_full.owl"),
        format          = "xml"
    )

    return temp_abox_file
