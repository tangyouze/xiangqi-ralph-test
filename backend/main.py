"""
Xiangqi Server Entry Point

启动 FastAPI 服务器
"""

import uvicorn

from xiangqi.api import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
