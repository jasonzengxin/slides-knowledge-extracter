# Task 3: Page-by-Page Multimodal Extraction

## 1. Description
This is a **Fat Node** (Reasoning). It utilizes `Qwen/Qwen3.6-27B` via SiliconFlow to analyze a single compressed page image. The goal is to accurately transcribe text and interpret diagrams into Mermaid syntax, outputting the result as an intermediate Markdown string, which is then saved to disk.

## 2. DSPy / Schema-Driven Contract

### Signature (Input)
```json
{
  "type": "object",
  "properties": {
    "image_path": { "type": "string" },
    "original_source": { "type": "string" },
    "page_number": { "type": "integer" }
  },
  "required": ["image_path", "original_source", "page_number"]
}
```

### Signature (Output Schema for LLM)
To strictly enforce output quality while obtaining Markdown, we enforce a JSON output where the value is the Markdown string.
```json
{
  "type": "object",
  "properties": {
    "page_markdown": { 
      "type": "string",
      "description": "The detailed markdown transcription of the page, including Mermaid diagrams."
    }
  },
  "required": ["page_markdown"]
}
```

## 3. Prompt Engineering
The system prompt will explicitly instruct the model:
> 你是一个专业的数据提取和文档分析专家。请精确提取这张图片（文档/PPT的一页）中的所有核心信息，并严格遵循以下规则输出：
> 1. **核心文本提取**：精确识别并输出页面上的所有文本。保留原有的层级结构，使用 Markdown 格式（如标题使用 `#`，列表使用 `-`）进行排版。不要输出“这张图片展示了…”之类的废话，直接输出提取的内容。
> 2. **图表与流程图解析**：如果页面中包含流程图、架构图或时序图，请理清所有的节点、条件分支和数据流向，并将其转化为合法的 **Mermaid 代码**（使用 `Graph TD` 或 `SequenceDiagram`）。
> 3. **Mermaid 代码规范**：必须将 Mermaid 代码包裹在 ```mermaid 和 ``` 之间。生成标准可全平台渲染的 Mermaid `graph TD` 或 `sequenceDiagram` 流程图：全部节点文本用双引号包裹（例如：`A["节点内容"]`）；条件判断统一使用 `-->|是|` / `-->|否|` 语法，连线仅用 `-->`；长文本换行只用 `<br/>`；绝对禁止使用 `subgraph`、自定义样式 (`classDef`/`style`)、转义字符、特殊符号与代码注释；菱形判断节点使用 `{}` 格式（例如：`B{"判断条件"}`）；无多余空格与非法换行，只输出纯净可直接渲染的 mermaid 代码。
> 4. **无图表处理**：如果页面中完全没有流程图或架构图，**不要**生编硬造任何 Mermaid 代码，只需做好文本提取即可。

## 4. Execution Details
*   Read the compressed image from `image_path` and encode to Base64.
*   Call SiliconFlow Vision API.
*   Extract `page_markdown` from the JSON response.
*   Save `page_markdown` to a local intermediate `.md` file in `.tmp/` (e.g., `[source]_page_[num].md`).
*   Return the path to this newly created intermediate Markdown file to the Orchestrator.
