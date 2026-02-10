"""
PRD Reviewer API — Vercel Serverless Function
PDF 处理 + LLM 调用 + SSE 流式输出
"""

import asyncio
import base64
import json
from pathlib import Path

import fitz  # PyMuPDF
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import StreamingResponse

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="PRD Reviewer API")


# ---------------------------------------------------------------------------
# Provider 配置
# ---------------------------------------------------------------------------

PROVIDER_DEFAULTS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4",
        "format": "openai",
    },
    "anthropic": {
        "base_url": None,
        "model": "claude-sonnet-4-20250514",
        "format": "anthropic",
    },
    "openai": {
        "base_url": None,
        "model": "gpt-4o",
        "format": "openai",
    },
}


# ---------------------------------------------------------------------------
# System Prompt — 双视角审查框架
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一位资深的产品需求文档审查专家。你将收到一份 PM 的设计单/需求文档的完整内容，包括文字和每一页的截图（含原型图、流程图、竞品截图等视觉内容）。

请从**设计师视角**和**技术视角**双重审查这份文档。

## 审查步骤

### 步骤一：原型图与文字交叉验证
先做一遍交叉比对：
- 原型图中的文案/数据是否与文字描述一致？
- 原型中展示的页面是否覆盖了文字提到的所有场景？
- 是否存在占位内容未替换（重复假文案、示意数据与描述矛盾）？
- 竞品截图与对应文字说明是否匹配？

### 步骤二：设计师视角审查（六维度）

**A1. 页面目标清晰度**
- 每个页面的核心行为（最重要的一个动作）是否明确？
- 信息层级和视觉权重优先级是否给出？同级模块之间的主次是否明确？

**A2. 用户场景与情感意图**
- 用户到达页面时的前置情绪和心理状态是否描述？
- "期待感"、"专业感"等模糊词汇是否配有具体竞品参考？
- 竞品截图是否说明了参考哪个方面（布局？配色？动效？）以及不参考什么？
- 是否有反面参考（不希望设计成什么样）？

**A3. 完整页面与状态清单**
- 每个页面/组件是否覆盖四态：首次状态、常规状态、空状态、异常状态？
- 同一元素的所有可能状态是否穷举（不能只有"进行中/已完成"，还有"未开始"、"刚完成的瞬间"、"过期"等）？
- 能否从文档直接列出完整的设计交付页面清单？

**A4. 设计方向与约束**
- 竞品截图是否配有文字分析（参考什么/不参考什么/为什么）？
- 是否存在"方案待定"、"没想好"的待决策项？是否阻塞设计开始？
- 设计约束是否明确（复用组件、技术限制、扩展计划、平台适配）？

**A5. 内容与配图确定性**
- 每处文案是定稿还是占位？原型图文案是否和文字描述一致？
- 动态文案的变量取值范围是否明确？极端长度下 UI 兼容性是否考虑？
- 需要配图/插画/图标的位置，风格方向是否明确？
- 多语言支持和翻译膨胀是否考虑？

**A6. 流转关系完整性**
- 每个页面的所有入口和出口是否逐一明确？
- 流程图是否只画了 happy path？分支/返回/退出路径是否标注？
- 弹窗的触发条件、关闭方式、优先级层级是否清晰？

### 步骤三：技术视角审查（七维度）

**B1. 结构完整性**：检查是否包含需求背景、目标、用户、流程图、原型图、状态枚举、异常处理、Checklist、文案、埋点、输出物、排期

**B2. 目标与指标**：数据目标是否可量化、成功标准和衡量方式、A/B 方案

**B3. 逻辑一致性**：流程闭合性、数据来源和计算规则、状态穷举和转换条件、前后文矛盾

**B4. 边界与异常**：网络异常/加载/降级、首次使用/回归/重装/多设备、数据空/异常/时区/跨天、订阅差异/新老用户

**B5. 交互细节**：点击区域、动画转场、手势、弹窗层级、Toast、返回逻辑、深色模式

**B6. 文案与多语言**：文案定稿、动态变量、极端长度兼容、多语言排版

**B7. 可扩展性**：扩展影响、功能冲突、性能、埋点、接口依赖

## 特别注意
- 仔细查看每一页的原型图，检查占位内容、内容错误、前后不一致
- 检查流程图是否覆盖所有关键路径
- 检查竞品截图是否有分析说明

## 输出格式

请严格按照以下 Markdown 格式输出：

