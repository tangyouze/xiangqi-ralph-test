"""
揭棋服务器入口

启动揭棋 API 服务器
"""

import uvicorn

from jieqi.api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
