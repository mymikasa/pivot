# 后端多环境配置系统设计

## 概述

将后端配置从单 `.env` 文件改为 `.env.dev` / `.env.test` / `.env.prod` 三套独立配置，通过 CLI 命令行参数 `--env` 切换环境。同时扩充配置项，支持服务器端口、CORS、日志级别等。

## 动机

当前配置系统存在以下问题：
- 只支持单套 `.env`，无法区分开发/测试/生产环境
- 配置项过少，缺少服务器、CORS、日志等常用配置
- docker-compose 中的密码、alembic.ini 中的数据库 URL、代码中的默认值分散管理

## 配置文件结构

三套独立的 `.env` 文件放在项目根目录，各自包含全部配置项：

### `.env.dev`（开发环境）

```
PIVOT_DATABASE_URL=mysql+pymysql://pivot:pivot_pass_2026@localhost:3306/pivot
PIVOT_JWT_SECRET_KEY=dev-secret-key
PIVOT_JWT_ALGORITHM=HS256
PIVOT_ACCESS_TOKEN_EXPIRE_MINUTES=15
PIVOT_REFRESH_TOKEN_EXPIRE_DAYS=7
PIVOT_SERVER_HOST=0.0.0.0
PIVOT_SERVER_PORT=8000
PIVOT_CORS_ORIGINS=["http://localhost:5173"]
PIVOT_LOG_LEVEL=DEBUG
PIVOT_DEBUG=true
```

### `.env.test`（测试环境）

```
PIVOT_DATABASE_URL=mysql+pymysql://pivot:pivot_pass_2026@localhost:3306/pivot_test
PIVOT_JWT_SECRET_KEY=test-secret-key
PIVOT_JWT_ALGORITHM=HS256
PIVOT_ACCESS_TOKEN_EXPIRE_MINUTES=15
PIVOT_REFRESH_TOKEN_EXPIRE_DAYS=7
PIVOT_SERVER_HOST=0.0.0.0
PIVOT_SERVER_PORT=8000
PIVOT_CORS_ORIGINS=["http://localhost:5173"]
PIVOT_LOG_LEVEL=WARNING
PIVOT_DEBUG=false
```

### `.env.prod`（生产环境）

```
PIVOT_DATABASE_URL=mysql+pymysql://pivot:CHANGE_ME@localhost:3306/pivot
PIVOT_JWT_SECRET_KEY=CHANGE_ME
PIVOT_JWT_ALGORITHM=HS256
PIVOT_ACCESS_TOKEN_EXPIRE_MINUTES=15
PIVOT_REFRESH_TOKEN_EXPIRE_DAYS=7
PIVOT_SERVER_HOST=0.0.0.0
PIVOT_SERVER_PORT=8000
PIVOT_CORS_ORIGINS=[]
PIVOT_LOG_LEVEL=WARNING
PIVOT_DEBUG=false
```

## 新增配置项

| 配置项 | 环境变量 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `server_host` | `PIVOT_SERVER_HOST` | `str` | `0.0.0.0` | 监听地址 |
| `server_port` | `PIVOT_SERVER_PORT` | `int` | `8000` | 监听端口 |
| `cors_origins` | `PIVOT_CORS_ORIGINS` | `list[str]` | `[]` | CORS 允许的来源列表（JSON 数组格式） |
| `log_level` | `PIVOT_LOG_LEVEL` | `str` | `INFO` | 日志级别 |
| `debug` | `PIVOT_DEBUG` | `bool` | `false` | 调试模式 |

## 架构

### CLI 入口 (`src/cli.py`)

使用 `argparse` 解析命令行参数，设置环境变量后启动 uvicorn：

```
uv run python -m src.cli --env dev
uv run python -m src.cli --env test
uv run python -m src.cli --env prod
```

流程：
1. `argparse` 解析 `--env` 参数（默认 `dev`）
2. 校验 `--env` 值必须是 `dev` / `test` / `prod`
3. 检查对应 `.env.xxx` 文件是否存在
4. 将文件绝对路径设置到环境变量 `PIVOT_ENV_FILE`
5. 导入 Settings 并启动 uvicorn（使用 `settings.server_host` 和 `settings.server_port`）

### Settings 改造 (`src/core/config.py`)

- `model_config.env_file` 改为从环境变量 `PIVOT_ENV_FILE` 读取，fallback 到 `.env.dev`
- 新增 `server_host`、`server_port`、`cors_origins`、`log_level`、`debug` 字段
- 添加 pydantic validator 校验

### 应用启动 (`src/main.py`)

- 根据 `settings.log_level` 配置 logging
- 添加 `CORSMiddleware`，使用 `settings.cors_origins`
- 保留现有 router 注册

## 校验规则

### CLI 层校验

- `--env` 只接受 `dev` / `test` / `prod`，其他值报错退出
- `.env.xxx` 文件不存在时报错退出，提示文件路径

### Settings 层校验（pydantic validator）

- `log_level` 必须是 `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` 之一
- `server_port` 范围 1-65535
- `database_url` 必须以 `mysql+pymysql://` 或 `sqlite:///` 开头
- `jwt_secret_key` 在生产环境不能是默认的 `change-me-in-production` 或 `CHANGE_ME`

### 启动失败行为

- 配置校验失败：打印清晰错误信息，退出码 1
- `.env` 文件存在但某字段缺失：使用代码中的默认值，不报错

## .gitignore 变更

```
# 之前
*.env
.env.*

# 之后
.env.dev
.env.prod
```

`.env.test` 提交到仓库，方便 CI 和开发者使用。`.env.dev` 和 `.env.prod` 包含敏感信息，不提交。

## 变更范围

### 新增文件

- `src/cli.py` — CLI 启动入口
- `.env.dev` — 开发环境配置
- `.env.test` — 测试环境配置
- `.env.prod` — 生产环境配置

### 修改文件

- `src/core/config.py` — 扩展配置项 + 动态 env_file + validators
- `src/main.py` — 添加 CORS middleware + logging 配置
- `.gitignore` — 调整忽略规则
- `Makefile` — 更新启动命令

### 不变文件

- `src/core/security.py` — 通过 `settings.xxx` 引用，无需改动
- `src/core/database.py` — 通过 `settings.database_url` 引用，无需改动
- `tests/` — 继续用 SQLite 内存库，不受影响
- `docker-compose.yml` — 不变

## 测试

- 现有 18 个后端测试不受影响（SQLite 内存库不依赖 .env）
- 新增配置相关的测试：验证 Settings 校验规则（无效 port、无效 log_level、无效 database_url 等）
