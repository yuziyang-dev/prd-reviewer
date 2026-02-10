# PRD Reviewer — 设计单智能审查工具

上传 PM 的设计单 PDF，AI 自动从**设计师视角 + 技术视角**双重审查，生成结构化报告。

## 功能

- PDF 逐页截图 + 文字提取，支持原型图/流程图/竞品截图识别
- 设计师六维度 + 技术七维度全面审查
- 流式输出审查报告，支持复制和下载 Markdown
- 支持 OpenRouter / Anthropic Claude / OpenAI GPT-4o

## 部署到 Vercel

### 1. 推送到 GitHub

```bash
cd prd-reviewer
git init && git add . && git commit -m "init"
gh repo create prd-reviewer --public --push --source=.
```

### 2. 导入 Vercel

1. 打开 [vercel.com/new](https://vercel.com/new)
2. 导入你的 GitHub 仓库
3. 直接部署，无需额外配置

### 3. 使用

访问部署后的 URL，点击设置齿轮：
- 选择 **OpenRouter**
- 填入 API Key（在 [openrouter.ai/keys](https://openrouter.ai/keys) 获取）
- 开始审查

## 本地开发

```bash
pip install -r requirements.txt
python app.py
# 访问 http://localhost:8000
```

## 已知限制

- **Vercel 请求体上限 4.5MB**：超大 PDF 文件可能上传失败，建议压缩后上传
- **Vercel 超时**：免费版 60s / Pro 版 300s，页数特别多时可能超时
- 本地运行无上述限制

## 技术栈

- **后端**：FastAPI + PyMuPDF + OpenAI SDK
- **前端**：HTML + Tailwind CSS + marked.js
- **部署**：Vercel Python Serverless Functions
