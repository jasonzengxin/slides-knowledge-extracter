# PDF Knowledge Extractor - 用户手册

本工具可以将 PDF、PPT、图片文件中的内容提取并转换为结构化的 Markdown 文档。支持自动识别文字、表格，并将流程图/架构图转换为可渲染的 Mermaid 代码。

---

## 1. 环境要求

- **操作系统**：macOS 或 Linux
- **Python**：3.12 或更高版本
- **包管理器**：[uv](https://docs.astral.sh/uv/)（推荐）或 pip

## 2. 安装系统依赖

工具底层依赖 LibreOffice（PPT 转 PDF）和 Poppler（PDF 转图片），需要先安装：

**macOS：**
```bash
brew install libreoffice poppler
```

**Ubuntu/Debian：**
```bash
sudo apt-get install libreoffice poppler-utils
```

## 3. 安装工具

```bash
# 1. 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 克隆项目
git clone <项目地址> && cd pdf-absct

# 3. 安装依赖
uv sync
```

## 4. 配置 API Key

工具需要调用 AI 模型，需要配置以下 API Key：

```bash
# 从模板创建配置文件
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```bash
# 必填：SiliconFlow（用于图片文字识别）
SILICONFLOW_API_KEY="your_siliconflow_api_key_here"
# 获取地址：https://siliconflow.cn/

# 必填：Kimi（用于内容合成，优先使用）
KIMI_API_KEY="your_kimi_api_key_here"
# 获取地址：https://platform.moonshot.cn/

# 选填：GLM（Kimi 不可用时的备选）
GLM_API_KEY="your_glm_api_key_here"
# 获取地址：https://z.ai/
```

## 5. 使用

### 单文件提取

将一个或多个文件合成到一个 Markdown 文档：

```bash
uv run pdf-extract document.pdf -o output.md
```

```bash
# 多个文件合并
uv run pdf-extract a.pdf b.pptx diagram.png -o summary.md
```

支持的格式：`.pdf`、`.ppt`、`.pptx`、`.png`、`.jpg`、`.jpeg`

### 批量目录转换

将一个目录中的所有 PDF/PPT/图片分别转换为独立的 Markdown 文件：

```bash
uv run pdf-batch ./papers -o ./output
```

- 每个 PDF 生成一个同名 `.md` 文件（如 `report.pdf` → `report.md`）
- 已存在的 `.md` 文件会自动跳过，不会重复转换
- 处理失败的文件不会影响其他文件的转换

### 并发控制

默认同时处理 8 页，可以通过环境变量调整：

```bash
EXTRACTION_CONCURRENCY=5 uv run pdf-extract large.pdf -o output.md
```

## 6. 常见问题

**Q: 运行时报错 `Command 'soffice' not found`**
A: 没有安装 LibreOffice，参考第 2 步安装。

**Q: 运行时报错 `Failed to convert PDF to images`**
A: 没有安装 Poppler，参考第 2 步安装。

**Q: 转换很慢怎么办？**
A: 正常现象。每个文件需要经过：切页 → 视觉模型逐页识别 → 合成模型汇总。30 页的 PDF 大约需要 1-3 分钟，取决于文档复杂度和 API 响应速度。批量转换时已有 MD 文件会自动跳过。

**Q: 合成质量不满意？**
A: 合成质量取决于文档本身的清晰度和 AI 模型的能力。如果 Kimi 额度用尽，会自动切换到 GLM 备选模型。
