# DIMA-OntoToolkit

**DIMA-OntoToolkit** is a research-oriented Python pipeline for extracting narrative biases, rhetorical techniques, and semantic structures from text articles. It applies the DIMA cognitive warfare framework along with a lightweight semantic model of narrative content called **Influence-Mini**, mapping all extracted features to individuals in a formal OWL ontology.

Learn more about the DIMA cognitive framework here:  
> [The DIMA Framework – An Attempt to Build a Tool for Cognitive Warfare](https://medium.com/@Cybart/the-dima-framework-an-attempt-to-build-a-tool-for-cognitive-warfare-e1ad3af76c48)

---

## 📘 What It Does

- Parses raw text or multiple articles from a folder
- Identifies semantic motifs (e.g. paragraphs)
- Extracts arguments, narrative agents, and quotes
- Generates an OWL file structured according to the DIMA ontology
- Use Hermit Reasoner and runs SPARQL queries on the extracted data.
---

## 🔍 Feature Extraction Pipeline

Once input text is provided, **DIMA-OntoToolkit** extracts key semantic structures then DIMA techniques before generating the final OWL files. These intermediary outputs are useful for debugging, visualization, or integration with other systems.

### 🪛 Steps in the Influence-Mini Feature Extraction Process

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

### 🧩 DIMA Feature Extraction: Cognitive Bias Detection

Once semantic features like arguments and motifs have been extracted, **DIMA-OntoToolkit** performs an additional **intermediary step**: identifying and annotating rhetorical strategies based on the **DIMA cognitive bias model**.

This step analyzes each `Argument` to detect the presence of rhetorical **techniques** (e.g., `NegativityBias`), associates them with **cognitive phases** (`Detect`, `Act`, `Inform`, `Memorise`), and generates explanatory notes and excerpts that justify the classification.

These outputs are saved in intermediate JSON files and later transformed into OWL individuals during the ontology generation phase.

#### 📄 Example: Intermediate Output

After analyzing `ex1.txt`, the following structure is added to the JSON:

```json
"Detect": {
  "NegativityBias": [
    {
      "argument_id": "argument_1",
      "excerpts": ["cyber intrusions", "antagonistic behavior"],
      "explanation": "Frames actions as hostile, emphasizing threat and escalation."
    }
  ]
}
```

This file lives under: `output/bias_analysis/article_biases_<article_id>.json` and is later used to instantiate DIMA ontology individuals.

## 🧩 Ontology-Based Semantic Representation

To support formal reasoning and advanced queries, DIMA-OTK maps `article_processed_<article_id>.json` and `article_biases_<article_id>.json` to a structured **OWL ontology**. This approach allows us to connect and infer semantic relationships beyond what is explicitly stated in the text - **without relying on opaque machine learning models**.

### 🏛️ The Influence-Mini Ontology: Core Concepts

The ontology used to structure the semantic content of articles is called **Influence-Mini**. It defines all key concepts - such as:

* `Motif`, `Argument`, `Quote`, `ParaphrasedQuote`, `NarratedAgent`, etc.
* Semantic properties like `hasText`, `hasPremise`, `hasQuote`, `mentionsInQuote`, etc.
* Class hierarchies (e.g., `ParaphrasedQuote` is a subclass of `Quote`)
* Logical relations and restrictions

This ontology is used to **semantically annotate and represent** each article’s content in a machine-readable form.

### 🧭 The DIMA Ontology: Annotating Bias

On top of the Influence-Mini ontology, the **DIMA ontology** is applied to identify and annotate **bias, rhetorical patterns, and manipulation techniques**.

It builds upon the semantic structure from Influence-Mini to label concepts with rhetorical indicators, bias types, or stance - enabling deeper analysis of persuasion strategies.

Once integrated, this enables rich inferences - for example:

> **If an argument uses the technique *Negativity Bias*, and that technique is known to be part of the *Divisive Information* tactic, the tool automatically infers that the argument promotes divisive narratives.**

---

### 🗃️ Ontology Storage and Reasoning Workflow

📄 The Influence-Mini and DIMA ontologies are each saved separately (with their respective individuals) to:
`output/owl_influence-mini/influence-mini_full.owl` and `output/owl_dima/dima_full.owl`.

These are then merged in memory during the query and reasoning phase for SPARQL evaluation.
Please note that reasoning is applied in-memory using the HermiT reasoner - inferred facts are not written to disk.

### 📊 Query: Number of Techniques Used per Article by Cognitive Phase

You can issue a SPARQL query like the following to get the number of times each cognitive **technique** was used in an article, grouped by the **DIMA cognitive phase** (Act, Detect, Inform, Memorise):

```sparql
PREFIX scim: <https://stratcomcoe.org/influence-mini/ontology#>
PREFIX dima: <https://m82-project.org/dima-bias/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?article ?techniqueType ?technique (COUNT(DISTINCT ?techniqueUsage) AS ?numTechniqueUsage)
WHERE {
  ?article scim:hasMotif ?motif .
  ?motif scim:hasArgument ?argument .
  ?argument dima:usesTechnique ?techniqueUsage .
  ?techniqueUsage dima:instantiatesTechnique ?technique .
  ?technique rdfs:subClassOf ?techniqueType .
}
GROUP BY ?article ?techniqueType ?technique
ORDER BY ?article ?techniqueType ?technique
```

---

#### 🧠 Explanation of Results

| **Article**               | **Cognitive Phase**      | **Technique**               | **# of Usages** |
| ------------------------- | ------------------------ | --------------------------- | --------------- |
| `scim:378d39b197_article` | `dima:ActTechnique`      | `dima:OmissionBias`         | 1               |
| `scim:378d39b197_article` | `dima:DetectTechnique`   | `dima:NegativityBias`       | 4               |
| `scim:378d39b197_article` | `dima:DetectTechnique`   | `dima:VonRestorffEffect`    | 6               |
| `scim:378d39b197_article` | `dima:InformTechnique`   | `dima:FalseConsensusEffect` | 1               |
| `scim:378d39b197_article` | `dima:MemoriseTechnique` | `dima:MereExposureEffect`   | 2               |

---

This query shows how often each technique appears in an article and categorizes it under its DIMA **phase**. These phases reflect cognitive objectives such as action initiation, detection, information framing, or memorability enhancement. This is useful for analyzing patterns of influence or manipulation across content.

---

## 🚀 How to Use DIMA-OntoToolkit

### API Key Configuration

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

### Quick Start (Using Docker)

#### Prerequisites
- [Docker](https://www.docker.com/) must be installed.
- An `.env` file with your OpenAI API key (see **API Key Configuration** section above).

#### 1. Build the Docker image

To build the Docker image for DIMA-OntoToolkit, run the following command:

```bash
./build-docker.sh
````

> **Note**: If you encounter a "Permission Denied" error when trying to run the scripts, you may need to make the script executable first by running:

```bash
chmod +x build-docker.sh
```

> **Note**: If you get a permission error while running the Docker command, you might need to use `sudo` to execute Docker commands:

```bash
sudo ./build-docker.sh
```

#### 2. Run the tool with your input text

Once the image is built, you can run the tool with your own input text by using the `-t` option:

```bash
./run-docker.sh -t "Your article text goes here."
```

> **Note**: Similarly, if you get a "Permission Denied" error while running the script, make it executable by running:

```bash
chmod +x run-docker.sh
```

> **Note**: If you encounter permission issues when running the Docker command, you may need to prepend `sudo`:

```bash
sudo ./run-docker.sh -t "Your article text goes here."
```

The **OWL output** file will be saved in the `output/` directory. You can review the processed data there.

#### 3. Run a SPARQL query on the extracted data

After processing the text or articles, you can run a **SPARQL query** to query the merged ontology with the `-q` option:

```bash
./run-docker.sh -q "PREFIX scim: <https://stratcomcoe.org/influence-mini/ontology#>
PREFIX dima: <https://m82-project.org/dima-bias/ontology#>

SELECT DISTINCT ?argument ?technique
WHERE {
  ?argument a scim:Argument ;
            dima:usesTechnique ?technique .
}"
```

This query will **retrieve all arguments** along with the **techniques** they use.

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
