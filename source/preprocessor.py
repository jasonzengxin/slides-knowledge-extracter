"""
预处理模块 (Task 2: File Preprocessing)

嗨！这是我们的瘦节点 (Thin Node) 之一，主要做“苦力活”，没有任何大模型推理。
它的任务是：
1. 拿到用户传进来的各类文件 (PDF, PPT, Images)。
2. 把包含多页的文件 (PPT 转 PDF 后再转图片, PDF 直接转图片) 拆分成一张张单页图片。
3. 把这些图片进行“压缩”，存到 `.tmp/` 隐藏文件夹里。

为什么要转成单张图片？
因为视觉大模型 (Qwen) 处理较小的单张图片效率最高，省 Token 也省宽带。
"""
import os
import shutil
import uuid
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image
from pdf2image import convert_from_path

from source.state import ExtractorState

TMP_DIR = Path(".tmp")

def setup_tmp_dir():
    """初始化用于存放中间文件的临时文件夹。"""
    TMP_DIR.mkdir(parents=True, exist_ok=True)

def generate_tmp_filename(prefix: str, extension: str) -> str:
    """生成带随机 ID 的临时文件名，防止文件重名覆盖。"""
    unique_id = uuid.uuid4().hex[:8]
    return str(TMP_DIR / f"{prefix}_{unique_id}{extension}")

def compress_and_save_image(img: Image.Image, output_path: str, max_size: int = 1536) -> str:
    """
    将图片等比例缩放至最大边为 max_size，并以优化后的 JPEG 格式保存。
    这能在保证模型能看清的前提下，最大程度节省带宽和 Token。
    """
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    # 如果图片是透明背景 (RGBA) 或者是调色板模式 (P)，需要转成 RGB 才能存 JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # 质量设为 85，开启优化
    img.save(output_path, "JPEG", optimize=True, quality=85)
    return output_path

def convert_ppt_to_pdf(ppt_path: str) -> str:
    """使用 LibreOffice 命令行工具将 PPT/PPTX 转换为 PDF。"""
    pdf_path = generate_tmp_filename(Path(ppt_path).stem, ".pdf")
    outdir = Path(pdf_path).parent
    # 构造 LibreOffice 无头模式命令
    command = [
        "soffice", 
        "--headless", 
        "--convert-to", "pdf", 
        "--outdir", str(outdir), 
        ppt_path
    ]
    
    try:
        subprocess.run(command, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"LibreOffice conversion failed. Is LibreOffice installed? Error: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Command 'soffice' not found. Please install LibreOffice and ensure it is in your system PATH.")
    
    # LibreOffice 会生成和原文件同名的 PDF 文件到 outdir，我们需要将其重命名为带随机后缀的防冲突文件名
    generated_pdf = outdir / f"{Path(ppt_path).stem}.pdf"
    if generated_pdf.exists():
        generated_pdf.rename(pdf_path)
        return pdf_path
        
    raise RuntimeError(f"LibreOffice conversion failed to produce expected file: {generated_pdf}")

def split_pdf_to_images(pdf_path: str, original_name: str) -> List[Dict[str, Any]]:
    """将 PDF 的每一页转化为一张图片，进行压缩保存，并返回页面信息列表。"""
    try:
        # 这一步需要系统安装了 poppler
        images = convert_from_path(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF to images. Is 'poppler' installed? Error: {e}")
        
    pages = []
    base_name = Path(original_name).stem
    for i, img in enumerate(images, start=1):
        img_path = generate_tmp_filename(f"{base_name}_page{i}", ".jpg")
        compress_and_save_image(img, img_path)
        pages.append({"page_number": i, "image_path": img_path})
        
    return pages

def execute_preprocessing(state: ExtractorState) -> Dict[str, Any]:
    """
    Task 2 的执行函数。
    它接收包含 'raw_input_files' 的全局状态字典，经过处理后，
    返回需要更新进状态的新字典，键为 'processed_documents'。
    """
    setup_tmp_dir()
    t0 = time.time()
    processed_documents = []
    
    for raw_path in state.get("raw_input_files", []):
        path_obj = Path(raw_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Input file not found: {raw_path}")
            
        ext = path_obj.suffix.lower()
        pages = []
        
        # 1. PPT/PPTX 需要先转 PDF 再切图
        if ext in ['.ppt', '.pptx']:
            pdf_path = convert_ppt_to_pdf(raw_path)
            pages = split_pdf_to_images(pdf_path, raw_path)
            # 转换完图片后，临时生成的 PDF 就可以删掉了以节省空间
            Path(pdf_path).unlink(missing_ok=True) 
            
        # 2. PDF 直接切图
        elif ext == '.pdf':
            pages = split_pdf_to_images(raw_path, raw_path)
            
        # 3. 图片直接进行压缩处理
        elif ext in ['.png', '.jpg', '.jpeg']:
            img = Image.open(raw_path)
            img_path = generate_tmp_filename(path_obj.stem, ".jpg")
            compress_and_save_image(img, img_path)
            # 图片算作只有一页
            pages = [{"page_number": 1, "image_path": img_path}]
            
        else:
            raise ValueError(f"Unsupported file extension: {ext} for file {raw_path}")
            
        processed_documents.append({
            "original_path": raw_path,
            "pages": pages
        })
            
    total_pages = sum(len(doc["pages"]) for doc in processed_documents)
    logging.info(f"Preprocessing done: {len(processed_documents)} file(s), {total_pages} pages in {time.time() - t0:.1f}s")

    return {"processed_documents": processed_documents}
