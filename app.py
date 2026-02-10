"""
PRD Reviewer - 应用入口
从 api/index.py 导入 FastAPI app，添加静态文件服务
用于本地开发和 Railway 等平台部署
"""

import os
from pathlib import Path

from api.index import app  # noqa: F401 — re-export for uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PUBLIC_DIR = Path(__file__).parent / "public"


@app.get("/")
async def serve_index():
    return FileResponse(str(PUBLIC_DIR / "index.html"))


# 挂载静态文件目录（favicon 等）
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"\n  🔍 PRD Reviewer 已启动")
    print(f"  📎 打开浏览器访问: http://localhost:{port}\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
