# DIMA-OntoToolkit

**DIMA-OntoToolkit** is a research-oriented Python pipeline for extracting narrative biases, semantic structures, and arguments from text articles. It maps these features to individuals in a formal OWL ontology.

---

## 🚀 What It Does

- Parses raw text or multiple articles from a folder
- Identifies semantic motifs (e.g. paragraphs)
- Extracts arguments, narrative agents, and quotes
- Generates an OWL file structured according to the DIMA ontology

## 🧠 Feature Extraction Pipeline

Once input text is provided, **DIMA-OntoToolkit** extracts key semantic structures before generating the final OWL file. These intermediary outputs are useful for debugging, visualization, or integration with other systems.

### 🔍 Steps in the Feature Extraction Process

1. **Headline Detection**

   - The tool attempts to identify a headline (either explicitly present or inferred via GPT).
   - If found at the top of the article, it's removed from the content for separate processing.

2. **Motif Segmentation**

   - The article content is split into **semantic motifs**, which typically correspond to paragraphs.
   - Each motif is treated as a standalone narrative segment.

3. **Argument Extraction**

   - Within each motif, the tool extracts structured **arguments** composed of:
     - `premises` (supporting facts or claims)
     - `developments` (reasoning or inference)
     - `conclusions` (final judgments)

4. **Narrative Agent Detection**

   - Entities involved in the story (e.g., nations, officials, citizens) are identified and classified into agent types like:
     - `NarratedState`
     - `NarratedPolitician`
     - `NarratedGeneralPublic`
     - `NarratedPerson`

5. **Quote Extraction**

   - Quotes are categorized by type (e.g., direct, paraphrased, interpretive).
   - Each quote is linked to the motif and argument component it supports.

#### 📄 Example: Intermediate Output

After analyzing `ex1.txt`, the following JSON was produced:

```json
{
  "article_id": "9a2a4d3a26",
  "headline": "Norlund Stands Tall Against Aggressive Zarnian Provocations",
  "motifs": [ ... ],
  "narrative_agents": [ ... ],
  "quotes": [ ... ]
}
```

This file lives under: `output/articles_processed/article_processed_<article_id>.json`

### 🧠 Ontology-Based Semantic Representation

To support formal reasoning and advanced queries, DIMA-OTK maps processed articles to a structured **OWL ontology**. This approach allows us to connect and infer semantic relationships beyond what is explicitly stated in the text — **without relying on black-box AI**.

#### 1. 🧱 The Influence-Mini Ontology: Core Concepts

The ontology used to structure the semantic content of articles is called **Influence-Mini**. It defines all key concepts — such as:

- `Motif`, `Argument`, `Quote`, `ParaphrasedQuote`, `NarratedAgent`, etc.
- Semantic properties like `hasText`, `hasPremise`, `hasQuote`, `mentionsInQuote`, etc.
- Class hierarchies (e.g., `ParaphrasedQuote` is a subclass of `Quote`)
- Logical relations and restrictions

This ontology is used to **semantically annotate and represent** each article’s content in a machine-readable form.

📄 The merged ontology file (TBox + individuals from articles), **without inference**, is saved to:
```

output/owl\_influence-mini/influence-mini\_full.owl

```

---

#### 2. 🧠 The DIMA Ontology: Annotating Bias

On top of the Influence-Mini ontology, the **DIMA ontology** is applied to identify and annotate **bias, rhetorical patterns, and manipulation techniques**.

It builds upon the semantic structure from Influence-Mini to label concepts with rhetorical indicators, bias types, or stance — enabling deeper analysis of persuasion strategies.

> ⚠️ Integration of the DIMA ontology and reasoning over it is under development and will be merged into:
```

output/owl\_dima/dima\_full.owl

````

---

### 🔎 Logical Reasoning (HermiT Inference Engine)

After the initial semantic annotations (called the ABox), the [HermiT OWL reasoner](http://www.hermit-reasoner.com/) is used to infer additional facts using **formal logic**:

- If `ParaphrasedQuote ⊆ Quote` and `X a ParaphrasedQuote`, then → `X a Quote`
- If `hasQuote ≡ inverse(isMentionedIn)` and `A hasQuote B`, then → `B isMentionedIn A`

These inferred facts are **not always written to disk**, but they are available **in memory** during SPARQL querying.

---

### 📊 Querying the Inferred Knowledge

With the ontology loaded and reasoning applied, users can issue SPARQL queries to retrieve and analyze structured information.

Here's a query that finds all quote instances (including subclassed types), their type, text, and ID:

```sparql
PREFIX scim: <https://stratcomcoe.org/influence-mini/ontology#>

