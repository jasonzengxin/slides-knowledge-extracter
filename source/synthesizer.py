"""
总结合成模块 (Task 4: Knowledge Synthesis)

这里是我们的最后一环，另一个胖节点 (Fat Node)。
经历过 Task 3 之后，我们在 `.tmp/` 目录下散落了一堆单独的页面 Markdown。
如果是 100 页的 PPT，就有 100 个零散的 Markdown 片段。

这个模块的任务是：
利用超长上下文的大语言模型（这里我们选用支持 Anthropic 协议的 Kimi API），
让它一次性阅读这所有的碎片，帮我们综合整理、去重排版，
最终输出成一篇完美的终极 Markdown 文章！
"""
import os
import logging
from typing import Dict, Any
from anthropic import AsyncAnthropic

from source.state import ExtractorState
from source.config import KIMI_API_KEY

# 确保在初始化之前 API Key 是存在的
if not KIMI_API_KEY:
    logging.warning("KIMI_API_KEY is not set. Synthesis will fail if called.")

kimi_client = AsyncAnthropic(
    api_key=KIMI_API_KEY or "dummy_key",
    base_url="https://api.kimi.com/coding/"
)

async def synthesize_knowledge(extracted_md_files: list[str]) -> str:
    """
    核心合成逻辑：读取所有 Markdown 碎片，组装 Prompt，请求 Kimi API 进行汇总。
    """
    if not extracted_md_files:
        return "No content was extracted to synthesize."
        
    # 1. 汇总所有中间 Markdown 文件的内容
    combined_content = []
    for md_path in extracted_md_files:
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                combined_content.append(f.read())
        else:
            logging.warning(f"Expected intermediate file not found: {md_path}")
            
    if not combined_content:
        return "No valid content found in the extracted files."
    
    # 用醒目的分隔符将每页内容隔开，帮助模型区分上下文
    full_payload = "\n\n========================================\n\n".join(combined_content)
    
    # 2. 构建 Kimi 的系统指令
    system_prompt = (
        "你是一个专业的技术文档专家。我将提供一系列从原文档和图片中提取出的页面级 Markdown 数据（包含文字和Mermaid图表）。\n"
        "请将这些零散的页面内容重新组织、提炼和综合，输出一份结构清晰、逻辑连贯的最终 Markdown 文档。\n"
        "要求：\n"
        "1. 保持并整合原有的 Mermaid 图表代码。\n"
        "2. 去除重复的冗余信息。\n"
        "3. 合理使用标题 (H1, H2, H3)、列表和加粗等格式。\n"
        "4. 不要输出任何寒暄或解释性的废话，直接输出最终的 Markdown 文档内容。"
    )

    try:
        # 3. 调用 Kimi (基于 Anthropic 协议)
        response = await kimi_client.messages.create(
            model="kimi-latest",  # Kimi coding endpoint 推荐的模型
            max_tokens=8192,      # 允许输出尽可能长的结果
            system=system_prompt,
            messages=[
                {
                    "role": "user", 
                    "content": f"以下是所有提取到的页面内容：\n\n{full_payload}\n\n请进行综合整理并直接输出最终的 Markdown。"
                }
            ],
            temperature=0.3       # 适度的 temperature，既保证逻辑连贯，又给一定的排版自由度
        )
        
        # Anthropic SDK 返回的 content 是一个包含 TextBlock 的列表
        final_markdown = response.content[0].text
        return final_markdown
        
    except Exception as e:
        logging.error(f"Synthesis failed during Kimi API call: {e}")
        # 容错降级：如果 Kimi 调用失败（例如超出最大 Token 等），我们也不能让用户的提取数据白费。
        # 直接把拼接好的原始内容返回，虽然没有高级排版，但至少数据保留下来了。
        fallback_msg = f"> **Warning**: Kimi API synthesis failed ({e}). Returning raw concatenated content below.\n\n"
        return fallback_msg + full_payload

async def execute_synthesis(state: ExtractorState) -> Dict[str, Any]:
    """
    Task 4 的执行函数。
    读取 Task 3 吐出的 extracted_md_files，并返回 final_markdown。
    """
    extracted_md_files = state.get("extracted_md_files", [])
    
    final_markdown = await synthesize_knowledge(extracted_md_files)
    
    # 最终把 Kimi 生成的 Markdown 字符串装在 'final_markdown' 中返回。
    # 接着这串内容就会被 node_output 写到磁盘上。
    return {"final_markdown": final_markdown}
