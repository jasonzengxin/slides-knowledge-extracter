"""
CLI 入口模块 (CLI Entrypoint)

嗨！这里是我们整个工具的启动入口。
我们使用 `click` 库来构建优雅的命令行交互界面。
当用户在终端敲下 `uv run extract <文件> -o <输出>` 时，这里的代码就会被执行。
"""
import click
import asyncio
from source.orchestrator import build_graph

# @click.command() 装饰器将这个函数变成了一个 CLI 命令
@click.command()
# 接收用户传入的多个文件路径，nargs=-1 代表接收任意数量的参数，类型为存在的路径
@click.argument('input_files', nargs=-1, required=True, type=click.Path(exists=True))
# 接收可选参数 -o/--output，指定最后生成的 markdown 路径，默认为 'output.md'
@click.option('-o', '--output', 'output_file', default='output.md', help='Path to the output Markdown file.')
def cli(input_files, output_file):
    """
    Extracts and synthesizes knowledge from diverse document formats.
    (提取并综合多样化文档格式中的知识)
    """
    # 打印一些友好的提示信息给用户
    click.echo(f"Initializing extraction for {len(input_files)} file(s)...")
    click.echo(f"Output will be saved to: {output_file}")
    
    # 1. 构建状态机引擎 (LangGraph)
    # 这会返回一个编译好的工作流 (workflow) 应用
    app = build_graph()
    
    # 2. 初始化图状态 (Initial State)
    # 根据我们在 source/state.py 中定义的 ExtractorState，我们把用户的输入塞进去。
    initial_state = {
        "raw_input_files": list(input_files),
        "output_path": output_file,
        # 后续节点需要填充的数据，先用空列表和空字符串初始化
        "processed_documents": [],
        "extracted_md_files": [],
        "failed_extractions": [],
        "final_markdown": ""
    }
    
    # 3. 运行工作流
    # 因为我们在提取阶段 (Task 3) 会并发调用大模型，整个图的执行是异步的。
    # app.ainvoke 会驱动状态机从 START 节点一步步流转到 END 节点。
    asyncio.run(app.ainvoke(initial_state))

# 只有当直接用 python 运行这个文件时才会触发（现在我们主要通过 pyproject.toml 里的 entrypoint 运行）
if __name__ == '__main__':
    cli()
