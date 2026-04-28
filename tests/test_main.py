import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from source.main import extract, batch


# ---- pdf-extract 命令测试 ----

def test_cli_extract_no_args():
    runner = CliRunner()
    result = runner.invoke(extract, [])
    assert result.exit_code != 0


@patch("source.main.asyncio.run")
def test_cli_extract_success(mock_asyncio_run, tmp_path):
    runner = CliRunner()

    dummy_file = tmp_path / "test.pdf"
    dummy_file.touch()

    output_file = tmp_path / "custom_output.md"

    result = runner.invoke(extract, [str(dummy_file), "-o", str(output_file)])

    assert result.exit_code == 0
    assert "Initializing extraction for 1 file(s)..." in result.output

    mock_asyncio_run.assert_called_once()


# ---- pdf-batch 命令测试 ----

def test_cli_batch_no_args():
    runner = CliRunner()
    result = runner.invoke(batch, [])
    assert result.exit_code != 0


def test_cli_batch_empty_directory(tmp_path):
    runner = CliRunner()

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"

    result = runner.invoke(batch, [str(input_dir), "-o", str(output_dir)])

    assert result.exit_code == 0
    assert "No supported files found" in result.output


@patch("source.main.build_graph")
@patch("source.main.asyncio.run")
def test_cli_batch_success(mock_asyncio_run, mock_build_graph, tmp_path):
    runner = CliRunner()

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "doc1.pdf").touch()
    (input_dir / "doc2.pdf").touch()
    (input_dir / "readme.txt").touch()

    output_dir = tmp_path / "output"

    mock_app = MagicMock()
    mock_build_graph.return_value = mock_app

    result = runner.invoke(batch, [str(input_dir), "-o", str(output_dir)])

    assert result.exit_code == 0
    assert "Found 2 file(s)" in result.output
    assert "0 skipped, 2 succeeded" in result.output
    assert mock_asyncio_run.call_count == 2


@patch("source.main.build_graph")
@patch("source.main.asyncio.run")
def test_cli_batch_partial_failure(mock_asyncio_run, mock_build_graph, tmp_path):
    runner = CliRunner()

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "good.pdf").touch()
    (input_dir / "bad.pdf").touch()

    output_dir = tmp_path / "output"

    mock_app = MagicMock()
    mock_build_graph.return_value = mock_app

    mock_asyncio_run.side_effect = [None, RuntimeError("API Error")]

    result = runner.invoke(batch, [str(input_dir), "-o", str(output_dir)])

    assert result.exit_code == 0
    assert "0 skipped, 1 succeeded, 1 failed" in result.output
    assert "bad.pdf" in result.output
    assert "API Error" in result.output


def test_cli_batch_skip_existing(tmp_path):
    runner = CliRunner()

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "already_done.pdf").touch()
    (input_dir / "new_one.pdf").touch()

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "already_done.md").write_text("existing content")

    with patch("source.main.asyncio.run") as mock_run, \
         patch("source.main.build_graph") as mock_graph:
        mock_graph.return_value = MagicMock()

        result = runner.invoke(batch, [str(input_dir), "-o", str(output_dir)])

    assert result.exit_code == 0
    assert "Skipping (already exists): already_done.pdf" in result.output
    assert "Processing: new_one.pdf" in result.output
    assert "1 skipped, 1 succeeded" in result.output
    assert mock_run.call_count == 1  # 只处理了 new_one