SELECT ?individual ?type ?text ?id
WHERE {
  ?type rdfs:subClassOf* scim:Quote .
  ?individual a ?type .
  OPTIONAL { ?individual scim:hasText ?text . }
  OPTIONAL { ?individual scim:hasId ?id . }
}
````

This query retrieves every instance of `Quote` and its subclasses (e.g. `DirectQuote`, `ParaphrasedQuote`, `IndirectQuote`) along with any available text and identifier.

🖥️ Sample output:

```
+----------------------+-----------------------+----------------------------------------+----------------------+
| individual           | type                  | text                                   | id                   |
+======================+=======================+========================================+======================+
| scim:quote_7         | scim:DirectQuote      | "We trust our leaders..."              | 9a2a4d3a26_quote_7   |
| scim:quote_3         | scim:ParaphrasedQuote | Zarnia has continued its posturing...  | 9a2a4d3a26_quote_3   |
| ...                  | ...                   | ...                                    | ...                  |
+----------------------+-----------------------+----------------------------------------+----------------------+
```

🧠 This logic-driven querying enables structured discovery of persuasive narratives, agent references, and potential bias — all without requiring opaque machine learning models.

---

## API Key Configuration

The bias extraction tool uses the OpenAI API. To run it, you need an API key.

1. Copy the provided `.env.example` file to `.env`:

    ```bash
    cp .env.example .env
    ```

2. Open `.env` and replace the placeholder with your actual OpenAI API key:

    ```env
    OPENAI_API_KEY=sk-your-real-api-key-here
    ```

3. **Do not commit this file.** It's already excluded via `.gitignore`.

The application will automatically load the key from `.env`.

---

## Quick Start (Using Docker)

### Prerequisites
- [Docker](https://www.docker.com/) installed
- `.env` file with your OpenAI API key (see above)

### 1. Build the Docker image

```bash
./build-docker.sh
```

### 2. Run the tool with your own input text

```bash
./run-docker.sh -t "You article text goes here."
```

OWL output will be saved to: output/

---

## Manual Docker Usage (No Scripts)

If you'd rather not use the helper scripts, you can build and run the container manually using Docker:

### 1. Build the Docker image

```bash
docker build -t dima-otk .
```

### 2. Run the tool with a text input

```bash
docker run --rm \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/.env:/app/.env" \
  -v "$(pwd)/articles:/app/articles" \
  dima-otk \
  python -m dima_otk.dima_otk -t "Your input text goes here."
```

---

## Origin and Attribution

This project builds on [M82-project/DIMA](https://github.com/M82-project/DIMA), an open-source framework licensed under the Apache License 2.0.

We have extended the original work to:
- Formalize the bias model as an OWL ontology
- Develop tools for populating this ontology from unstructured text
- Enable semantic analysis and knowledge graph generation

The full license text is provided in the `LICENSE` file.

## Third-Party Libraries

This project uses the following third-party libraries:

- [Owlready2](https://github.com/pwin/OWLReady2) – GNU LGPL v3
- [ftfy](https://github.com/rspeer/python-ftfy) – MIT License
- [requests](https://github.com/psf/requests) – Apache License 2.0
- [tabulate](https://github.com/astanin/python-tabulate) – MIT License

You can find copies of the relevant licenses in the respective repositories or license documentation.

## Third‑Party Components

This project uses the following third-party components:

- [HermiT OWL 2 Reasoner](http://www.hermit-reasoner.com/)
  Copyright © 2008–2025 University of Oxford & contributors
  License: GNU Lesser General Public License v3.0 or later
  Source code: https://hermit-reasoner.com
