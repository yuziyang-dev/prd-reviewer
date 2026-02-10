# PRD Reviewer — 设计单智能审查工具

上传 PM 的设计单 PDF，AI 自动从**设计师视角 + 技术视角**双重审查，生成结构化报告。

## 功能

- PDF 逐页截图 + 文字提取，支持原型图/流程图/竞品截图识别
- 设计师六维度 + 技术七维度全面审查
- 流式输出审查报告，支持复制和下载 Markdown
- 支持 OpenRouter / Anthropic Claude / OpenAI GPT-4o

## 部署到 Railway（推荐）

### 1. 推送到 GitHub

```bash
cd prd-reviewer
gh repo create prd-reviewer --public --push --source=.
```

### 2. 部署到 Railway

1. 打开 [railway.app/new](https://railway.app/new)
2. 选择 **Deploy from GitHub repo**
3. 选择 `prd-reviewer` 仓库
4. Railway 自动检测 Python 项目并部署
5. 部署完成后，在 Settings → Networking 点击 **Generate Domain** 获取公网 URL

### 3. 使用

访问部署后的 URL，点击右上角设置齿轮：
- 选择 **OpenRouter**（或其他 AI 服务商）
- 填入 API Key（在 [openrouter.ai/keys](https://openrouter.ai/keys) 获取）
- 上传 PDF，开始审查

## 本地开发

```bash
pip install -r requirements.txt
python app.py
# 访问 http://localhost:8000
```

## 技术栈

- **后端**：FastAPI + PyMuPDF + OpenAI SDK
- **前端**：HTML + Tailwind CSS + marked.js
- **部署**：Railway（无文件大小限制，超时上限 5 分钟）
