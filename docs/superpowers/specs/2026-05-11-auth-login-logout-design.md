# 登录登出功能设计

## 概述

为 Pivot 平台实现管理员和普通用户的登录登出功能。采用双 Token（Access Token + Refresh Token）机制 + RBAC 权限模型，后端 FastAPI + MySQL，前端 React + TanStack 全家桶。

## 1. 整体架构

```
┌───────────────┐         ┌──────────────────────┐        ┌─────────┐
│  React 前端   │ ──HTTP──▶│   FastAPI 后端        │ ──SQL──▶│  MySQL  │
│  (frontend/)  │◀─JSON── │   (src/)              │        │         │
└───────────────┘         │                      │        └─────────┘
                          │  auth/  认证模块       │
                          │  users/ 用户模块       │
                          │  core/  公共配置       │
                          └──────────────────────┘
```

**后端模块划分（`src/`）：**

| 路径 | 职责 |
|------|------|
| `src/core/` | 配置、数据库连接、安全工具（JWT 生成/验证、密码哈希） |
| `src/users/` | 用户 CRUD、角色模型（User / Role） |
| `src/auth/` | 登录、登出、Token 刷新接口 |

**数据流：**

1. 用户提交账号密码 → 后端验证 → 返回 Access Token + Refresh Token
2. 前端存储 Token → 每次请求携带 Access Token
3. Access Token 过期 → 前端自动用 Refresh Token 换新 → 用户无感
4. 登出 → 前端清 Token + 后端删除 Refresh Token 记录

## 2. 数据模型

**roles 表：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT, 自增主键 | 角色 ID |
| name | VARCHAR(32), UNIQUE | 角色名（admin / user） |
| description | VARCHAR(255) | 角色描述 |

**users 表：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT, 自增主键 | 用户 ID |
| username | VARCHAR(64), UNIQUE | 用户名 |
| email | VARCHAR(255), UNIQUE | 邮箱 |
| hashed_password | VARCHAR(255) | bcrypt 哈希后的密码 |
| role_id | INT, 外键 → roles.id | 用户角色 |
| is_active | BOOLEAN, 默认 true | 是否启用 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**refresh_tokens 表：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT, 自增主键 | Token 记录 ID |
| token | VARCHAR(512), UNIQUE | Refresh Token 值 |
| user_id | INT, 外键 → users.id | 所属用户 |
| expires_at | DATETIME | 过期时间 |
| created_at | DATETIME | 创建时间 |

**初始数据：** 系统启动时自动 seed 两个角色：`admin` 和 `user`。

## 3. API 接口设计

### 认证接口（`/api/auth/`）

| 路径 | 方法 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| `/api/auth/login` | POST | 登录 | `{username, password}` | `{access_token, refresh_token, token_type, user}` |
| `/api/auth/logout` | POST | 登出 | Header: Authorization Bearer | `{message}` |
| `/api/auth/refresh` | POST | 刷新 Token | `{refresh_token}` | `{access_token, refresh_token, token_type}` |

### 用户管理接口（`/api/users/`）

| 路径 | 方法 | 说明 | 请求体 / 参数 | 权限 |
|------|------|------|---------------|------|
| `/api/users/me` | GET | 获取当前用户信息 | 无 | 已登录 |
| `/api/users/change-password` | POST | 修改自己密码 | `{old_password, new_password}` | 已登录 |
| `/api/users/list` | GET | 用户列表（分页） | query: `page, page_size, keyword` | admin |
| `/api/users/create` | POST | 创建用户 | `{username, email, password, role_id}` | admin |
| `/api/users/update` | POST | 编辑用户 | `{id, username?, email?, role_id?, is_active?}` | admin |
| `/api/users/disable` | POST | 禁用用户（软删除） | `{id}` | admin |
| `/api/users/delete` | POST | 硬删除用户 | `{id}` | admin |

## 4. 前端设计

### 技术栈

- React 19 + TypeScript 5 + Vite 7
- TanStack Router（文件路由）+ TanStack Query + TanStack Form
- Zod 4 表单校验
- Tailwind CSS 4 + Radix UI
- `@hey-api/openapi-ts` 生成 API 客户端
- Vitest + MSW + Testing Library

### 目录结构（`frontend/src/`）

| 路径 | 职责 |
|------|------|
| `routes/auth/login.tsx` | 登录页（左右分栏布局） |
| `routes/_authenticated/` | 需认证的路由布局 |
| `routes/_authenticated/manage/users.tsx` | 用户管理页（admin） |
| `components/auth/` | 登录表单等认证相关组件 |
| `components/ui/` | 复用现有共享 UI 组件 |
| `data/auth.ts` | 认证相关 query options / mutations |
| `hooks/use-auth.ts` | 认证状态 Hook（封装 Token 管理） |
| `lib/api-generated/` | OpenAPI 生成的 API 客户端 |
| `lib/api-utils.ts` | `handleApiResponse` 等工具 |
| `stores/auth.ts` | 全局认证状态（Token 存储） |

### 路由

- `/auth/login` — 登录页（公开）
- `/` — 首页/仪表盘（需登录，`_authenticated` 布局）
- `/manage/users` — 用户管理页（仅 admin）

### 登录页布局

左右分栏式：左侧品牌展示区（渐变背景 + 品牌名称 + 描述），右侧登录表单。

### 认证流程

1. `stores/auth.ts` 管理 Access Token（内存）和 Refresh Token（localStorage）
2. Axios 拦截器：自动附加 Token、401 时静默刷新
3. TanStack Router 路由守卫：未登录重定向 `/auth/login`，非 admin 访问管理页返回 403
4. 登录/登出通过 `data/auth.ts` 的 mutation 封装，成功后 invalidate queries

### API 调用方式

后端 FastAPI 自动生成 OpenAPI spec（`/openapi.json`），前端执行 `npm run generate-api` 生成类型安全客户端，通过生成的客户端调用接口，响应走 `handleApiResponse`。

### 表单

- 登录表单使用 `useAppForm` + Zod schema 校验
- 遵循 `data-testid` 规范（如 `username-input`、`password-input`、`submit-button`）

## 5. 错误处理与安全策略

### 密码安全

- 使用 `bcrypt` 哈希存储，不存明文
- 密码强度要求：最少 8 位，包含字母和数字

### JWT 安全

- Access Token 有效期 15 分钟，Refresh Token 有效期 7 天
- Token 签名使用 HS256，密钥从环境变量 `JWT_SECRET_KEY` 读取
- 登出时删除数据库中对应的 Refresh Token 记录，实现 Token 吊销

### 接口安全

- 登录接口限流：同一 IP 每分钟最多 5 次尝试
- 所有需认证接口校验 Access Token 签名和过期时间
- Admin 接口额外校验 `role_id` 是否为 admin 角色
- 禁用用户（`is_active=false`）的 Token 即使未过期也拒绝访问，在认证中间件中检查

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 错误场景

| 场景 | 状态码 | detail |
|------|--------|--------|
| 用户名或密码错误 | 401 | 用户名或密码错误 |
| Token 过期 | 401 | Token 已过期 |
| Token 无效 | 401 | 无效的认证凭证 |
| 权限不足 | 403 | 权限不足 |
| 用户名已存在 | 409 | 用户名已存在 |
| 邮箱已存在 | 409 | 邮箱已存在 |
| 请求参数错误 | 422 | FastAPI 自动校验返回 |
| 登录限流 | 429 | 请求过于频繁，请稍后再试 |
