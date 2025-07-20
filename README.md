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

### 🔍 Create an Ontology ...

to fill

### 📦 Final Output

After all features are extracted, the structured data is mapped to OWL individuals and serialized as an RDF/OWL file in:

```
output/result.owl
```

This file conforms to the **DIMA ontology** and can be opened in Protégé or used in downstream reasoning tasks.

---

## The DIMA Ontology

The **DIMA ontology** formalizes a taxonomy of narrative manipulation strategies and cognitive bias techniques, originally defined in the [M82-project/DIMA](https://github.com/M82-project/DIMA) framework.

It models:

- **Bias categories** (e.g., `Information préexistante`, `Information clivante`)
- **Cognitive techniques** associated with each category (e.g., `Effet de contraste`, `Biais de négativité`)
- **Semantic relationships** between them, using OWL classes and object properties
- Metadata such as UUIDs and standardized IDs (e.g., `TA0013`, `TE0142`)

This ontology serves as the **TBox** (terminological box) used to generate structured **ABox assertions** (individuals) based on detected patterns in unstructured text.

You can find the ontology file here:

```text
ontology/dima-bias.ttl
```

It is OWL 2-compliant and can be opened in tools such as [Protégé](https://protege.stanford.edu/).

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

You can find copies of the relevant licenses in the respective repositories or license documentation.
