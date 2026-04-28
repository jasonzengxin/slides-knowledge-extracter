import pytest
from pathlib import Path
from click.testing import CliRunner
from PIL import Image

from source.main import extract

@pytest.fixture
def dummy_image(tmp_path: Path) -> Path:
    """Creates a dummy image file for testing."""
    img_path = tmp_path / "dummy_test.jpg"
    # Create a simple 100x100 red square image
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path, format="JPEG")
    return img_path

def test_cli_e2e_extraction(dummy_image: Path, tmp_path: Path):
    """
    End-to-end test for the CLI extraction pipeline.
    This test runs the 'extract' command with a dummy image.
    Currently, this will FAIL its assertions since the nodes are empty stubs
    and no real Markdown content is generated yet.
    """
    runner = CliRunner()
    output_md = tmp_path / "summary_output.md"
    
    # Run the CLI command
    # equivalent to: uv run extract <dummy_image> -o <output_md>
    result = runner.invoke(extract, [str(dummy_image), "-o", str(output_md)])
    
    # The CLI shouldn't crash entirely
    assert result.exit_code == 0, f"CLI crashed with error: {result.output}"
    
    # We expect the final output markdown file to be created
    assert output_md.exists(), "The output markdown file was not generated."
    
    content = output_md.read_text(encoding="utf-8")
    
    # For a fully functional E2E pipeline, we expect the content to have actual synthesized text.
    # Since our stubs currently return empty strings, this assertion will intentionally fail.
    assert len(content.strip()) > 0, "The generated markdown file is empty. (Tasks 2-4 are not implemented yet)"

    # We also expect the orchestrator to clean up the temporary hidden directory
    # but we can't easily check the root .tmp/ here since it might conflict with other runs.
    # However, if the tasks work correctly, this test will pass.
