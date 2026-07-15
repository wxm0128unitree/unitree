# 部门设备与配件管理中心

面向部门内部 3–5 人使用的轻量资产管理系统，用于管理机器人、实训台及配件库存。

- 线上地址：[unitree-backend-2wel.onrender.com](https://unitree-backend-2wel.onrender.com/)
- API 文档：[unitree-backend-2wel.onrender.com/docs](https://unitree-backend-2wel.onrender.com/docs)

## 当前功能

- **机器人逐台管理**：按 G1、R1、Go2、A2 等型号统计，记录资产编号、位置、负责人和状态。
- **实训台独立管理**：统一使用“实训台”分类，不再区分人形或四足标签。
- **配件数量管理**：统计 Pico、夹爪、三指灵巧手、电池、遥控器和拓展坞的库存总量，通过入库、借出、归还、维修等操作增减数量。
- **设备流转**：支持在库、借出、维修、盘点、归档/恢复；迁移表示设备转出本部门，迁移后不计入当前设备统计。
- **查询与导出**：支持筛选、搜索、操作日志及设备/日志 CSV 导出。
- **用户与权限**：支持登录、注册、普通用户和管理员；管理员可管理用户、迁移设备、归档/恢复以及备份/恢复数据。
- **数据备份**：支持手动备份、下载和恢复；恢复前会额外生成安全备份。

## 技术栈

- 后端：FastAPI、SQLAlchemy、Pydantic、JWT
- 前端：React、Vite
- 数据库：本地默认 SQLite，线上使用 PostgreSQL；同时兼容 libSQL/Turso
- 部署：Render

## 本地运行

环境要求：Python 3.12、Node.js 22（推荐使用当前 LTS 版本）。

1. 在当前 PowerShell 会话设置本地密钥：

```powershell
$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(64))"
```

如需自定义首次创建的管理员，可在启动前继续设置 `ADMIN_NAME`、`ADMIN_PHONE` 和 `ADMIN_PASSWORD`。已有数据库不会重复创建管理员。

2. 一键构建并启动：

```powershell
.\start.ps1
```

启动后访问：

- 系统首页：<http://localhost:8000>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/health>

前后端分开调试时运行：

```powershell
.\dev_start.ps1
```

开发模式前端地址为 <http://localhost:5173>，后端地址为 <http://localhost:8000>。

## 环境变量

| 变量 | 用途 | 说明 |
| --- | --- | --- |
| `JWT_SECRET` | JWT 签名密钥 | 生产环境必须设置为随机长字符串 |
| `ADMIN_NAME` | 初始管理员姓名 | 仅数据库无用户时自动创建 |
| `ADMIN_PHONE` | 初始管理员手机号 | 仅首次初始化使用 |
| `ADMIN_PASSWORD` | 初始管理员密码 | 生产环境必须修改默认值 |
| `ALLOW_REGISTER` | 是否开放注册 | `1` 开放，`0` 关闭；当前部署保持开放 |
| `DB_PATH` | SQLite 文件路径 | 仅本地 SQLite 模式使用 |
| `DATABASE_URL` | 线上数据库连接 | 设置后优先于 `DB_PATH` |
| `DATABASE_AUTH_TOKEN` | libSQL/Turso 凭证 | 仅使用 libSQL/Turso 时需要 |
| `CORS_ORIGINS` | 允许访问 API 的前端来源 | 多个地址用英文逗号分隔 |
| `BACKUP_ROOT` | 备份目录 | 应使用持久化目录 |

Docker 部署的完整示例见 [`.env.example`](./.env.example)；Render 环境变量应在控制台配置。不要提交 `.env`、数据库文件、备份文件或密钥。

## 测试与构建

后端测试：

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -q
```

前端生产构建：

```powershell
npm run build --prefix frontend
```

## Render 部署

当前生产环境连接 GitHub，推送 `main` 分支后由 Render 自动部署。重新创建服务时可参考 [`render.yaml`](./render.yaml)，并在 Render 控制台配置生产密钥和数据库连接。

部署后至少检查：

1. `/api/health` 返回 `{"status":"ok"}`。
2. 登录、设备总览、实训台和数量库存数据正常。
3. 新增、借出、归还、迁移和盘点操作均写入日志。
4. 管理员可以创建并下载备份。

## 数据安全

- 升级或批量调整数据前，先在“备份恢复”页面创建并下载备份。
- Render 临时磁盘上的文件可能随重建丢失；数据库和备份目录必须使用持久化存储，重要备份应下载到本地。
- 归档和迁移不会删除历史记录；不要直接修改生产数据库。
- 数据库初始化和字段补齐采用可重复执行的增量逻辑，但生产更新后仍需核对统计和操作日志。

## 项目结构

```text
unitree/
├── backend/
│   ├── app/              # API、数据模型、业务逻辑和备份逻辑
│   ├── tests/            # 后端自动化测试
│   ├── run_external.py   # 本地/局域网启动
│   └── run_prod.py       # 生产启动
├── frontend/
│   ├── src/              # React 前端源码
│   └── dist/             # 生产构建产物
├── start.ps1             # 一键构建并启动
├── dev_start.ps1         # 前后端开发模式
├── render.yaml           # Render Blueprint 配置
└── CHANGELOG.md          # 版本更新记录
```

版本变化和数据库兼容说明见 [`CHANGELOG.md`](./CHANGELOG.md)。
