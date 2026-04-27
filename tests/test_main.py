import pytest
import os
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from source.main import cli

def test_cli_missing_input():
    runner = CliRunner()
    # Execute without arguments
    result = runner.invoke(cli, [])
    assert result.exit_code != 0
    assert "Missing argument 'INPUT_FILES...'" in result.output

@patch("source.main.build_graph")
@patch("source.main.asyncio.run")
def test_cli_success(mock_asyncio_run, mock_build_graph, tmp_path):
    runner = CliRunner()
    
    # Create a dummy file
    dummy_file = tmp_path / "test.pdf"
    dummy_file.touch()
    
    output_file = tmp_path / "custom_output.md"
    
    mock_app = MagicMock()
    mock_build_graph.return_value = mock_app
    
    result = runner.invoke(cli, [str(dummy_file), "-o", str(output_file)])
    
    assert result.exit_code == 0
    assert "Initializing extraction for 1 file(s)..." in result.output
    
    # Verify build_graph was called
    mock_build_graph.assert_called_once()
    
    # Verify ainvoke was passed to asyncio.run
    mock_asyncio_run.assert_called_once()
    
    # Extract the initial state passed to ainvoke
    call_args = mock_app.ainvoke.call_args[0][0]
    assert call_args["raw_input_files"] == [str(dummy_file)]
    assert call_args["output_path"] == str(output_file)
    assert call_args["processed_documents"] == []
