import pytest
import os
import json
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from PIL import Image

from source.extractor import encode_file_to_base64, extract_page_knowledge, execute_extraction_parallel

@pytest.fixture(autouse=True)
def clean_tmp_dir():
    """在每个测试用例结束后清理 .tmp 文件夹。"""
    yield
    tmp_path = Path(".tmp")
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)

@pytest.fixture
def dummy_image(tmp_path: Path) -> str:
    """生成一张用于测试的图片。"""
    img_path = tmp_path / "test_image.jpg"
    Image.new('RGB', (10, 10), color='blue').save(img_path, format="JPEG")
    return str(img_path)

def test_encode_file_to_base64(dummy_image):
    b64_str = encode_file_to_base64(dummy_image)
    assert isinstance(b64_str, str)
    assert len(b64_str) > 0

@pytest.mark.asyncio
@patch("source.extractor.client.chat.completions.create", new_callable=AsyncMock)
async def test_extract_page_knowledge_success(mock_create, dummy_image):
    # 模拟 API 返回合法的 JSON
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({"page_markdown": "# Hello World\n- item 1"})
    mock_create.return_value = MagicMock(choices=[mock_choice])
    
    page_meta = {"image_path": dummy_image, "page_number": 2}
    original_path = "/fake/dir/doc.pdf"
    
    # 确保 .tmp 目录存在
    Path(".tmp").mkdir(exist_ok=True)
    
    output_file = await extract_page_knowledge(page_meta, original_path)
    
    assert output_file == ".tmp/doc_page_2.md"
    assert Path(output_file).exists()
    
    content = Path(output_file).read_text(encoding="utf-8")
    assert "<!-- Source: doc.pdf | Page: 2 -->" in content
    assert "# Hello World" in content
    
    # 验证 API 调用参数
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "Qwen/Qwen3.6-27B"
    assert call_kwargs["response_format"] == {"type": "json_object"}

@pytest.mark.asyncio
@patch("source.extractor.client.chat.completions.create", new_callable=AsyncMock)
async def test_extract_page_knowledge_fallback(mock_create, dummy_image):
    # 模拟 API 没有返回合法的 JSON，而是返回了纯文本（Fallback 测试）
    mock_choice = MagicMock()
    mock_choice.message.content = "纯文本 Markdown 没有包在 JSON 里"
    mock_create.return_value = MagicMock(choices=[mock_choice])
    
    page_meta = {"image_path": dummy_image, "page_number": 1}
    original_path = "doc.pdf"
    
    Path(".tmp").mkdir(exist_ok=True)
    output_file = await extract_page_knowledge(page_meta, original_path)
    
    content = Path(output_file).read_text(encoding="utf-8")
    assert "纯文本 Markdown 没有包在 JSON 里" in content

@pytest.mark.asyncio
async def test_extract_page_knowledge_file_not_found():
    page_meta = {"image_path": "non_existent.jpg", "page_number": 1}
    with pytest.raises(FileNotFoundError, match="Image not found"):
        await extract_page_knowledge(page_meta, "doc.pdf")

@pytest.mark.asyncio
@patch("source.extractor.extract_page_knowledge", new_callable=AsyncMock)
async def test_execute_extraction_parallel_mixed_results(mock_extract):
    # 模拟 extract_page_knowledge 的并发返回值
    # 前两张成功，第三张失败抛出异常
    mock_extract.side_effect = [
        ".tmp/doc_page_1.md",
        ".tmp/doc_page_2.md",
        Exception("API Timeout")
    ]
    
    state = {
        "processed_documents": [
            {
                "original_path": "doc.pdf",
                "pages": [
                    {"page_number": 1, "image_path": "img1.jpg"},
                    {"page_number": 2, "image_path": "img2.jpg"},
                    {"page_number": 3, "image_path": "img3.jpg"}
                ]
            }
        ]
    }
    
    result = await execute_extraction_parallel(state)
    
    # 验证成功的提取
    assert len(result["extracted_md_files"]) == 2
    assert ".tmp/doc_page_1.md" in result["extracted_md_files"]
    assert ".tmp/doc_page_2.md" in result["extracted_md_files"]
    
    # 验证失败的容错 (Best Effort)
    assert len(result["failed_extractions"]) == 1
    failure = result["failed_extractions"][0]
    assert failure["file"] == "doc.pdf"
    assert failure["page"] == 3
    assert "API Timeout" in failure["error"]

@pytest.mark.asyncio
async def test_execute_extraction_parallel_empty():
    state = {"processed_documents": []}
    result = await execute_extraction_parallel(state)
    
    assert result["extracted_md_files"] == []
    assert result["failed_extractions"] == []
