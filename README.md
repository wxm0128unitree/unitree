# 🤖 宇树机器人出入库管理系统

> 基于 FastAPI + React 的设备库存与操作日志管理系统  
> 支持多用户、注册、权限管理、审计追踪

## ✨ 功能

- 📦 **设备管理**：新增/编辑/删除设备，状态切换（借出/归还/维修中）
- 👤 **用户体系**：注册、登录、JWT 鉴权、操作人=真实姓名
- 📋 **审计日志**：所有写操作自动记录「谁 + 何时 + 做什么」
- 🔍 **多维筛选**：型号、状态、持有人、关键词搜索

---

## 🚀 部署方案对比

| 方案 | 成本 | 难度 | 适合 |
|---|---|---|---|
| **☁️ [免费云平台](#-免费云平台部署推荐无需服务器)** | 0 | ⭐ | < 30 人小团队（**推荐先试**） |
| **🐳 [阿里云 ECS](#-5-分钟上手阿里云-ecs-部署)** | ¥60+/月 | ⭐⭐⭐ | > 30 人、需 24h 在线 |
| **💻 [本地模式](#-本地开发模式)** | 0 | ⭐ | 自己电脑用 |

---

## 🚀 5 分钟上手（推荐：阿里云 ECS 部署）

### 1. 准备服务器

- **阿里云 ECS**（轻量应用服务器 / ECS），最低配置：1核 2GB（10-30 人）
- 系统：**Ubuntu 22.04 LTS** 或 **Debian 12**
- 安全组：放通 `22`、`80`、`443` 端口

### 2. 域名 + 备案

- 注册一个域名（如 `robot.your-domain.cn`）
- **中国大陆服务必须备案**（用阿里云免费备案通道，7 天左右）
- 备案完成后，把域名解析到 ECS 公网 IP

### 3. 一键部署

SSH 上服务器后执行：

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | bash

# 2. 上传代码（git clone 或 scp 都行）
git clone <your-repo> /opt/robot && cd /opt/robot

# 3. 配置环境
cp .env.example .env
# ① 把 JWT_SECRET 改成随机字符串（用 python -c "import secrets; print(secrets.token_urlsafe(64))" 生成）
# ② 修改 Caddyfile 里的 robot.your-domain.cn 为你的真实域名
# ③ 修改 Caddyfile 里的 email 字段为你能收邮件的邮箱

# 4. 启动
docker compose up -d

# 5. 查看日志
docker compose logs -f
```

### 4. 验证

浏览器打开 `https://robot.your-domain.cn`

- **默认管理员**（首次启动自动创建，可在 `.env` 修改）：
  - 姓名：王曦明
  - 账号：13083401281
  - 密码：111111
- 任何人都可以点登录页底部的「立即注册」自助开账号

---

---

## ☁️ 免费云平台部署（推荐！无需服务器）

**完全免费，无 Docker，无备案，15 分钟上线。**

| 服务 | 作用 | 免费额度 |
|---|---|---|
| **Turso** | 托管 SQLite 数据库 | 9GB 存储、5 亿读/月 |
| **Render** | 跑后端 FastAPI | 750 小时/月、永久 URL |
| **Vercel** | 跑前端 + 全球 CDN | 100 GB 带宽/月 |

部署后任何人打开 `https://xxx.vercel.app` 就能用，手机/电脑都能访问。

### 步骤 1：建 Turso 数据库（5 分钟）

1. 打开 https://turso.tech → 用 GitHub 登录
2. 点击 **Create Database** → 名字 `robot-inventory` → 区域选 **Hong Kong**（国内快）
3. 数据库建好后，复制 **Database URL**（类似 `libsql://robot-inventory-xxx.turso.io`）
4. 点击 **Create Token** → 权限选 **Read & Write** → 复制 token（一串随机字符）
5. 把这两条保存好，部署 Render 时要用

### 步骤 2：部署后端到 Render（5 分钟）

1. 把整个项目推到你的 GitHub（**私有仓库**即可）：
   ```bash
   cd 出入库管理系统
   git init
   git add .
   git commit -m "deploy"
   gh repo create --private   # 或手动在 GitHub 网站创建
   git push -u origin main
   ```

2. 打开 https://dashboard.render.com → **New +** → **Blueprint**
3. 连你的 GitHub 仓库，Render 会自动识别 `render.yaml`
4. 在环境变量里填：
   - `JWT_SECRET`：粘贴生成的随机字符串（`python -c "import secrets; print(secrets.token_urlsafe(64))"`）
   - `DATABASE_URL`：粘贴 Turso 的 libsql URL
   - `DATABASE_AUTH_TOKEN`：粘贴 Turso 的 token
5. 点 **Apply** → 等 3-5 分钟部署完成
6. 部署成功后 Render 会给一个 URL：`https://robot-inventory-api.onrender.com`

7. 浏览器打开 `https://robot-inventory-api.onrender.com/api/health` 看到 `{"status": "ok"}` 就成功了

### 步骤 3：部署前端到 Vercel（5 分钟）

1. 打开 https://vercel.com → **Add New Project** → 选你的 GitHub 仓库
2. 配置：
   - **Root Directory**：`frontend`
   - **Build Command**：`npm run build`
   - **Output Directory**：`dist`
3. 在 **Environment Variables** 加一条：
   - `VITE_API_BASE`：`https://robot-inventory-api.onrender.com`
4. 点 **Deploy** → 等 1-2 分钟
5. 得到 URL：`https://robot-inventory-xxx.vercel.app`

6. 浏览器打开 → 应该看到登录页

### 步骤 4：回填 CORS 域名

后端要允许前端的域名才能跨域访问。回到 Render 控制台，修改环境变量：
- `CORS_ORIGINS`：`https://robot-inventory-xxx.vercel.app`
- 点保存 → Render 自动重启（约 30 秒）

完成！🎉

### 默认管理员账号

首次启动会自动创建（`.env` 中可改）：

| 字段 | 值 |
|---|---|
| 姓名 | 王曦明 |
| 账号 | 13083401281 |
| 密码 | 111111 |

⚠️ **上线后立刻登录改密码**！或重新部署时改 `ADMIN_PASSWORD` 环境变量。

### 任何人自助注册

打开 `https://robot-inventory-xxx.vercel.app` → 点登录页底部「立即注册」→ 填姓名 + 手机号 + 密码 → 自动登录。

要关闭注册（手动开账户）：把 Render 的 `ALLOW_REGISTER` 改成 `0`。

---

## 🚀 5 分钟上手（阿里云 ECS 部署）

> 适用于中国大陆、要求 24h 在线、规模 > 50 人。

```bash
start.bat         # Windows 一键启动（自动 build 前端 + 启动后端）
```

第一次启动会自动：
1. `cd frontend && npm install && npm run build`
2. 创建 Python 虚拟环境并装依赖
3. 启动 FastAPI（reload 模式）
4. 浏览器打开 http://localhost:8000

---

## 🏭 生产模式（无 Docker）

适用：Win/Linux 单机、不想用容器。

```bash
cd backend
python run_prod.py
```

`run_prod.py` 自动：
- 生成 `JWT_SECRET` 随机串（首次启动后固定）
- 启动 4 worker uvicorn（适合 50 人并发）
- 监听 0.0.0.0:8000
- 健康检查 http://your-ip:8000/api/health

> 🔒 生产模式建议在前面套一层 Nginx 反代 + HTTPS。

---

## ⚙️ 部署后的常用维护命令

```bash
# 查看服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 重启后端（改代码 / 配置后）
docker compose restart backend

# 完全重建（清掉所有容器和数据卷）
docker compose down -v
docker compose up -d --build

# 备份数据库（重要）
# robot_data 卷挂的就是 SQLite 文件
# 找到路径：
docker volume inspect robot_data
# 假设路径是 /var/lib/docker/volumes/robot_data/_data
cp /var/lib/docker/volumes/robot_data/_data/robot_inventory.db \
   /backup/robot_$(date +%Y%m%d).db
```

---

## 🔧 配置参考

### `.env`

| 字段 | 必填 | 说明 |
|---|---|---|
| `JWT_SECRET` | ✅ 必填 | 关键密钥；用 `python -c "import secrets; print(secrets.token_urlsafe(64))"` 生成 |
| `ADMIN_NAME` | ❌ | 默认管理员姓名 |
| `ADMIN_PHONE` | ❌ | 默认管理员手机号（同时也是登录账号） |
| `ADMIN_PASSWORD` | ❌ | 默认管理员密码 |
| `ALLOW_REGISTER` | ❌ | 1=允许注册（默认），0=关闭 |
| `DB_PATH` | ❌ | SQLite 文件位置 |

### 如果数据库丢了 / 重置

```bash
# 停服后，删除 SQLite 文件
docker compose down
docker volume rm robot_robot_data
docker compose up -d
# 启动后会用 .env 里的 ADMIN_* 重新创建管理员
```

---

## 📁 项目结构

```
出入库管理系统/
├── Dockerfile                  # 多阶段构建（前端 build + 后端 serve）
├── docker-compose.yml          # 一键启动：Caddy + FastAPI
├── Caddyfile                   # 自动 HTTPS 反代配置
├── .env.example                # 环境变量模板
├── .gitignore
├── start.bat                   # Windows 本地开发启动器
│
├── backend/
│   ├── requirements.txt
│   ├── run_prod.py             # 生产模式启动器（无 Docker）
│   ├── run_external.py         # 开发模式启动器（reload）
│   └── app/
│       ├── main.py             # FastAPI 路由 + 启动时 bootstrap
│       ├── auth.py             # JWT + bcrypt
│       ├── database.py         # SQLAlchemy + 多进程 bootstrap 锁
│       ├── models.py           # Robot / OperationLog / User 三张表
│       ├── schemas.py          # Pydantic 校验
│       └── crud.py             # 业务逻辑
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx             # 登录 / 主界面路由
        ├── api/
        │   └── index.js        # 自动注入 Authorization / 401 跳登录
        ├── pages/
        │   ├── Login.jsx
        │   ├── Register.jsx
        │   ├── Dashboard.jsx
        │   └── Logs.jsx
        ├── components/
        │   ├── AddRobotModal.jsx
        │   ├── StatusModal.jsx
        │   ├── FilterSelect.jsx
        │   ├── RobotCard.jsx
        │   └── Toast.jsx
        └── styles/
            └── index.css
```

---

## 📜 API 一览

| 方法 | 路径 | 说明 | 鉴权 |
|---|---|---|---|
| GET | `/api/health` | 健康检查 | ❌ |
| GET | `/api/bootstrap` | 初始化状态（前端首次使用） | ❌ |
| POST | `/api/auth/register` | 注册 | ❌ |
| POST | `/api/auth/login` | 登录 | ❌ |
| GET | `/api/auth/me` | 当前用户 | ✅ |
| GET | `/api/robots` | 设备列表（支持 model/status/holder/keyword） | ❌ |
| POST | `/api/robots` | 新增设备 | ✅ |
| GET | `/api/robots/{id}` | 设备详情 | ❌ |
| POST | `/api/robots/{id}/status` | 修改状态 | ✅ |
| DELETE | `/api/robots/{id}` | 删除设备 | ✅ |
| GET | `/api/stats` | 统计 | ❌ |
| GET | `/api/logs` | 日志 | ❌ |
| GET | `/api/users` | 用户列表 | ✅ |

API 在线文档：`https://your-domain/docs`（Swagger UI）

---

## ⚖️ 注意事项

- **数据备份**：SQLite 文件务必定期备份（参考上方命令）
- **HTTPS 证书**：Caddy 自动签发 + 续期，但需要域名 DNS 正确解析且 80/443 端口可访问
- **JWT 密钥**：**.env 中的 `JWT_SECRET` 一旦更换，旧登录全部失效**
- **并发规模**：SQLite 适合 < 50 并发写。若超过请改 `DATABASE_URL` 为 MySQL/PostgreSQL

---

## 🎉 Done

如果部署中遇到问题，先看：
1. `docker compose logs backend` — 后端报错信息
2. `docker compose logs caddy` — 反代 / HTTPS 报错
3. 浏览器开发者工具 Network — API 响应
