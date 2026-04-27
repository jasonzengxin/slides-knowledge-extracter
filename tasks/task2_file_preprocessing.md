# Task 2: File Preprocessing (Image Splitting & Compression)

## 1. Description
This is a **Thin Node** (Deterministic Execution). Its responsibility is to take raw file paths and transform them into a standardized format for the Vision model. 
Specifically, it must:
1. Convert `.ppt`/`.pptx` to `.pdf`.
2. Split all PDFs into individual page images.
3. Compress all resulting images (including raw image inputs) to optimize token usage and transfer speed without losing legibility.

## 2. DSPy / Schema-Driven Contract
This task takes a JSON defining the raw inputs and outputs a JSON defining an array of compressed image files.

### Signature (Input)
```json
{
  "type": "object",
  "properties": {
    "raw_files": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": { "type": "string" },
          "extension": { "type": "string" }
        },
        "required": ["path", "extension"]
      }
    }
  },
  "required": ["raw_files"]
}
```

### Signature (Output)
```json
{
  "type": "object",
  "properties": {
    "processed_documents": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "original_path": { "type": "string" },
          "pages": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "page_number": { "type": "integer" },
                "image_path": { "type": "string", "description": "Path to the compressed image in .tmp/" }
              },
              "required": ["page_number", "image_path"]
            }
          }
        },
        "required": ["original_path", "pages"]
      }
    }
  },
  "required": ["processed_documents"]
}
```

## 3. Execution Details
*   **PPTs**: Use `libreoffice --headless` to convert to PDF.
*   **PDFs**: Use `pdf2image` to extract each page as a PIL Image.
*   **Compression**: Use `Pillow` (PIL) to resize the image (e.g., max dimension 1024px or 1536px, depending on quality needed) and save as an optimized JPEG.
*   Save all resulting compressed JPEGs to a hidden `.tmp/` directory.
