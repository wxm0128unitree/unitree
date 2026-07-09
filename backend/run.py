# -*- coding: utf-8 -*-
"""
后端启动脚本
用法：python run.py
"""
import uvicorn
import os
import sys

# 设置控制台输出为 UTF-8 (Windows 兼容)
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

if __name__ == "__main__":
    # host=0.0.0.0 允许局域网和外网访问
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )