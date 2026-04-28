"""
总结合成模块 (Task 4: Knowledge Synthesis)

这里是我们的最后一环，另一个胖节点 (Fat Node)。
经历过 Task 3 之后，我们在 `.tmp/` 目录下散落了一堆单独的页面 Markdown。
如果是 100 页的 PPT，就有 100 个零散的 Markdown 片段。

这个模块的任务是：
利用超长上下文的大语言模型，让它一次性阅读这所有的碎片，
帮我们综合整理、去重排版，最终输出成一篇完美的终极 Markdown 文章！

模型优先级：Kimi (kimi-latest) → GLM (glm-5.1)
"""
import os
import time
import logging
from typing import Dict, Any
from anthropic import AsyncAnthropic

from source.state import ExtractorState
from source.config import KIMI_API_KEY, GLM_API_KEY

# 确保在初始化之前 API Key 是存在的
if not KIMI_API_KEY:
    logging.warning("KIMI_API_KEY is not set.")
if not GLM_API_KEY:
    logging.warning("GLM_API_KEY is not set. No fallback available if Kimi fails.")

# Kimi client (primary)
kimi_client = AsyncAnthropic(
    api_key=KIMI_API_KEY or "dummy_key",
    base_url="https://api.kimi.com/coding/"
)

# GLM client (fallback)
glm_client = AsyncAnthropic(
    api_key=GLM_API_KEY or "dummy_key",
    base_url="https://api.z.ai/api/anthropic/"
)

SYSTEM_PROMPT = (
    "你是一个专业的技术文档专家。我将提供一系列从原文档和图片中提取出的页面级 Markdown 数据（包含文字和Mermaid图表）。\n"
    "请将这些零散的页面内容重新组织、提炼和综合，输出一份结构清晰、逻辑连贯的最终 Markdown 文档。\n"
    "要求：\n"
    "1. 保持并整合原有的 Mermaid 图表代码。\n"
    "2. 去除重复的冗余信息。\n"
    "3. 合理使用标题 (H1, H2, H3)、列表和加粗等格式。\n"
    "4. 不要输出任何寒暄或解释性的废话，直接输出最终的 Markdown 文档内容。"
)


async def _call_model(client: AsyncAnthropic, model: str, full_payload: str) -> str:
    """调用单个模型并返回结果文本。"""
    response = await client.messages.create(
        model=model,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"以下是所有提取到的页面内容：\n\n{full_payload}\n\n请进行综合整理并直接输出最终的 Markdown。"
            }
        ],
        temperature=0.3
    )
    return response.content[0].text


async def synthesize_knowledge(extracted_md_files: list[str]) -> str:
    """
    核心合成逻辑：读取所有 Markdown 碎片，组装 Prompt，依次尝试 Kimi → GLM 进行汇总。
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

    full_payload = "\n\n========================================\n\n".join(combined_content)

    payload_size_kb = len(full_payload.encode("utf-8")) / 1024
    logging.info(f"Synthesis payload: {len(combined_content)} pages, {payload_size_kb:.1f} KB")

    # 2. 模型优先级列表：(client, model_name, display_name)
    models = []
    if KIMI_API_KEY:
        models.append((kimi_client, "kimi-latest", "Kimi"))
    if GLM_API_KEY:
        models.append((glm_client, "glm-5.1", "GLM"))

    if not models:
        logging.error("No API keys configured for any synthesis model.")
        fallback_msg = "> **Warning**: No synthesis model available (neither Kimi nor GLM). Returning raw concatenated content.\n\n"
        return fallback_msg + full_payload

    # 3. 依次尝试每个模型
    last_error = None
    for client, model, display_name in models:
        try:
            logging.info(f"Attempting synthesis with {display_name} ({model})...")
            t0 = time.time()
            final_markdown = await _call_model(client, model, full_payload)
            logging.info(f"Synthesis succeeded with {display_name} in {time.time() - t0:.1f}s")
            return final_markdown
        except Exception as e:
            last_error = e
            logging.warning(f"{display_name} ({model}) failed in {time.time() - t0:.1f}s: {e}. Trying next model...")

    # 4. 所有模型都失败了，降级返回原始内容
    logging.error(f"All synthesis models failed. Last error: {last_error}")
    fallback_msg = f"> **Warning**: All synthesis models failed (last error: {last_error}). Returning raw concatenated content below.\n\n"
    return fallback_msg + full_payload


async def execute_synthesis(state: ExtractorState) -> Dict[str, Any]:
    """
    Task 4 的执行函数。
    读取 Task 3 吐出的 extracted_md_files，并返回 final_markdown。
    """
    extracted_md_files = state.get("extracted_md_files", [])

    final_markdown = await synthesize_knowledge(extracted_md_files)

    return {"final_markdown": final_markdown}
