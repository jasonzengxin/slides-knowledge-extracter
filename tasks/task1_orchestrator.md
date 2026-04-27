# Task 1: CLI Entrypoint & State Machine Orchestrator

## 1. Description
This is a **Thin Node** responsible for the macro architecture of the knowledge extractor. It serves as the CLI entrypoint and the workflow engine (DAG manager) that drives the application state through a State Machine. It does not perform any data extraction or reasoning itself; it strictly orchestrates the flow of data between the other nodes.

## 2. DSPy / Schema-Driven Contract
The orchestrator relies on the strict JSON contracts of its downstream tasks.

### Input Schema (CLI Arguments)
```json
{
  "type": "object",
  "properties": {
    "input_files": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of input file paths (PDF, PPT, Images)"
    },
    "output_file": {
      "type": "string",
      "description": "Path to the output Markdown file"
    }
  },
  "required": ["input_files", "output_file"]
}
```

### Output Schema (Execution Result)
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["SUCCESS", "FAILURE"]
    },
    "output_path": { "type": "string" },
    "error_message": { "type": "string" }
  },
  "required": ["status"]
}
```

## 3. State Machine Flow
The DAG is structured as follows:
1. `INIT` -> Parse CLI arguments.
2. `PREPROCESSING` -> Pass `input_files` to **Task 2 (Preprocessor)**.
3. `EXTRACTION` -> Pass processed files to **Task 3 (Extractor)** one by one.
4. `SYNTHESIS` -> Pass all extracted JSON payloads to **Task 4 (Synthesizer)**.
5. `OUTPUT_GENERATION` -> Write the synthesized Markdown string to `output_file`.
6. `DONE` -> Exit with `SUCCESS`.
