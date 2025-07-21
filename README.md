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

To support formal reasoning and advanced queries, DIMA-OTK maps processed articles to a structured **OWL ontology**. This approach allows us to connect and infer semantic relationships beyond what is explicitly stated in the text - **without relying on opaque machine learning models**.

#### 1. 🧱 The Influence-Mini Ontology: Core Concepts

The ontology used to structure the semantic content of articles is called **Influence-Mini**. It defines all key concepts - such as:

* `Motif`, `Argument`, `Quote`, `ParaphrasedQuote`, `NarratedAgent`, etc.
* Semantic properties like `hasText`, `hasPremise`, `hasQuote`, `mentionsInQuote`, etc.
* Class hierarchies (e.g., `ParaphrasedQuote` is a subclass of `Quote`)
* Logical relations and restrictions

This ontology is used to **semantically annotate and represent** each article’s content in a machine-readable form.

📄 The merged ontology file (TBox + individuals from articles) is saved to: `output/owl_influence-mini/influence-mini_full.owl`. Please note that reasoning is applied in-memory using the HermiT reasoner, but inferred facts may not be written to disk.

---

#### 2. 🧠 The DIMA Ontology: Annotating Bias

On top of the Influence-Mini ontology, the **DIMA ontology** is applied to identify and annotate **bias, rhetorical patterns, and manipulation techniques**.

It builds upon the semantic structure from Influence-Mini to label concepts with rhetorical indicators, bias types, or stance - enabling deeper analysis of persuasion strategies.

> ⚠️ Integration of the DIMA ontology and reasoning over it is under development and will be merged into:

```
output/owl_dima/dima_full.owl
```

Once integrated, this enables rich inferences - for example:

> **If an argument uses the technique *Negativity Bias*, and that technique is known to be part of the *Divisive Information* tactic, the tool automatically infers that the argument promotes divisive narratives.**

You can then issue SPARQL queries like the following to retrieve a full reasoning path:

```sparql
PREFIX scim: <https://stratcomcoe.org/influence-mini/ontology#>
PREFIX dima: <https://m82-project.org/dima-bias/ontology#>

SELECT DISTINCT ?argument ?tech_usage ?technique ?explanation ?tactic
       (CONCAT(
          COALESCE(?premise_text, ""), " ",
          COALESCE(?dev_text, ""), " ",
          COALESCE(?conc_text, "")
        ) AS ?combined_text)
WHERE {
  ?argument a scim:Argument ;
            dima:usesTechnique ?tech_usage ;
            dima:usesTactic ?tactic .

  ?tech_usage a dima:TechniqueUsage ;
              dima:instantiatesTechnique ?technique ;
              dima:hasExplanation ?explanation .

  OPTIONAL {
    ?premise a scim:Premise ;
             dima:usesTechnique ?tech_usage ;
             scim:hasText ?premise_text .
  }
  OPTIONAL {
    ?dev a scim:Development ;
         dima:usesTechnique ?tech_usage ;
         scim:hasText ?dev_text .
  }
  OPTIONAL {
    ?conc a scim:Conclusion ;
          dima:usesTechnique ?tech_usage ;
          scim:hasText ?conc_text .
  }
}
ORDER BY ?argument
```
### 📊 Query Result: Combined Text from Argument, Technique, and Explanation

| **Argument ID**             | **Technique Usage**               | **Technique**        | **Explanation**                                                                                             | **Tactic**              | **Combined Text (Premise + Development + Conclusion)**                                                                                                                                                                  |
|-----------------------------|------------------------------------|----------------------|-------------------------------------------------------------------------------------------------------------|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scim:9a2a4d3a26_argument_1` | `dima:9a2a4d3a26_negativitybias_1` | `dima:NegativityBias` | The argument repeatedly frames Zarnia's actions as aggressive, unauthorized, and destabilizing, emphasizing threat and negative intent without balancing neutral or positive aspects. | `dima:DivisiveInformation` | Last week's unauthorized military exercises near the Norlund border marked the third such incident this month. Observers argue that Zarnia's behavior reflects a deliberate attempt to destabilize the region. Zarnia has continued its pattern of aggressive posturing. |
| `scim:9a2a4d3a26_argument_3` | `dima:9a2a4d3a26_negativitybias_3` | `dima:NegativityBias` | This argument highlights international anxiety and punitive measures, repeatedly framing Zarnia as a threat and focusing on negative consequences. | `dima:DivisiveInformation` | International voices have begun to echo concern over Zarnia's intentions. There is growing international pressure on Zarnia due to perceived threatening behavior.                                                                 |
| `scim:c9ce7d9bb7_argument_1` | `dima:c9ce7d9bb7_negativitybias_1` | `dima:NegativityBias` | The argument repeatedly frames Velmora's actions as threats and provocations, emphasizing negative consequences and expert warnings without neutral or positive balance. | `dima:DivisiveInformation` | Last week's unauthorized military exercises near the Norlund border marked the third such incident this month. Observers argue that Zarnia's behavior reflects a deliberate attempt to destabilize the region. Zarnia has continued its pattern of aggressive posturing. |
| `scim:c9ce7d9bb7_argument_2` | `dima:c9ce7d9bb7_negativitybias_2` | `dima:NegativityBias` | The conclusion frames the situation as one where Caldria is subjected to 'deliberate intimidation,' emphasizing threat and negative intent, thus exploiting negativity bias. | `dima:DivisiveInformation` | The situation has been framed with clear indicators of tension and threat, notably highlighting deliberate intimidation as a means of establishing a negative narrative. |
| `scim:c9ce7d9bb7_argument_4` | `dima:c9ce7d9bb7_negativitybias_4` | `dima:NegativityBias` | Both premises frame the situation in negative terms (disruption, tension) without neutral or positive balance, emphasizing threat and instability to exploit negativity bias. | `dima:DivisiveInformation` | The combination of premises focuses on fear-based rhetoric, emphasizing instability and potential threat without counterbalancing positive or neutral views. |

---

### 🧠 Explanation of Results

- **Argument ID**: The unique identifier for each argument.
- **Technique Usage**: The individual representing the specific use of a cognitive technique (e.g., `Negativity Bias`).
- **Technique**: The actual technique used (e.g., `NegativityBias`).
- **Explanation**: The natural language explanation associated with the technique usage.
- **Tactic**: The inferred higher-level narrative tactic (e.g., `DivisiveInformation`).
- **Combined Text**: A concatenation of the text from any premises, developments, or conclusions linked to the argument using the technique. This is automatically generated from the relevant components.

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
