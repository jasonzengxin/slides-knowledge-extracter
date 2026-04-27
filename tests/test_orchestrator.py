import pytest
import os
from source.orchestrator import build_graph, node_output

def test_build_graph():
    app = build_graph()
    
    # Assert nodes exist
    nodes = app.get_graph().nodes
    assert "node_preprocess" in nodes
    assert "node_extract" in nodes
    assert "node_synthesize" in nodes
    assert "node_output" in nodes

def test_node_output_success(tmp_path):
    output_path = tmp_path / "output.md"
    
    state = {
        "output_path": str(output_path),
        "final_markdown": "# Success Document",
        "failed_extractions": []
    }
    
    result = node_output(state)
    
    assert result == {}
    assert output_path.exists()
    content = output_path.read_text()
    assert content == "# Success Document"

def test_node_output_with_failures(tmp_path):
    output_path = tmp_path / "output_failed.md"
    
    state = {
        "output_path": str(output_path),
        "final_markdown": "# Success Document",
        "failed_extractions": [{"file": "test.pdf", "page": 1, "error": "API Timeout"}]
    }
    
    node_output(state)
    
    assert output_path.exists()
    content = output_path.read_text()
    assert "# Success Document" in content
    assert "## Processing Errors" in content
    assert "- **test.pdf** (Page 1): API Timeout" in content

def test_node_output_no_markdown(tmp_path):
    output_path = tmp_path / "no_output.md"
    
    state = {
        "output_path": str(output_path),
        "final_markdown": "",
        "failed_extractions": []
    }
    
    node_output(state)
    
    # File shouldn't be created if there's no final markdown
    assert not output_path.exists()
