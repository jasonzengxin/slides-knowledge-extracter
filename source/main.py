"""
CLI 入口模块 (CLI Entrypoint)

两个独立命令：
  pdf-extract <文件...> -o <输出.md>   单/多文件提取，合成到一个 MD
  pdf-batch <输入目录> -o <输出目录>   批量目录转换，每个文件独立输出 MD
"""
import os
import time
import asyncio
import logging
from pathlib import Path
import click
from source.orchestrator import build_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

SUPPORTED_EXTENSIONS = {'.pdf', '.ppt', '.pptx', '.png', '.jpg', '.jpeg'}


async def _run_pipeline(input_files: list[str], output_path: str):
    """运行单次 LangGraph 管线。"""
    t0 = time.time()
    app = build_graph()
    initial_state = {
        "raw_input_files": input_files,
        "output_path": output_path,
        "processed_documents": [],
        "extracted_md_files": [],
        "failed_extractions": [],
        "final_markdown": ""
    }
    await app.ainvoke(initial_state)
    logging.info(f"Pipeline finished in {time.time() - t0:.1f}s -> {output_path}")


# ---- pdf-extract 命令 ----

@click.command()
@click.argument('input_files', nargs=-1, required=True, type=click.Path(exists=True))
@click.option('-o', '--output', 'output_file', default='output.md', help='Path to the output Markdown file.')
def extract(input_files, output_file):
    """
    Extracts and synthesizes knowledge from one or more files into a single Markdown document.

    支持格式：PDF, PPT, PPTX, PNG, JPG, JPEG
    """
    click.echo(f"Initializing extraction for {len(input_files)} file(s)...")
    click.echo(f"Output will be saved to: {output_file}")

    asyncio.run(_run_pipeline(list(input_files), output_file))


# ---- pdf-batch 命令 ----

@click.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('-o', '--output', 'output_dir', required=True, help='Output directory for generated Markdown files.')
def batch(input_dir, output_dir):
    """
    Batch convert all supported files in a directory to individual Markdown files.

    每个 PDF/PPT/图片文件独立转换，输出到指定目录。已存在的 MD 文件会自动跳过。
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # 扫描输入目录
    files = sorted([
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    if not files:
        click.echo(f"No supported files found in {input_dir}")
        return

    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Found {len(files)} file(s) in {input_dir}")
    click.echo(f"Output directory: {output_dir}")
    click.echo("")

    skipped = []
    successes = []
    failures = []

    batch_t0 = time.time()

    for i, f in enumerate(files, start=1):
        output_file = output_path / f"{f.stem}.md"

        if output_file.exists():
            click.echo(f"[{i}/{len(files)}] Skipping (already exists): {f.name}")
            skipped.append(f.name)
            continue

        click.echo(f"[{i}/{len(files)}] Processing: {f.name}")

        try:
            file_t0 = time.time()
            asyncio.run(_run_pipeline([str(f)], str(output_file)))
            click.echo(f"  Done in {time.time() - file_t0:.1f}s")
            successes.append(f.name)
        except Exception as e:
            click.echo(f"  Failed in {time.time() - file_t0:.1f}s: {e}")
            failures.append({"file": f.name, "error": str(e)})

    click.echo("")
    click.echo(f"Batch complete: {len(skipped)} skipped, {len(successes)} succeeded, {len(failures)} failed in {time.time() - batch_t0:.1f}s")
    if failures:
        click.echo("Failed files:")
        for fail in failures:
            click.echo(f"  - {fail['file']}: {fail['error']}")


if __name__ == '__main__':
    import sys
    # pdf-extract 或 pdf-batch 由 pyproject.toml entrypoint 调用
    # python -m source.main extract/batch 作为 fallback
    if len(sys.argv) > 1 and sys.argv[1] in ('extract', 'batch'):
        cmd = sys.argv.pop(1)
        {'extract': extract, 'batch': batch}[cmd]()
    else:
        extract()
