import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from source.synthesizer import synthesize_knowledge, execute_synthesis

@pytest.fixture
def dummy_md_files(tmp_path: Path):
    """创建一些虚拟的提取文件供合成使用。"""
    file1 = tmp_path / "page_1.md"
    file1.write_text("<!-- Source: doc.pdf | Page: 1 -->\n# Page 1\nContent 1", encoding="utf-8")

    file2 = tmp_path / "page_2.md"
    file2.write_text("<!-- Source: doc.pdf | Page: 2 -->\n# Page 2\nContent 2", encoding="utf-8")

    return [str(file1), str(file2)]


@pytest.mark.asyncio
@patch("source.synthesizer.kimi_client.messages.create", new_callable=AsyncMock)
async def test_synthesize_knowledge_success(mock_kimi_create, dummy_md_files):
    mock_content_block = MagicMock()
    mock_content_block.text = "# Synthesized Document\nThis is the combined content."

    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_kimi_create.return_value = mock_response

    result = await synthesize_knowledge(dummy_md_files)

    mock_kimi_create.assert_called_once()
    call_kwargs = mock_kimi_create.call_args.kwargs
    assert call_kwargs["model"] == "kimi-latest"
    assert "Content 1" in call_kwargs["messages"][0]["content"]
    assert "Content 2" in call_kwargs["messages"][0]["content"]

    assert result == "# Synthesized Document\nThis is the combined content."


@pytest.mark.asyncio
async def test_synthesize_knowledge_empty_input():
    result = await synthesize_knowledge([])
    assert result == "No content was extracted to synthesize."


@pytest.mark.asyncio
async def test_synthesize_knowledge_missing_files(tmp_path):
    result = await synthesize_knowledge([str(tmp_path / "non_existent.md")])
    assert result == "No valid content found in the extracted files."


@pytest.mark.asyncio
@patch("source.synthesizer.glm_client.messages.create", new_callable=AsyncMock)
@patch("source.synthesizer.kimi_client.messages.create", new_callable=AsyncMock)
async def test_synthesize_knowledge_kimi_fails_glm_fallback(mock_kimi_create, mock_glm_create, dummy_md_files):
    """Kimi 失败后自动 fallback 到 GLM 并成功。"""
    mock_kimi_create.side_effect = Exception("API Timeout")

    mock_content_block = MagicMock()
    mock_content_block.text = "# GLM Fallback Result\nCombined content."
    mock_response = MagicMock()
    mock_response.content = [mock_content_block]
    mock_glm_create.return_value = mock_response

    result = await synthesize_knowledge(dummy_md_files)

    mock_kimi_create.assert_called_once()
    mock_glm_create.assert_called_once()
    assert result == "# GLM Fallback Result\nCombined content."


@pytest.mark.asyncio
@patch("source.synthesizer.glm_client.messages.create", new_callable=AsyncMock)
@patch("source.synthesizer.kimi_client.messages.create", new_callable=AsyncMock)
async def test_synthesize_knowledge_all_models_fail(mock_kimi_create, mock_glm_create, dummy_md_files):
    """Kimi 和 GLM 都失败时，降级返回原始拼接内容。"""
    mock_kimi_create.side_effect = Exception("Kimi Timeout")
    mock_glm_create.side_effect = Exception("GLM Rate Limit")

    result = await synthesize_knowledge(dummy_md_files)

    assert "> **Warning**: All synthesis models failed" in result
    assert "GLM Rate Limit" in result
    assert "Content 1" in result
    assert "Content 2" in result


@pytest.mark.asyncio
@patch("source.synthesizer.synthesize_knowledge", new_callable=AsyncMock)
async def test_execute_synthesis(mock_synthesize):
    mock_synthesize.return_value = "# Final Result"

    state = {
        "extracted_md_files": ["file1.md", "file2.md"]
    }

    result = await execute_synthesis(state)

    assert result["final_markdown"] == "# Final Result"
    mock_synthesize.assert_called_once_with(["file1.md", "file2.md"])


@pytest.mark.asyncio
@patch("source.synthesizer.synthesize_knowledge", new_callable=AsyncMock)
async def test_execute_synthesis_empty_state(mock_synthesize):
    mock_synthesize.return_value = "No content"

    state = {}
    result = await execute_synthesis(state)

    assert result["final_markdown"] == "No content"
    mock_synthesize.assert_called_once_with([])
