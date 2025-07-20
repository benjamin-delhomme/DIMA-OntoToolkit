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
from rdflib import Graph
from pathlib import Path
from owlready2 import PREDEFINED_ONTOLOGIES, get_ontology, World

def influencemini_initialize_tbox():
    g = Graph()
    g.parse("ontologies/influence-mini.ttl", format="turtle")
    xml_out_file = Path("output/owl_influence-mini/tbox.owl")
    xml_out_file.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(xml_out_file), format="xml")
    IRI = "https://stratcomcoe.org/influence-mini/ontology"
    PREDEFINED_ONTOLOGIES[IRI] = str(xml_out_file.resolve())

def convert_semantic_analysis_article(article_id: str) -> Path:
    IRI = "https://stratcomcoe.org/influence-mini/ontology"

    # load world and TBox
    world = World()
    tbox = world.get_ontology(IRI).load()

    # create ABox ontology that imports the TBox
    abox_iri = f"http://example.org/influence-mini/abox/{article_id}"
    abox = world.get_ontology(abox_iri)
    abox.imported_ontologies.append(tbox)

    # load JSON
    data = json.loads(Path(f"output/semantic_analysis/article_processed_{article_id}.json").read_text())
    art_id = data["article_id"]
    pref = f"{art_id}_"

    with abox:
        # create Article
        article = tbox.Article(f"{art_id}_article")
        article.hasId.append(f"{art_id}_article")
        article.hasHeadline.append(data["headline"])

        # init caches
        comp_index = {}
        motif_index = {}
        agent_index = {}
        quote_index = {}

        # create Motifs and Arguments
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

        # create Narrated Agents
        for ag in data["narrated_agents"]:
            cls = tbox.__dict__.get(ag["type"], tbox.NarratedAgent)
            ag_ind = cls(pref + ag["agent_id"])
            ag_ind.hasId.append(pref + ag["agent_id"])
            ag_ind.hasName.append(ag["name"])
            agent_index[ag["agent_id"]] = ag_ind

        # create Quotes
        for q in data["quotes"]:
            q_cls = tbox.__dict__.get(q["type"], tbox.Quote)
            q_ind = q_cls(pref + q["quote_id"])
            q_ind.hasText.append(q["text"])
            q_ind.hasId.append(pref + q["quote_id"])
            quote_index[q["quote_id"]] = q_ind

            status_ind = tbox.__dict__.get(q["status"])
            if status_ind:
                q_ind.hasQuoteStatus.append(status_ind)

            for cid in q["maps_to_arg_components"]:
                if cid in comp_index:
                    comp_index[cid].hasQuote.append(q_ind)

            for aid in q["attributed_to"]:
                if aid in agent_index:
                    q_ind.isAttributedTo.append(agent_index[aid])
            for mid in q["mentions"]:
                if mid in agent_index:
                    q_ind.mentionsInQuote.append(agent_index[mid])

    # save ABox
    out_file = Path(f"output/owl_influence-mini/{art_id}_abox.owl")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    abox.save(file=str(out_file))
    return out_file
