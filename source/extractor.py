"""
视觉提取模块 (Task 3: Multimodal Extraction)

这里是我们的胖节点 (Fat Node) 之一，涉及繁重的 AI 推理！
它的任务是：拿到 Task 2 切好的一堆单页图片，
并且用 **异步并发** 的方式去请求 SiliconFlow 的 Qwen3.6-27B 视觉模型。

大模型需要做的事在我们的 Prompt 里规定得很死（Schema-Driven）：
识别图片上的文字，理清流程图，最后把结果变成带有 Mermaid 代码的 Markdown 格式。
"""
import base64
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
from openai import AsyncOpenAI

from source.state import ExtractorState
from source.config import SILICONFLOW_API_KEY

# 确保在初始化之前 API Key 是存在的
if not SILICONFLOW_API_KEY:
    logging.warning("SILICONFLOW_API_KEY is not set. Extraction will fail if called.")

client = AsyncOpenAI(
    api_key=SILICONFLOW_API_KEY or "dummy_key",
    base_url="https://api.siliconflow.cn/v1"
)

def encode_file_to_base64(filepath: str) -> str:
    """将本地图片文件编码为 Base64 字符串，供视觉大模型读取。"""
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

async def extract_page_knowledge(page_meta: dict, original_path: str) -> str:
    """
    请求大模型处理单张图片，并将生成的 Markdown 保存到临时文件中。
    返回保存的 Markdown 文件的路径。
    """
    image_path = page_meta["image_path"]
    page_number = page_meta["page_number"]
    
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    base64_data = encode_file_to_base64(image_path)
    # JPEG 也是 Task 2 中统一保存的格式
    data_uri = f"data:image/jpeg;base64,{base64_data}"
    
    # 严格的系统约束 Prompt (Schema-Driven)
    prompt = (
        "你是一个专业的数据提取和文档分析专家。请精确提取这张图片（文档/PPT的一页）中的所有核心信息，并严格遵循以下规则输出：\n"
        "1. **核心文本提取**：精确识别并输出页面上的所有文本。保留原有的层级结构，使用 Markdown 格式（如标题使用 `#`，列表使用 `-`）进行排版。不要输出“这张图片展示了…”之类的废话，直接输出提取的内容。\n"
        "2. **图表与流程图解析**：如果页面中包含流程图、架构图或时序图，请理清所有的节点、条件分支和数据流向，并将其转化为合法的 **Mermaid 代码**（使用 `Graph TD` 或 `SequenceDiagram`）。\n"
        "3. **Mermaid 代码规范**：必须将 Mermaid 代码包裹在 ```mermaid 和 ``` 之间。生成标准可全平台渲染的 Mermaid `graph TD` 或 `sequenceDiagram` 流程图：全部节点文本用双引号包裹（例如：`A[\"节点内容\"]`）；条件判断统一使用 `-->|是|` / `-->|否|` 语法，连线仅用 `-->`；长文本换行只用 `<br/>`；绝对禁止使用 `subgraph`、自定义样式 (`classDef`/`style`)、转义字符、特殊符号与代码注释；菱形判断节点使用 `{}` 格式（例如：`B{\"判断条件\"}`）；无多余空格与非法换行，只输出纯净可直接渲染的 mermaid 代码。\n"
        "4. **无图表处理**：如果页面中完全没有流程图或架构图，**不要**生编硬造任何 Mermaid 代码，只需做好文本提取即可。"
    )

    # 我们使用 SiliconFlow 兼容的 response_format JSON 来强制大模型将结果包在一个 JSON 属性里
    # 这样能最大程度避免大模型在代码块外瞎解释，导致我们解析 Markdown 失败。
    response = await client.chat.completions.create(
        model="Qwen/Qwen3.6-27B",
        messages=[
            {"role": "system", "content": "You must output a valid JSON object containing exactly one key 'page_markdown'."},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": prompt}
            ]}
        ],
        response_format={"type": "json_object"},
        temperature=0.1  # 极低的温度，确保抽取的确定性，减少幻觉
    )
    
    # 解析 JSON 获取 Markdown
    raw_json = response.choices[0].message.content
    try:
        result_data = json.loads(raw_json)
        markdown_content = result_data.get("page_markdown", "")
    except json.JSONDecodeError:
        # Fallback: 如果大模型实在不听话没输出标准 JSON，我们直接拿它的原始内容作为 Markdown。
        markdown_content = raw_json
        
    # 保存到中间文件
    # 生成如: .tmp/slide_page_1.md
    output_filename = f".tmp/{Path(original_path).stem}_page_{page_number}.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        # 在顶部打个标记，方便最终大模型汇总时知道这是哪一页
        f.write(f"<!-- Source: {Path(original_path).name} | Page: {page_number} -->\n\n")
        f.write(markdown_content)
        
    return output_filename

async def execute_extraction_parallel(state: ExtractorState) -> Dict[str, Any]:
    """
    Task 3 的执行函数。
    由于一个文档可能被拆成几十张图，串行请求 API 会慢到让人崩溃。
    所以我们使用 Python 的 asyncio.gather 并发去请求。
    """
    processed_documents = state.get("processed_documents", [])
    
    # 1. 展平所有文档的页面，构建任务列表
    all_pages = []
    for doc in processed_documents:
        original_path = doc["original_path"]
        for page in doc["pages"]:
            all_pages.append({
                "original_path": original_path,
                "page_meta": page
            })
            
    if not all_pages:
        return {"extracted_md_files": [], "failed_extractions": []}

    # 2. 创建并发协程任务
    tasks = [
        extract_page_knowledge(p["page_meta"], p["original_path"]) 
        for p in all_pages
    ]
    
    # 3. 并发执行！
    # 重点：return_exceptions=True 是 "Best Effort" 机制的灵魂。
    # 它保证了哪怕第 50 页因为网络波动报错抛出 Exception，
    # asyncio.gather 也不会把其他 99 页的成功任务取消掉，而是把错误当作结果返回在列表中。
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. 统计成功与失败的记录
    successes = []
    failures = []
    
    for item, result in zip(all_pages, results):
        if isinstance(result, Exception):
            failures.append({
                "file": item["original_path"], 
                "page": item["page_meta"]["page_number"], 
                "error": str(result)
            })
            logging.error(f"Extraction failed for {item['original_path']} page {item['page_meta']['page_number']}: {result}")
        else:
            successes.append(result)  # result 就是我们返回的 md_file_path
            
    # 返回成功拿到的 markdown 文件路径列表，和报错的页面信息列表。
    # LangGraph 会自动把这个字典合并到主状态 ExtractorState 中。
    return {
        "extracted_md_files": successes,
        "failed_extractions": failures
    }
