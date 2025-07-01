# DIMA-OntoToolkit

**DIMA-OntoToolkit** is a semantic toolset for detecting and formalizing biases in natural language content using an OWL ontology. It uses a language model (e.g., GPT) to interpret the input and generates OWL individuals that conform to the bias model defined in the DIMA ontology.

---

## What It Does

Given a text input (e.g., an article, comment, or narrative), the tool:
1. Analyzes the text to identify bias elements using GPT.
2. Maps the results to structured instances (individuals) in the ontology.
3. Outputs an OWL file representing those individuals in RDF/OWL (ABox).

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
./run-docker.sh -t "This article unfairly blames a specific group for the economic crisis."
```

OWL output will be saved to: bias_extractor/output/

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

