import pytest
import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock

from source.preprocessor import (
    setup_tmp_dir, 
    generate_tmp_filename, 
    compress_and_save_image,
    convert_ppt_to_pdf,
    split_pdf_to_images,
    execute_preprocessing
)

@pytest.fixture(autouse=True)
def clean_tmp_dir():
    """在每个测试用例结束后清理 .tmp 文件夹。"""
    yield
    tmp_path = Path(".tmp")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)

def test_setup_tmp_dir():
    tmp_path = Path(".tmp")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
        
    setup_tmp_dir()
    assert tmp_path.exists()
    assert tmp_path.is_dir()

def test_generate_tmp_filename():
    setup_tmp_dir()
    filename1 = generate_tmp_filename("test", ".jpg")
    filename2 = generate_tmp_filename("test", ".jpg")
    
    assert filename1.endswith(".jpg")
    assert "test_" in filename1
    assert ".tmp" in filename1
    assert filename1 != filename2

def test_compress_and_save_image(tmp_path):
    setup_tmp_dir()
    
    # 生成一个大的测试图片 (2000x3000)
    img = Image.new('RGB', (2000, 3000), color='blue')
    output_path = str(tmp_path / "compressed.jpg")
    
    result_path = compress_and_save_image(img, output_path, max_size=1000)
    
    assert os.path.exists(result_path)
    
    # 验证缩放逻辑
    saved_img = Image.open(result_path)
    # 按比例缩放，最大边限制在 1000 内
    assert saved_img.width <= 1000
    assert saved_img.height <= 1000
    assert saved_img.height == 1000  # 原图高宽比 3:2，长边 3000 -> 1000

@patch("source.preprocessor.subprocess.run")
def test_convert_ppt_to_pdf_success(mock_run, tmp_path):
    setup_tmp_dir()
    ppt_path = tmp_path / "test.pptx"
    ppt_path.touch()
    
    # 模拟 LibreOffice 执行并在对应的输出目录中生成同名 PDF 文件
    def mock_subprocess_run(*args, **kwargs):
        cmd = kwargs.get("command") or args[0]
        outdir = Path(cmd[5])
        generated_pdf = outdir / "test.pdf"
        generated_pdf.touch()
        return MagicMock(returncode=0)
        
    mock_run.side_effect = mock_subprocess_run
    
    pdf_path = convert_ppt_to_pdf(str(ppt_path))
    assert pdf_path.endswith(".pdf")
    assert ".tmp" in pdf_path
    assert Path(pdf_path).exists()

@patch("source.preprocessor.subprocess.run")
def test_convert_ppt_to_pdf_failure(mock_run, tmp_path):
    setup_tmp_dir()
    ppt_path = tmp_path / "test.pptx"
    ppt_path.touch()
    
    # 模拟由于某些原因没有生成 PDF 的情况
    mock_run.return_value = MagicMock(returncode=0)
    
    with pytest.raises(RuntimeError, match="failed to produce expected file"):
        convert_ppt_to_pdf(str(ppt_path))
        
    # 模拟命令执行失败
    mock_run.side_effect = subprocess.CalledProcessError(1, cmd="soffice", stderr="error")
    with pytest.raises(RuntimeError, match="conversion failed"):
        convert_ppt_to_pdf(str(ppt_path))
        
    # 模拟没有安装 LibreOffice (找不到命令)
    mock_run.side_effect = FileNotFoundError()
    with pytest.raises(RuntimeError, match="Command 'soffice' not found"):
        convert_ppt_to_pdf(str(ppt_path))

@patch("source.preprocessor.convert_from_path")
def test_split_pdf_to_images(mock_convert, tmp_path):
    setup_tmp_dir()
    pdf_path = tmp_path / "test.pdf"
    pdf_path.touch()
    
    # 模拟 pdf2image 拆分出了两页 PDF
    img1 = Image.new('RGB', (100, 100), color='red')
    img2 = Image.new('RGB', (100, 100), color='green')
    mock_convert.return_value = [img1, img2]
    
    pages = split_pdf_to_images(str(pdf_path), "test.pdf")
    
    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert pages[0]["image_path"].endswith(".jpg")
    assert Path(pages[0]["image_path"]).exists()
    
    assert pages[1]["page_number"] == 2
    assert pages[1]["image_path"].endswith(".jpg")
    assert Path(pages[1]["image_path"]).exists()

@patch("source.preprocessor.convert_from_path")
def test_split_pdf_to_images_error(mock_convert, tmp_path):
    setup_tmp_dir()
    pdf_path = tmp_path / "test.pdf"
    
    mock_convert.side_effect = Exception("poppler error")
    with pytest.raises(RuntimeError, match="Failed to convert PDF to images"):
        split_pdf_to_images(str(pdf_path), "test.pdf")

@patch("source.preprocessor.convert_ppt_to_pdf")
@patch("source.preprocessor.split_pdf_to_images")
def test_execute_preprocessing_ppt_and_pdf(mock_split, mock_convert, tmp_path):
    # 造两个虚拟文件
    ppt_file = tmp_path / "slide.ppt"
    pdf_file = tmp_path / "doc.pdf"
    ppt_file.touch()
    pdf_file.touch()
    
    # Mock ppt 转换和拆分
    mock_convert.return_value = str(tmp_path / "mock_converted.pdf")
    mock_split.return_value = [{"page_number": 1, "image_path": "mock_page1.jpg"}]
    
    state = {"raw_input_files": [str(ppt_file), str(pdf_file)]}
    result = execute_preprocessing(state)
    
    docs = result.get("processed_documents")
    assert len(docs) == 2
    assert docs[0]["original_path"] == str(ppt_file)
    assert len(docs[0]["pages"]) == 1
    assert docs[1]["original_path"] == str(pdf_file)
    
    # 验证是否调用了正确的方法
    mock_convert.assert_called_once_with(str(ppt_file))
    assert mock_split.call_count == 2

def test_execute_preprocessing_image(tmp_path):
    # 造一张虚拟图片
    test_img_path = tmp_path / "test_input.png"
    Image.new('RGB', (100, 100), color='green').save(test_img_path)
    
    state = {"raw_input_files": [str(test_img_path)]}
    
    result = execute_preprocessing(state)
    
    docs = result.get("processed_documents")
    assert docs is not None
    assert len(docs) == 1
    
    doc = docs[0]
    assert doc["original_path"] == str(test_img_path)
    assert len(doc["pages"]) == 1
    
    page = doc["pages"][0]
    assert page["page_number"] == 1
    assert ".tmp/" in page["image_path"]
    assert page["image_path"].endswith(".jpg")
    assert Path(page["image_path"]).exists()

def test_execute_preprocessing_unsupported(tmp_path):
    # 造一个不支持的文件
    test_file = tmp_path / "test_input.txt"
    test_file.write_text("hello")
    
    state = {"raw_input_files": [str(test_file)]}
    
    with pytest.raises(ValueError, match="Unsupported file extension"):
        execute_preprocessing(state)

def test_execute_preprocessing_file_not_found():
    state = {"raw_input_files": ["/non/existent/path/file.png"]}
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        execute_preprocessing(state)
