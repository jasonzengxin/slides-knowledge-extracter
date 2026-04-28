# Design Document: Task 1 - CLI Entrypoint & State Machine Orchestrator

## 1. Overview
This document outlines the design for the macro-architecture and orchestration layer of the Knowledge Extractor. It implements a Thin Node orchestrator responsible for CLI parsing, state management, and driving the Directed Acyclic Graph (DAG) of tasks. 

**Key Architectural Choices:**
*   **Workflow Engine:** `LangGraph` (Provides a robust, stateful DAG implementation).
*   **CLI Framework:** `Click` (Mature, powerful command-line argument parsing).
*   **Concurrency:** Asynchronous parallel processing (`asyncio`) for the Extraction phase.
*   **Error Handling:** "Best Effort" approach. Node failures on individual files do not halt the entire pipeline; errors are recorded and reported in the final synthesis.

## 2. System Components

### 2.1. CLI Layer (`Click`)
The entrypoint uses a Click group with two subcommands:

*   **`extract`** — Process one or more files into a single Markdown document.
    *   **Arguments:** `[INPUT_FILES]...` (Accepts multiple file paths, validates existence).
    *   **Options:** `-o, --output` (Target markdown file path, defaults to `output.md`).
*   **`batch`** — Convert all supported files in a directory, each to its own Markdown file.
    *   **Arguments:** `INPUT_DIR` (Directory path, validates existence).
    *   **Options:** `-o, --output` (Output directory path, required).

### 2.2. Graph State Definition (`LangGraph State`)
The core of LangGraph is the state object passed between nodes. We will define a strict `TypedDict` (or Pydantic model) acting as the single source of truth for the workflow's context.

```python
from typing import TypedDict, List, Dict, Any, Optional

class ExtractorState(TypedDict):
    # INIT State
    raw_input_files: List[str]
    output_path: str
    
    # PREPROCESSING State
    processed_files: List[Dict[str, str]] # Output from Task 2 (path, ready_path, mime_type)
    
    # EXTRACTION State
    extracted_data: List[Dict[str, Any]]  # Successful JSON outputs from Task 3
    failed_extractions: List[Dict[str, str]] # Track files that failed: {"file": "...", "error": "..."}
    
    # SYNTHESIS State
    final_markdown: Optional[str]         # Output from Task 4
```

### 2.3. Graph Nodes (The DAG)
The workflow consists of the following LangGraph nodes:

1.  **`node_init`**: Receives Click arguments, initializes the `ExtractorState`.
2.  **`node_preprocess`**: Invokes Task 2 (File Preprocessing). Maps `raw_input_files` to `processed_files`.
3.  **`node_extract` (Parallel & Best-Effort)**: 
    *   Takes the list of `processed_documents`. Since documents have multiple pages, it flattens the list of pages and uses `asyncio.gather(..., return_exceptions=True)` to execute Task 3 on all image pages **concurrently**.
    *   Iterates through the results: successful markdown paths are appended to `extracted_md_files`, while exceptions are caught and appended to `failed_extractions`.
4.  **`node_synthesize`**: Invokes Task 4. Passes `extracted_md_files` (and optionally `failed_extractions` for logging) to the Kimi LLM to generate `final_markdown`.
5.  **`node_output`**: Writes `final_markdown` to `output_path`. Appends a section detailing any files listed in `failed_extractions`.

### 2.4. Graph Edges (Workflow Flow)
The LangGraph `StateGraph` will be wired linearly, as no complex conditional branching is required for the happy path (failures are handled within the `node_extract` state mutation):

`START` -> `node_init` -> `node_preprocess` -> `node_extract` -> `node_synthesize` -> `node_output` -> `END`

## 3. Concurrency & "Best Effort" Mechanism Details

### Concurrency Implementation
In `node_extract`, we use an `asyncio.Semaphore` to control the maximum number of concurrent API requests (configurable via `EXTRACTION_CONCURRENCY` env var, default 8):

```python
sem = asyncio.Semaphore(EXTRACTION_CONCURRENCY)

async def extract_with_sem(p):
    async with sem:
        return await extract_page_knowledge(p["page_meta"], p["original_path"])

tasks = [extract_with_sem(p) for p in all_pages]
# return_exceptions=True ensures one failure doesn't cancel the other tasks
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Best Effort Reporting
The `node_output` will be responsible for final user feedback. If the `failed_extractions` list in the State is not empty, it will append a specific section to the generated `output.md` (e.g., `## Processing Errors`) clearly notifying the user which files were skipped and why, ensuring transparency without halting the generation of successful data.
ll append a specific section to the generated `output.md` (e.g., `## Processing Errors`) clearly notifying the user which files were skipped and why, ensuring transparency without halting the generation of successful data.
