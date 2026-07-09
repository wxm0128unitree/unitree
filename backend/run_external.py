# -*- coding: utf-8 -*-
"""
外网访问启动脚本
1. 监听所有网卡（0.0.0.0）
2. 显示本机所有可访问的 IP 地址，方便手机/同事访问
"""
import socket
import sys
import os

# Windows 默认 GBK 编码，强制改为 UTF-8 以支持中文/emoji
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
    os.environ["PYTHONIOENCODING"] = "utf-8"

import uvicorn  # noqa: E402


def get_local_ips():
    """获取本机所有 IP 地址"""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip not in ips and not ip.startswith('127.') and ':' not in ip:
                ips.append(ip)
    except Exception:
        pass
    return ips


def print_banner(port):
    print("=" * 60)
    print("[Robot] YuShu Robot Inventory - Service Started")
    print("=" * 60)
    print(f"\nLocal:      http://localhost:{port}")
    print(f"127.0.0.1:  http://127.0.0.1:{port}")

    ips = get_local_ips()
    if ips:
        print("\n[LAN] Same-network / mobile devices can access:")
        for ip in ips:
            print(f"  -> http://{ip}:{port}")

    print("\n[WAN] External access options:")
    print("  1) cpolar (free, recommended): https://www.cpolar.com")
    print("     Run: cpolar http 8000")
    print("  2) Cloudflare Tunnel: cloudflared tunnel --url http://localhost:8000")
    print("  3) Deploy to cloud server (Aliyun/Tencent)")
    print(f"\n[Docs] API documentation: http://localhost:{port}/docs")
    print("=" * 60)
    print("Press Ctrl+C to stop the service\n")


if __name__ == "__main__":
    port = 8000
    print_banner(port)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )