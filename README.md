# Unitree 部门设备与配件管理中心

面向部门内部仓库与资产管理员的轻量管理系统。系统统一管理机器人、实训台、电池、遥控器及其他配件，围绕“当前状态、实际持有人、操作记录”组织业务，降低口头登记和表格分散带来的遗漏。

- 生产环境：<https://unitree-backend-2wel.onrender.com/>
- API 文档：<https://unitree-backend-2wel.onrender.com/docs>
- 健康检查：<https://unitree-backend-2wel.onrender.com/api/health>

## 当前版本能力

### 设备与实训台

- 按资产编号、型号、负责人、持有人、位置和状态统一管理。
- 支持负责人、持有人、状态、型号、资产编号和去向组合查询。
- 支持盘点、资料修改、部门调出、归档和恢复。
- 当前借用人、借用用途和预计归还时间直接来自现有操作记录，不增加数据库字段。
- 已调出或归档设备可单独筛选，不计入部门当前资产统计。

### 状态流转

界面只展示当前状态允许执行的下一步操作：

```text
在库 ──借出──> 借出
 │              ├──归还──> 在库
 └──送修──> 维修中 ──修复入库──> 在库
借出 ──转交──> 借出（更新实际持有人）
借出 ──送修──> 维修中
```

- 在库：只能办理借出或送修。
- 借出：只能归还、转交或送修。
- 维修中：只能修复入库。
- 重复提交相同状态不会产生无意义日志。
- 只有在库资产可以归档或调出部门。

### 配件库存

- 电池、遥控器等可逐件编号管理，也支持数量库存。
- 单件配件使用借出、归还、维修、修复等正式流转操作。
- 数量操作保留拆分后子项的完整流水。
- 归还兼容的未编号库存时自动合并数量。
- “作废”采用软处理并保留流水，不永久删除历史数据。

### 日志、查询与导出

- 设备日志和配件流水分区展示。
- 支持操作类型、操作人、时间、关键词和设备编号过滤。
- 支持分页查看，避免一次加载全部历史记录。
- 设备、设备日志和配件流水均可导出 CSV。
- 可通过资产编号查看单台设备的完整追溯记录。

### 用户与数据安全

- JWT 登录认证，区分管理员与普通用户。
- 管理员可管理用户、执行调出/归档及备份恢复。
- 普通用户按负责人范围查看和维护资产。
- 支持创建、下载和恢复备份；恢复前会生成安全备份。
- 本轮业务优化未引入数据库结构迁移，现有生产数据保持兼容。

## 界面与品牌资源

- Unitree Logo：`frontend/public/assets/unitree-logo.png`
- 机器狗全站背景：`frontend/public/assets/unitree-hero.webp`（由原始 PNG 优化生成）
- 登录、注册和管理界面通过真实图片元素加载背景，并叠加独立遮罩保证文字可读。
- 页面针对桌面和移动端做了响应式适配。

## 技术架构

- 前端：React 18、Vite 8
- 后端：FastAPI、SQLAlchemy、Pydantic、JWT
- 数据库：本地默认 SQLite；生产支持 PostgreSQL；兼容 libSQL/Turso
- 部署：Render Web Service
- 测试：Pytest

生产模式由 FastAPI 同时提供 API 与 `frontend/dist` 静态资源。Render 服务以 `backend/run_prod.py` 启动，推送 `main` 后自动部署。

## 项目结构

```text
unitree/
├── backend/
│   ├── app/               # API、状态机、模型、认证与备份
│   ├── tests/             # 后端自动化测试
│   ├── requirements.txt
│   └── run_prod.py        # 生产启动入口
├── frontend/
│   ├── public/assets/     # Logo 与机器狗背景
│   ├── src/               # React 源码
│   ├── dist/              # 生产构建产物
│   └── package.json
├── render.yaml            # Render Blueprint
├── start.ps1              # Windows 一键构建并启动
├── dev_start.ps1          # 前后端开发模式
├── docker-compose.yml
└── CHANGELOG.md
```

## 本地运行

环境建议：Python 3.12、Node.js 22。

在 PowerShell 中配置首次启动信息：

```powershell
$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(64))"
$env:ADMIN_NAME = "管理员"
$env:ADMIN_PHONE = "你的手机号"
$env:ADMIN_PASSWORD = "请使用强密码"
.\start.ps1
```

访问 <http://localhost:8000>。已有数据库不会重复创建管理员。

前后端分开调试：

```powershell
.\dev_start.ps1
```

- 前端：<http://localhost:5173>
- 后端：<http://localhost:8000>
- API 文档：<http://localhost:8000/docs>

## 环境变量

- `JWT_SECRET`：JWT 签名密钥，生产环境必须使用随机长字符串。
- `ADMIN_NAME`、`ADMIN_PHONE`、`ADMIN_PASSWORD`：空数据库首次启动时创建管理员。
- `ALLOW_REGISTER`：`1` 开放注册，`0` 关闭注册。
- `DATABASE_URL`：生产数据库连接，设置后优先于本地 SQLite。
- `DB_PATH`：本地 SQLite 文件位置。
- `DATABASE_AUTH_TOKEN`：使用 libSQL/Turso 时的认证令牌。
- `CORS_ORIGINS`：允许访问 API 的前端来源，多个地址用英文逗号分隔。
- `BACKUP_ROOT`：备份文件目录，生产环境应指向持久化存储。
- `FRONTEND_DIST`：生产前端构建目录，默认是 `frontend/dist`。
- `WORKERS`：Uvicorn 工作进程数。

不要提交 `.env`、JWT 密钥、数据库文件、用户密码或生产备份。

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

构建后应确认 `frontend/dist/index.html` 引用的 JS/CSS 文件真实存在。

## Render 部署

仓库根目录包含 `render.yaml`。现有生产服务连接 GitHub `main` 分支，并由 Render 自动部署。

发布后的检查顺序：

1. `/api/health` 返回 `status: ok`。
2. 首页加载新的带哈希 JS/CSS 文件。
3. `/assets/unitree-logo.png` 与 `/assets/unitree-hero.webp` 返回成功。
4. 登录页能看到机器狗背景和 Unitree Logo。
5. 登录后核对统计数据、筛选、状态操作与日志。

Render 免费实例休眠后，首次访问可能需要几十秒完成唤醒。

## 运维与数据保护

- 更新生产环境前，先在“备份恢复”页面创建并下载备份。
- 不要直接编辑生产数据库或手工删除资产记录。
- 作废、归档和调出都会保留历史，优先使用系统提供的业务操作。
- Render 临时磁盘可能在重建后清空；数据库和备份必须使用持久化存储。
- 部署后若页面仍显示旧版，应先核对 HTML 引用的资源哈希，再判断是否为浏览器缓存。

## 版本说明

详细历史见 [`CHANGELOG.md`](./CHANGELOG.md)。本 README 以当前状态机、库存流水、日志分页、CSV 导出、品牌界面和 Render 部署方式为准。
