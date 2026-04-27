"""
宏观架构与状态机编排模块 (DAG & State Machine Orchestrator)

欢迎来到系统的“指挥中心”！
这里不负责干具体的脏活累活（比如调大模型、切图等），它只负责一件事：**宏观流程编排**。
我们使用了 LangGraph 构建了一个有向无环图 (DAG)。
数据在这里像流水线一样，从一个节点流向下一个节点。
"""
from langgraph.graph import StateGraph, START, END
from source.state import ExtractorState
from source.preprocessor import execute_preprocessing
from source.extractor import execute_extraction_parallel
from source.synthesizer import execute_synthesis

def node_output(state: ExtractorState) -> dict:
    """
    终点节点：负责将最后合成的 Markdown 数据落盘写入文件。
    这是一个普通的同步函数，因为写文件很快。
    """
    # 从流入的 state 中读取前面节点产生的数据
    output_path = state.get("output_path", "output.md")
    final_markdown = state.get("final_markdown", "")
    failed = state.get("failed_extractions", [])
    
    if final_markdown:
        # 如果生成了内容，就打开文件写入
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_markdown)
            
            # 如果在并发处理 Task 3 (视觉提取) 时有报错的页面，
            # 我们按照 "Best Effort" (尽力而为) 策略，把报错信息追加到文档末尾。
            # 这样用户既能拿到大部分成功的数据，也能清楚知道哪些地方失败了。
            if failed:
                f.write("\n\n## Processing Errors\n")
                for err in failed:
                    f.write(f"- **{err.get('file')}** (Page {err.get('page')}): {err.get('error')}\n")
                    
        print(f"Extraction complete! Output saved to: {output_path}")
    else:
        print("Extraction failed or no content generated.")
        
    # 返回空字典，表示我们不再对 State 进行追加修改了
    return {}

def build_graph() -> StateGraph:
    """
    构建并编译 LangGraph 状态机。
    这里定义了整个应用的心跳流转规则。
    """
    # 实例化一个 StateGraph，绑定我们严格定义的 ExtractorState
    workflow = StateGraph(ExtractorState)

    # ==========================
    # 1. 注册所有的功能节点 (Nodes)
    # ==========================
    # Task 2: 预处理 (切图与压缩)
    workflow.add_node("node_preprocess", execute_preprocessing)
    # Task 3: 视觉提取 (并发调用 Qwen 大模型)
    workflow.add_node("node_extract", execute_extraction_parallel)
    # Task 4: 文本总结 (调用 Kimi 汇总页面)
    workflow.add_node("node_synthesize", execute_synthesis)
    # 收尾: 落盘写文件
    workflow.add_node("node_output", node_output)

    # ==========================
    # 2. 定义流转边 (Edges)
    # ==========================
    # 我们这是一个确定性的线性 DAG：START -> Task 2 -> Task 3 -> Task 4 -> Output -> END
    workflow.add_edge(START, "node_preprocess")
    workflow.add_edge("node_preprocess", "node_extract")
    workflow.add_edge("node_extract", "node_synthesize")
    workflow.add_edge("node_synthesize", "node_output")
    workflow.add_edge("node_output", END)

    # 编译并返回这个状态机，供 main.py 启动
    return workflow.compile()
