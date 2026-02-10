"""
PRD Reviewer - 本地开发服务器
从 api/index.py 导入 FastAPI app，添加静态文件服务
"""

from pathlib import Path

from api.index import app  # noqa: F401 — re-export for uvicorn
from fastapi.responses import FileResponse

PUBLIC_DIR = Path(__file__).parent / "public"


@app.get("/")
async def serve_index():
    return FileResponse(str(PUBLIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn

    print("\n  🔍 PRD Reviewer 已启动（本地开发模式）")
    print("  📎 打开浏览器访问: http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
