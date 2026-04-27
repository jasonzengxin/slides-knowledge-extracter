# Design Document: Task 2 - File Preprocessing (Image Splitting & Compression)

## 1. Overview
This document details the design of the File Preprocessing node (Task 2). Its primary responsibility is to ensure all input files are converted into individual, compressed image pages (JPEGs) that the downstream Vision LLM can easily and efficiently process.

**Key Design Decisions:**
*   **PDF to Image:** `pdf2image` library (requires `poppler` installed on the system).
*   **Presentation Conversion:** `LibreOffice` via headless command-line to convert `.ppt`/`.pptx` to `.pdf` first.
*   **Image Compression:** `Pillow` (PIL) to resize and optimize image dimensions to save tokens/bandwidth.
*   **Intermediate Storage:** A dedicated, hidden `.tmp/` directory within the project root.

## 2. Input and Output Contract
Strictly adheres to `tasks/task2_file_preprocessing.md`.
*   **Input:** List of raw file paths.
*   **Output:** List of dictionaries containing `original_path` and an array of `pages` (each containing `page_number` and `image_path`).

## 3. Component Design

### 3.1. Temporary Directory Management
```python
import os
import shutil
import uuid
from pathlib import Path

TMP_DIR = Path(".tmp")

def setup_tmp_dir():
    TMP_DIR.mkdir(parents=True, exist_ok=True)

def generate_tmp_filename(prefix: str, extension: str) -> str:
    unique_id = uuid.uuid4().hex[:8]
    return str(TMP_DIR / f"{prefix}_{unique_id}{extension}")
```

### 3.2. Image Compression (Pillow)
```python
from PIL import Image

def compress_and_save_image(img: Image.Image, output_path: str, max_size: int = 1536):
    """Resizes the image to fit within max_size x max_size while maintaining aspect ratio, and saves as optimized JPEG."""
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(output_path, "JPEG", optimize=True, quality=85)
    return output_path
```

### 3.3. Document Conversion & Splitting
```python
import subprocess
from pdf2image import convert_from_path

def convert_ppt_to_pdf(ppt_path: str) -> str:
    """Uses LibreOffice to convert PPT to PDF and returns the path to the PDF."""
    pdf_path = generate_tmp_filename(Path(ppt_path).stem, ".pdf")
    outdir = Path(pdf_path).parent
    command = ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(outdir), ppt_path]
    subprocess.run(command, capture_output=True, check=True)
    
    generated_pdf = outdir / f"{Path(ppt_path).stem}.pdf"
    if generated_pdf.exists():
        generated_pdf.rename(pdf_path)
        return pdf_path
    raise RuntimeError("LibreOffice conversion failed.")

def split_pdf_to_images(pdf_path: str, original_name: str) -> list[dict]:
    """Splits PDF into images, compresses them, and returns page metadata."""
    images = convert_from_path(pdf_path)
    pages = []
    base_name = Path(original_name).stem
    for i, img in enumerate(images, start=1):
        img_path = generate_tmp_filename(f"{base_name}_page{i}", ".jpg")
        compress_and_save_image(img, img_path)
        pages.append({"page_number": i, "image_path": img_path})
    return pages
```

### 3.4. Main Node Function
```python
def execute_preprocessing(state: dict) -> dict:
    setup_tmp_dir()
    processed_documents = []
    
    for raw_path in state["raw_input_files"]:
        path_obj = Path(raw_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Input file not found: {raw_path}")
            
        ext = path_obj.suffix.lower()
        pages = []
        
        if ext in ['.ppt', '.pptx']:
            pdf_path = convert_ppt_to_pdf(raw_path)
            pages = split_pdf_to_images(pdf_path, raw_path)
            # Optional: delete the intermediate PDF to save space
            Path(pdf_path).unlink(missing_ok=True) 
        elif ext == '.pdf':
            pages = split_pdf_to_images(raw_path, raw_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            img = Image.open(raw_path)
            img_path = generate_tmp_filename(path_obj.stem, ".jpg")
            compress_and_save_image(img, img_path)
            pages = [{"page_number": 1, "image_path": img_path}]
            
        processed_documents.append({
            "original_path": raw_path,
            "pages": pages
        })
            
    return {"processed_documents": processed_documents}
```