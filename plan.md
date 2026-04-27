# Knowledge Extractor Plan

## 1. Objective
Develop a Command-Line Interface (CLI) tool that extracts, analyzes, and synthesizes knowledge from diverse document formats (PDFs, presentations, and images). The final output must be a consolidated, well-formatted Markdown (`.md`) document containing the summarized and synthesized information.

## 2. Interface Requirements
*   **User Interface:** A Python-based Command-Line Interface (CLI).
*   **Inputs:** The CLI must accept one or more file paths as arguments.
    *   Supported file types:
        *   PDF (`.pdf`)
        *   Presentations (`.ppt`, `.pptx`)
        *   Images (`.png`, `.jpg`, `.jpeg`, etc.)
*   **Outputs:** The CLI must output a single Markdown file containing the synthesized knowledge. The user should optionally be able to specify the output file path (e.g., `-o output.md`).

## 3. Functional Requirements

### 3.1. File Preprocessing (Splitting & Compression)
*   Multi-page documents (PDFs, PPTs) must be split so that **every single page becomes an individual image**.
*   These images must be **appropriately compressed** to reduce token consumption and API bandwidth while preserving readability for the vision model.
*   PPT/PPTX files will first be converted to PDF internally before being split into images.

### 3.2. Multi-modal Extraction (Page-by-Page Vision)
*   The system uses a Vision LLM (`Qwen/Qwen3.6-27B` via SiliconFlow) to read each compressed image individually.
*   The extraction prompt must explicitly ask the model to describe the page, clarify text, and convert any flowcharts/diagrams into **Mermaid code (Graph TD or SequenceDiagram)**.
*   The extracted content for each page must be saved as an intermediate Markdown (`.md`) document.

### 3.3. LLM-Powered Synthesis (Kimi API)
*   The system must utilize the **Kimi API** (via the Anthropic compatible endpoint `https://api.kimi.com/coding/`) to read all the intermediate page-level Markdown documents.
*   Kimi will synthesize and reorganize the information across all pages into a final, coherent output Markdown document.

## 4. Technical Constraints & Dependencies
*   **Programming Language:** Python (using `uv` for dependency management).
*   **Vision Integration:** SiliconFlow API (`Qwen/Qwen3.6-27B`) for page-by-page image understanding.
*   **Synthesis Integration:** Kimi API (Moonshot) using the Anthropic protocol (`anthropic` SDK).
*   **System Dependencies:** 
    *   `libreoffice` (for PPT to PDF conversion).
    *   `poppler` (required by `pdf2image` for PDF to Image extraction).
*   **Python Libraries:** `pdf2image`, `Pillow` (for image compression).