```
# 设计单审查报告

## 一、文档概述
一段话概括内容和整体评价。

## 二、审查结果总览

### 设计师视角

| 维度 | 评级 | 问题数 |
|------|------|-------|
| 页面目标清晰度 | ✅/⚠️/❌ | N |
| 用户场景与情感意图 | ✅/⚠️/❌ | N |
| 页面与状态完整性 | ✅/⚠️/❌ | N |
| 设计方向与约束 | ✅/⚠️/❌ | N |
| 内容与配图确定性 | ✅/⚠️/❌ | N |
| 流转关系完整性 | ✅/⚠️/❌ | N |

### 技术视角

| 维度 | 评级 | 问题数 |
|------|------|-------|
| 结构完整性 | ✅/⚠️/❌ | N |
| 目标与指标 | ✅/⚠️/❌ | N |
| 逻辑一致性 | ✅/⚠️/❌ | N |
| 边界与异常 | ✅/⚠️/❌ | N |
| 交互细节 | ✅/⚠️/❌ | N |
| 文案与多语言 | ✅/⚠️/❌ | N |
| 可扩展性 | ✅/⚠️/❌ | N |

评级标准：✅ 完善 / ⚠️ 部分缺失 / ❌ 严重缺失

## 三、详细问题清单

### 🔴 阻塞设计/开发开始
逐条列出，每条标注 [设计]/[技术]/[通用]，包含：问题描述、所在位置、影响、建议。

### 🟡 过程中需确认
逐条列出，每条标注视角标签，包含：问题描述、建议。

### 🟢 完善建议
逐条列出。

## 四、设计交付清单

### [模块名称]
| 页面/组件 | 需要设计的状态 | 备注 |
|----------|-------------|------|

## 五、模糊表述标记

| 位置 | 原文 | 问题 |
|------|------|------|

## 六、待 PM 回复

### 🔴 阻塞设计/开发开始
1. [问题]

### 🟡 过程中需确认
2. [问题]
```

## 审查原则
- 设计师视角优先，技术视角补充
- 有理有据，指出具体位置，引用原文
- 给出建议而非仅指出问题
- 区分阻塞级别
- 标记而非否定模糊表述
- 尊重 PM 的设计判断
- 使用中文输出
"""


# ---------------------------------------------------------------------------
# PDF 处理
# ---------------------------------------------------------------------------

def process_pdf(pdf_bytes: bytes, dpi: int = 150) -> tuple[list[str], list[str]]:
    """解析 PDF，返回 (每页文字列表, 每页 base64 PNG 列表)"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text: list[str] = []
    pages_b64: list[str] = []

    for page in doc:
        pages_text.append(page.get_text())
        pix = page.get_pixmap(dpi=dpi)
        png_bytes = pix.tobytes("png")
        b64 = base64.b64encode(png_bytes).decode("ascii")
        pages_b64.append(b64)

    doc.close()
    return pages_text, pages_b64


# ---------------------------------------------------------------------------
# LLM 调用 — Anthropic 原生格式
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 维度映射 — 用于动态构建 prompt
# ---------------------------------------------------------------------------

DIMENSION_LABELS = {
    "a1_page_target": "页面目标清晰度",
    "a2_user_scenario": "用户场景与情感意图",
    "a3_page_states": "完整页面与状态清单",
    "a4_design_direction": "设计方向与约束",
    "a5_content_certainty": "内容与配图确定性",
    "a6_flow_completeness": "流转关系完整性",
    "b1_structure": "结构完整性",
    "b2_goals": "目标与指标",
    "b3_logic": "逻辑一致性",
    "b4_edge_cases": "边界与异常",
    "b5_interaction": "交互细节",
    "b6_copywriting": "文案与多语言",
    "b7_scalability": "可扩展性",
}

ALL_DIM_KEYS = list(DIMENSION_LABELS.keys())


def build_system_prompt(enabled_dims: list[str] | None = None) -> str:
    """根据启用的维度构建 system prompt。全选时返回完整 prompt，否则追加维度过滤指令。"""
    if not enabled_dims or set(enabled_dims) >= set(ALL_DIM_KEYS):
        return SYSTEM_PROMPT

    designer_dims = [DIMENSION_LABELS[k] for k in enabled_dims if k.startswith("a")]
    tech_dims = [DIMENSION_LABELS[k] for k in enabled_dims if k.startswith("b")]

    filter_instruction = "\n\n## ⚠️ 本次审查范围\n用户已选择以下维度进行审查，请**只输出**这些维度的审查结果，跳过未选择的维度：\n"
    if designer_dims:
        filter_instruction += f"\n**设计师视角**：{'、'.join(designer_dims)}"
    if tech_dims:
        filter_instruction += f"\n**技术视角**：{'、'.join(tech_dims)}"
    if not designer_dims:
        filter_instruction += "\n\n设计师视角维度全部跳过，总览表中不需要设计师视角部分。"
    if not tech_dims:
        filter_instruction += "\n\n技术视角维度全部跳过，总览表中不需要技术视角部分。"

    return SYSTEM_PROMPT + filter_instruction


