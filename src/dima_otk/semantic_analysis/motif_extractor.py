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

import re
from typing import List, Dict

def split_into_paragraphs(text: str) -> List[str]:
    """
    Splits the article content into paragraphs based on double line breaks.
    This forms the basis for identifying Motifs in the ontology.
    """
    # Normalize all line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Split on 2+ line breaks (marks paragraph breaks)
    return [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]


def identify_motifs(paragraphs: List[str]) -> List[Dict]:
    """
    Takes a list of paragraph strings and returns a list of motifs.
    Each motif is assigned a unique motif ID and contains the original text.

    In news articles, each paragraph is assumed to be a semantic Motif.

    Returns:
        List of dictionaries:
        [
            {
                "id": "motif_0",
                "text": "...original paragraph text..."
            },
            ...
        ]
    """
    motifs = []
    for i, para in enumerate(paragraphs):
        motifs.append({
            "id": f"motif_{i}",
            "text": para.strip()
        })
    return motifs
