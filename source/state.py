"""
状态定义模块 (State Definition Module)

欢迎加入团队！在这个项目中，我们使用了 LangGraph 框架来构建我们的状态机（State Machine）。
LangGraph 强制要求我们定义一个全局的“状态字典”（这里我们使用了 TypedDict）。
这个状态会在所有的执行节点（Nodes）之间流转，每一个节点都可以读取上一个节点处理后的状态，
并且将自己处理完的数据合并回这个状态中。

这种“Schema-Driven”（强契约化）的设计，能让我们在复杂的流转中清楚地知道：
现在到了哪一步？当前可用数据长什么样？
"""
from typing import TypedDict, List, Dict, Any, Optional

class ExtractorState(TypedDict):
    # ==========================================
    # 1. 初始化状态 (INIT State)
    # 这些是在 CLI 命令启动时，由用户传入的参数
    # ==========================================
    
    # 用户想要处理的原始文件路径列表（例如：['doc.pdf', 'slide.ppt']）
    raw_input_files: List[str]
    # 用户指定的输出 Markdown 文件路径
    output_path: str
    
    # ==========================================
    # 2. 预处理状态 (PREPROCESSING State)
    # 由 Task 2 (node_preprocess) 填充
    # ==========================================
    
    # 存储拆分和压缩后的文档数据。
    # 结构示例：
    # [
    #   {
    #     "original_path": "path/to/doc.pdf", 
    #     "pages": [
    #       {"page_number": 1, "image_path": ".tmp/doc_page1.jpg"},
    #       {"page_number": 2, "image_path": ".tmp/doc_page2.jpg"}
    #     ]
    #   }
    # ]
    # 这是由于视觉大模型处理单张图片更高效，所以多页 PDF/PPT 会被拆分成多张单页图片。
    processed_documents: List[Dict[str, Any]] 
    
    # ==========================================
    # 3. 提取状态 (EXTRACTION State)
    # 由 Task 3 (node_extract) 并发处理后填充
    # ==========================================
    
    # 成功通过视觉大模型（SiliconFlow Qwen3.6）提取出来的中间 Markdown 文件路径列表。
    # 每一张图片对应一个 markdown 文件，这些文件存放在 .tmp/ 下。
    extracted_md_files: List[str]  
    
    # 在并行处理各页图片时，如果某些页面调用大模型失败（比如超时），我们会把它记录在这里。
    # 这体现了我们的 "Best Effort" (尽力而为) 策略——不因为一页失败就中断整个流程。
    # 结构示例: {"file": "doc.pdf", "page": 1, "error": "API Timeout"}
    failed_extractions: List[Dict[str, Any]]
    
    # ==========================================
    # 4. 合成状态 (SYNTHESIS State)
    # 由 Task 4 (node_synthesize) 填充
    # ==========================================
    
    # 最终由 Kimi 大模型将所有 extracted_md_files 综合整理后生成的 Markdown 字符串。
    # Orchestrator 会在最后一步把这段文字写入到 output_path 文件中。
    final_markdown: Optional[str]  
