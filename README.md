# PDF/PPT/Photo Knowledge Extractor

A powerful Command-Line Interface (CLI) tool that extracts, analyzes, and synthesizes knowledge from diverse document formats (PDFs, PowerPoint presentations, and images).

It uses a state-of-the-art multimodal pipeline to not only extract text but also visually comprehend documents, including transcribing flowcharts and diagrams into Mermaid syntax. Finally, it uses an advanced LLM to synthesize all extracted information into a single, cohesive Markdown document.

## Features

*   **Multi-format Support:** Handles `.pdf`, `.ppt`, `.pptx`, `.png`, `.jpg`, `.jpeg`.
*   **Visual Comprehension:** Converts all pages/slides into images for deep visual analysis.
*   **Diagram to Code:** Automatically translates visual flowcharts and diagrams into **Mermaid** code (Graph TD or SequenceDiagram).
*   **Intelligent Synthesis:** Merges information across multiple pages and documents into a clean, well-formatted Markdown summary.
*   **Model Fallback:** Kimi (primary) → GLM-5.1 (fallback) for synthesis, ensuring reliability even when the primary model is unavailable.
*   **Concurrent Processing:** Processes multiple pages in parallel with configurable concurrency control.
*   **Batch Mode:** Convert all supported files in a directory at once, each producing its own Markdown output.

## Architecture

The tool is built on a Directed Acyclic Graph (DAG) architecture using `LangGraph`:

1.  **Preprocessor:** Converts PPTs to PDFs, splits PDFs into individual pages, and compresses them as JPEGs.
2.  **Extractor (Vision LLM):** Uses SiliconFlow (`Qwen/Qwen3.6-27B`) to extract text and Mermaid diagrams page-by-page with configurable concurrency.
3.  **Synthesizer (Text LLM):** Uses Kimi API (Moonshot) to aggregate and format all intermediate data into the final Markdown output. Falls back to GLM-5.1 if Kimi is unavailable.

## Prerequisites

### 1. System Dependencies

This tool relies on underlying system libraries for document conversion and image extraction. You must install them before running the application:

*   **macOS (Homebrew):**
    ```bash
    brew install libreoffice poppler
    ```
*   **Ubuntu/Debian:**
    ```bash
    sudo apt-get install libreoffice poppler-utils
    ```

### 2. API Keys

You will need API keys for the AI services used in this project:

1.  **SiliconFlow API Key:** For the Vision model (`Qwen/Qwen3.6-27B`). Get it from [SiliconFlow](https://siliconflow.cn/).
2.  **Kimi API Key:** For the Synthesis model (primary). Get it from [Moonshot AI](https://platform.moonshot.cn/).
3.  **GLM API Key** (optional): Fallback synthesis model. Get it from [z.ai](https://z.ai/).

## Installation

This project uses `uv` for lightning-fast dependency management.

1.  Ensure you have `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`).
2.  Initialize the environment and install dependencies:
    ```bash
    uv sync
    ```
3.  Set up your environment variables:
    ```bash
    cp .env.example .env
    # Edit .env and add your API keys
    ```

## Usage

The tool provides two commands: `extract` (single/multi-file) and `batch` (directory).

### Extract — Single or Multi-file

Process one or more files, synthesizing them into a single Markdown document:

```bash
# Process a single PDF
uv run extract document.pdf

# Process a PPTX and an image, outputting to a specific file
uv run extract presentation.pptx diagram.png -o my_summary.md
```

### Batch — Directory Processing

Convert all supported files in a directory, each producing its own Markdown file:

```bash
# Convert all PDFs/PPTs/images in a directory
uv run batch ./papers -o ./output
```

This will process each supported file independently and output `./output/{filename}.md` for each one.

### Concurrency Control

The number of concurrent API requests for vision extraction is configurable via the `EXTRACTION_CONCURRENCY` environment variable (default: 8):

```bash
EXTRACTION_CONCURRENCY=5 uv run extract large_document.pdf
```

### Temporary Files

During execution, the tool creates a hidden `.tmp/` directory to store compressed images and intermediate page-level Markdown files. This directory is automatically cleaned up after a successful run.

## Development

The application is structured into clearly defined tasks and nodes within `source/` using a strict **Schema-Driven** and **State Machine** architecture.

*   `source/main.py`: CLI entrypoint (`Click`) — `extract` and `batch` commands.
*   `source/config.py`: Environment variable configuration (API keys, concurrency).
*   `source/state.py`: Defines the `LangGraph` State Dictionary (`TypedDict`).
*   `source/orchestrator.py`: Configures the DAG execution flow.
*   `source/preprocessor.py` (Task 2): Document conversion and image extraction.
*   `source/extractor.py` (Task 3): Vision LLM interaction with concurrency control.
*   `source/synthesizer.py` (Task 4): Text LLM summarization with Kimi → GLM fallback.

To modify the DAG flow, update `source/orchestrator.py`. For node implementation details, consult the `designs/` and `tasks/` markdown files.

## Testing

This project uses `pytest` for end-to-end (E2E) testing. The test suite automatically creates dummy assets and invokes the CLI to ensure the pipeline executes properly from start to finish.

1.  Ensure development dependencies are installed:
    ```bash
    uv sync
    ```
2.  Run the test suite:
    ```bash
    uv run pytest tests/
    ```

*(Note: The E2E test suite requires API Keys set in `.env` if testing real LLM nodes, but tests use mock objects where necessary or fallback mechanisms to ensure CI/CD robustness without internet dependencies.)*
