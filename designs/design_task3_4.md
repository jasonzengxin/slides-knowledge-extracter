# Design Document: Task 3 & 4 - Extraction & Synthesis

## 1. Overview
This document details the design for the core reasoning nodes.
*   **Task 3 (Page Extraction):** Uses SiliconFlow's `Qwen/Qwen3.6-27B` vision model to process each page image, extracting text and converting flowcharts to Mermaid syntax. Saves the output to intermediate Markdown files.
*   **Task 4 (Synthesis):** Uses the Moonshot **Kimi API** (via the Anthropic SDK compatibility layer) to read all intermediate Markdown files and synthesize them into a final output document.

## 2. Task 3: Page-by-Page Extraction

### 2.1. Execution Logic
```python
import base64
import json
from pathlib import Path
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="YOUR_SILICONFLOW_API_KEY",
    base_url="https://api.siliconflow.cn/v1"
)

def encode_file_to_base64(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

async def extract_page_knowledge(page_meta: dict) -> str:
    image_path = page_meta["image_path"]
    base64_data = encode_file_to_base64(image_path)
    data_uri = f"data:image/jpeg;base64,{base64_data}"
    
    prompt = (
        "你是一个专业的数据提取和文档分析专家。请精确提取这张图片（文档/PPT的一页）中的所有核心信息，并严格遵循以下规则输出：\n"
        "1. **核心文本提取**：精确识别并输出页面上的所有文本。保留原有的层级结构，使用 Markdown 格式（如标题使用 `#`，列表使用 `-`）进行排版。不要输出“这张图片展示了…”之类的废话，直接输出提取的内容。\n"
        "2. **图表与流程图解析**：如果页面中包含流程图、架构图或时序图，请理清所有的节点、条件分支和数据流向，并将其转化为合法的 **Mermaid 代码**（使用 `Graph TD` 或 `SequenceDiagram`）。\n"
        "3. **Mermaid 代码规范**：必须将 Mermaid 代码包裹在 ```mermaid 和 ``` 之间。生成标准可全平台渲染的 Mermaid `graph TD` 或 `sequenceDiagram` 流程图：全部节点文本用双引号包裹（例如：`A[\"节点内容\"]`）；条件判断统一使用 `-->|是|` / `-->|否|` 语法，连线仅用 `-->`；长文本换行只用 `<br/>`；绝对禁止使用 `subgraph`、自定义样式 (`classDef`/`style`)、转义字符、特殊符号与代码注释；菱形判断节点使用 `{}` 格式（例如：`B{\"判断条件\"}`）；无多余空格与非法换行，只输出纯净可直接渲染的 mermaid 代码。\n"
        "4. **无图表处理**：如果页面中完全没有流程图或架构图，**不要**生编硬造任何 Mermaid 代码，只需做好文本提取即可。"
    )

    # We use response_format JSON to ensure clean parsing, wrapping the markdown in a property.
    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "extraction",
            "schema": {
                "type": "object",
                "properties": {
                    "page_markdown": {"type": "string"}
                },
                "required": ["page_markdown"],
                "additionalProperties": False
            },
            "strict": True
        }
    }

    response = await client.chat.completions.create(
        model="Qwen/Qwen3.6-27B",
        messages=[
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": prompt}
            ]}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    # Parse result
    raw_json = response.choices[0].message.content
    result_data = json.loads(raw_json)
    markdown_content = result_data.get("page_markdown", "")
    
    # Save to intermediate file
    output_filename = f".tmp/{Path(page_meta['original_path']).stem}_page_{page_meta['page_number']}.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"<!-- Source: {page_meta['original_path']} | Page: {page_meta['page_number']} -->\n\n")
        f.write(markdown_content)
        
    return output_filename
```

## 3. Task 4: Knowledge Synthesis Engine (Kimi + GLM Fallback)

### 3.1. Model Fallback Strategy

The synthesis engine uses a **Kimi → GLM-5.1** fallback chain. Both models are accessed via the Anthropic SDK compatibility layer:

| Priority | Model | Endpoint | Role |
|:---:|:---|:---|:---|
| 1 | `kimi-latest` | `https://api.kimi.com/coding/` | Primary |
| 2 | `glm-5.1` | `https://api.z.ai/api/anthropic/` | Fallback |

If Kimi fails (rate limit, quota exhausted, service unavailable), the system automatically tries GLM-5.1. Only if both models fail does it degrade to returning raw concatenated content.

### 3.2. Implementation

```python
from anthropic import AsyncAnthropic

# Primary: Kimi
kimi_client = AsyncAnthropic(
    api_key=KIMI_API_KEY,
    base_url="https://api.kimi.com/coding/"
)

# Fallback: GLM
glm_client = AsyncAnthropic(
    api_key=GLM_API_KEY,
    base_url="https://api.z.ai/api/anthropic/"
)

async def synthesize_knowledge(extracted_md_files: list[str]) -> str:
    # ... read and combine markdown files ...

    models = []
    if KIMI_API_KEY:
        models.append((kimi_client, "kimi-latest", "Kimi"))
    if GLM_API_KEY:
        models.append((glm_client, "glm-5.1", "GLM"))

    for client, model, name in models:
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[...],
                temperature=0.3
            )
            return response.content[0].text
        except Exception as e:
            logging.warning(f"{name} failed: {e}. Trying next model...")

    # All models failed — degrade to raw content
    return fallback_msg + full_payload
```