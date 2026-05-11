# 注册功能设计

## 概述

为 Pivot 平台新增用户自助注册功能。用户通过填写用户名、邮箱、密码完成注册，注册后自动成为普通用户角色，需跳转登录页手动登录。

## 1. 后端 API

### 接口

`POST /api/auth/register`（公开，无需认证）

### 请求体

```json
{
  "username": "string (3-64字符)",
  "email": "string (有效邮箱)",
  "password": "string (最少8位，含字母和数字)",
  "confirm_password": "string (必须和 password 一致)"
}
```

### 成功响应（200）

```json
{
  "message": "注册成功"
}
```

### 校验规则

- `username`：3-64 字符，唯一
- `email`：有效邮箱格式，唯一
- `password`：最少 8 位，必须包含字母和数字
- `confirm_password`：必须和 `password` 一致

### 实现细节

- `schemas/auth.py` 新增 `RegisterRequest`，包含 pydantic validator 校验密码强度和两次密码一致性
- `routers/auth.py` 新增 `register` 函数，密码通过 `get_password_hash` 哈希后存储
- `role_id` 查询 `user` 角色自动填入，`is_active` 默认 `true`
- 不返回 Token，注册成功只返回消息

## 2. 前端

### 新增文件

- `frontend/src/routes/auth/register.tsx` — 注册页
- `frontend/src/components/auth/register-form.tsx` — 注册表单组件

### 修改文件

- `frontend/src/data/auth.ts` — 新增 `useRegisterMutation`
- `frontend/src/routes/auth/login.tsx` — 添加"去注册"链接

### 注册页布局

复用登录页的左右分栏布局（左侧品牌区 + 右侧表单区）：
- 表单标题："创建账号"
- 副标题："填写信息注册新账号"
- 表单底部："已有账号？去登录"链接，指向 `/auth/login`

### 登录页改动

在登录表单底部添加"没有账号？去注册"链接，指向 `/auth/register`。

### 注册表单

四个字段：用户名、邮箱、密码、确认密码。
- 密码字段带显示/隐藏切换（复用登录表单样式）
- 提交按钮："注 册"，loading 状态："正在注册..."
- Zod 校验：用户名 3-64 字符、邮箱格式、密码 8 位含字母和数字、确认密码一致
- 成功后跳转 `/auth/login`

### 数据层

`useRegisterMutation`：调用 `POST /auth/register`，成功后 navigate 到登录页。

## 3. 错误码

### 注册接口错误码

| HTTP 状态码 | detail | 触发场景 |
|---|---|---|
| 409 | 用户名已存在 | username 已被注册 |
| 409 | 邮箱已存在 | email 已被注册 |
| 422 | 两次密码不一致 | password ≠ confirm_password |
| 422 | 密码至少8位，需包含字母和数字 | 密码强度不足 |
| 422 | (FastAPI 自动校验) | 请求参数格式错误 |

### 完整后端错误码文档

| HTTP 状态码 | detail | 触发场景 |
|---|---|---|
| 401 | 用户名或密码错误 | 登录凭证不匹配 |
| 401 | 用户已被禁用 | 登录用户 is_active=false |
| 401 | 无效的刷新凭证 | refresh token 解码失败或类型不对 |
| 401 | 刷新凭证已失效 | refresh token 不在数据库中 |
| 401 | 用户不存在或已被禁用 | refresh 时用户状态异常 |
| 401 | 原密码错误 | 修改密码时旧密码不对 |
| 401 | 无效的认证凭证 | access token 无效/过期（中间件） |
| 403 | 权限不足 | 非 admin 访问 admin 接口 |
| 404 | 用户不存在 | 操作目标用户不存在 |
| 409 | 用户名已存在 | 注册/创建用户时用户名重复 |
| 409 | 邮箱已存在 | 注册/创建用户时邮箱重复 |
| 422 | 两次密码不一致 | 注册时 password ≠ confirm_password |
| 422 | 密码至少8位，需包含字母和数字 | 注册时密码强度不足 |
| 422 | (FastAPI 自动校验) | 请求参数格式错误 |
| 429 | 请求过于频繁，请稍后再试 | 登录限流 |

## 4. 变更范围

### 新增文件

- `frontend/src/routes/auth/register.tsx`
- `frontend/src/components/auth/register-form.tsx`

### 修改文件

- `src/schemas/auth.py` — 新增 `RegisterRequest`
- `src/routers/auth.py` — 新增 `register` 路由
- `frontend/src/data/auth.ts` — 新增 `useRegisterMutation`
- `frontend/src/routes/auth/login.tsx` — 添加"去注册"链接
- `frontend/src/routeTree.gen.ts` — 自动重新生成

### 不变文件

- `src/models/user.py` — 模型不变
- `src/core/security.py` — 复用 `get_password_hash`
- `src/seed.py` — seed 不变

## 5. 测试

### 后端新增测试

- 正常注册 → 200，数据库中能查到用户
- 用户名已存在 → 409
- 邮箱已存在 → 409
- 两次密码不一致 → 422
- 密码强度不足（纯数字/过短） → 422
- 注册的用户角色为 user，is_active 为 true