async def call_anthropic(api_key: str, full_text: str, pages_b64: list[str], model: str, base_url: str | None = None, system_prompt: str = ""):
    """调用 Anthropic Claude API（原生格式），流式返回"""
    import anthropic

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = anthropic.AsyncAnthropic(**kwargs)

    content = []
    content.append({
        "type": "text",
        "text": f"以下是需求文档的完整文字内容（共 {len(pages_b64)} 页）：\n\n{full_text}",
    })
    for i, b64 in enumerate(pages_b64):
        content.append({"type": "text", "text": f"\n--- 第 {i + 1} 页截图 ---"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64},
        })
    content.append({
        "type": "text",
        "text": "\n请按照审查框架，对以上设计单进行深度审查，输出结构化审查报告。",
    })

    async with client.messages.stream(
        model=model, max_tokens=16000, system=system_prompt or SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


# ---------------------------------------------------------------------------
# LLM 调用 — OpenAI 兼容格式（OpenAI / OpenRouter / 中转服务）
# ---------------------------------------------------------------------------

async def call_openai_compat(api_key: str, full_text: str, pages_b64: list[str], model: str, base_url: str | None = None, system_prompt: str = ""):
    """调用 OpenAI 兼容 API（OpenAI / OpenRouter / 中转），流式返回"""
    from openai import AsyncOpenAI

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)

    content = []
    content.append({
        "type": "text",
        "text": f"以下是需求文档的完整文字内容（共 {len(pages_b64)} 页）：\n\n{full_text}",
    })
    for i, b64 in enumerate(pages_b64):
        content.append({"type": "text", "text": f"\n--- 第 {i + 1} 页截图 ---"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
        })
    content.append({
        "type": "text",
        "text": "\n请按照审查框架，对以上设计单进行深度审查，输出结构化审查报告。",
    })

    stream = await client.chat.completions.create(
        model=model, max_tokens=16000,
        messages=[
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# ---------------------------------------------------------------------------
# 审查 API — SSE 流式响应
# ---------------------------------------------------------------------------

@app.post("/api/review")
async def review(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    provider: str = Form("openrouter"),
    model: str = Form(""),
    base_url: str = Form(""),
    dimensions: str = Form(""),
):
    pdf_bytes = await file.read()

    cfg = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["openrouter"])
    use_model = model or cfg["model"]
    use_base_url = base_url or cfg["base_url"]
    api_format = cfg["format"]

    # 解析启用的维度
    enabled_dims = None
    if dimensions:
        try:
            enabled_dims = json.loads(dimensions)
        except json.JSONDecodeError:
            pass

    system_prompt = build_system_prompt(enabled_dims)
    dim_count = len(enabled_dims) if enabled_dims else len(ALL_DIM_KEYS)

    print(f"[INFO] provider={provider}, model={use_model}, base_url={use_base_url}, dims={dim_count}/{len(ALL_DIM_KEYS)}, pdf_size={len(pdf_bytes)} bytes")

    async def generate():
        yield _sse({"type": "progress", "step": 1, "message": "正在解析 PDF 文档..."})
        await asyncio.sleep(0.05)

        try:
            pages_text, pages_b64 = process_pdf(pdf_bytes)
        except Exception as e:
            yield _sse({"type": "error", "message": f"PDF 解析失败：{e}"})
            return

        total_pages = len(pages_text)
        yield _sse({"type": "progress", "step": 1, "message": f"PDF 解析完成，共 {total_pages} 页"})
        await asyncio.sleep(0.05)

        dim_label = f"（{dim_count} 个维度）" if dim_count < len(ALL_DIM_KEYS) else ""
        yield _sse({"type": "progress", "step": 2, "message": f"正在使用 {use_model} 审查{dim_label}..."})
        await asyncio.sleep(0.05)

        full_text = "\n\n".join(
            f"=== 第 {i + 1} 页 ===\n{t}" for i, t in enumerate(pages_text) if t.strip()
        )

        try:
            if api_format == "anthropic":
                streamer = call_anthropic(api_key, full_text, pages_b64, use_model, use_base_url, system_prompt)
            else:
                streamer = call_openai_compat(api_key, full_text, pages_b64, use_model, use_base_url, system_prompt)

            async for chunk in streamer:
                yield _sse({"type": "content", "text": chunk})

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] {type(e).__name__}: {error_msg}")
            if "401" in error_msg or "authentication" in error_msg.lower():
                yield _sse({"type": "error", "message": f"API Key 认证失败，请检查 Key 是否正确。\n\n原始错误：{error_msg[:200]}"})
            elif "404" in error_msg or "not_found" in error_msg.lower():
                yield _sse({"type": "error", "message": f"模型不可用，请检查模型名称。\n\n原始错误：{error_msg[:200]}"})
            elif "rate" in error_msg.lower() or "429" in error_msg:
                yield _sse({"type": "error", "message": "请求频率过高，请稍后重试"})
            else:
                yield _sse({"type": "error", "message": f"审查出错：{error_msg[:300]}"})
            return

        yield _sse({"type": "done"})

    return StreamingResponse(generate(), media_type="text/event-stream")


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
