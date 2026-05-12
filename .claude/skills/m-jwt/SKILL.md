---
name: m-jwt
description: 用于在 Go gRPC 微服务中接入 JWT 鉴权 —— 签发与校验、claims 设计、gRPC interceptor、metadata 传递、refresh 流程、密钥与配置管理。技术栈：golang-jwt/jwt v5 + grpc interceptor + viper，与 backend-dev skill 的分层约定配套。
---

# Go gRPC JWT 鉴权接入规约

技术栈：`github.com/golang-jwt/jwt/v5` · gRPC unary/stream interceptor · viper · 与 `backend-dev` skill 的 Clean Architecture 配套。

本 SKILL.md 是**入口**，只保留决策与硬规则；具体 API 形态、interceptor 实现、运维流程见 `references/*.md`，按需读取。

## 何时适用

- 给现有 gRPC 服务加鉴权（unary 或 stream）。
- 实现登录、登出、refresh token RPC。
- 设计 claims（增减字段、修改 issuer / audience）。
- 切换签名算法（HS256 ↔ RS256）。
- 调试"为什么 metadata 里有 token 但 ctx 里没有 user_id"。

任务若完全不涉及鉴权或 token，不要套用本 skill。

## 深入阅读（按触发场景读，不要预先全读）

| 触发场景 | 读 |
|---|---|
| 设计 Claims 字段、实现 Issuer / Verifier、业务里调签发 | `references/api.md` |
| 配 gRPC interceptor、白名单、metadata 桥接、ctx 存取 | `references/interceptor.md` |
| 密钥与配置、refresh 流程、撤销策略、错误映射、算法切换 | `references/ops.md` |

## 默认选择（可按需覆盖，但要在 PR 里说明）

| 项 | 默认值 | 触发更换的条件 |
|---|---|---|
| 库 | `github.com/golang-jwt/jwt/v5` | 无 |
| 算法 | HS256 | 服务被外部第三方调用、需要公钥分发 → 升 RS256 |
| Access token TTL | 15 min | 业务对短期凭据敏感（如金融）→ 缩到 5 min |
| Refresh token TTL | 7 day | 移动端长会话 → 30 day；高敏感 → 1 day |
| 撤销策略 | 无状态（依赖 exp） | 需要"立即登出"或会话踢出 → 加 Redis denylist |
| header 名 | `authorization` | 无 |
| scheme | `Bearer ` | 无 |

## 模块位置与 import 边界

```
<root>/
├── pkg/
│   └── jwt/                          # 跨服务共享的 JWT 工具
│       ├── jwt.go                    # Config / Claims / errors / Issuer / Verifier（不依赖 grpc）
│       └── interceptor.go            # UnaryAuth / StreamAuth + ctx helpers（依赖 grpc）
└── app/
    └── <svc>/
        └── ioc/
            ├── jwt.go                # InitJWTIssuer / InitJWTVerifier
            └── grpc.go               # 把 interceptor 接到 grpc.NewServer(...)
```

**依赖方向**：`pkg/jwt` 只依赖 stdlib + `golang-jwt/jwt/v5` + `google.golang.org/grpc`，**不依赖**任何 `app/<svc>/`。

**默认 2 文件**起步 —— 单文件超过 ~300 行才拆，按"暴露 API 单元"分（如 `denylist.go`、`metrics.go`），**不要**为命名而拆出 10 行的 `errors.go`。

## 核心硬规则

不读 references 也得记住这 7 条：

1. **业务层不直接操作 token**：service / grpc handler 不 `Parse`、不读 metadata；只通过 `jwt.UserIDFromContext(ctx)` / `RoleFromContext(ctx)` 取身份。
2. **interceptor 是唯一的鉴权出入口**：白名单按 method full name 配置；解析失败统一返回 `codes.Unauthenticated`，对外消息固定 `"unauthenticated"`。
3. **token 类型必须断言**：业务 RPC 只接受 `AccessToken`；refresh 仅用于 `RefreshToken` RPC 换 access。
4. **secret 走环境变量**：`<APP>_<SVC>_JWT_SECRET`，≥ 32 字节，启动校验 fail-fast。
5. **错误不构造 `status.Error`**：`pkg/jwt` 只返回领域哨兵（`ErrTokenExpired` 等）；interceptor 才映射 gRPC code。
6. **claims 不塞敏感字段**：不存 user 对象、email、密码哈希。token 越小越好。
7. **多服务统一一份 `pkg/jwt`**：不允许在 `app/<a>/` 和 `app/<b>/` 各自实现 JWT 工具。

## 工作流 checklist（新增鉴权）

1. **proto 不变**：鉴权是 transport 层关注点，**不**在 proto 里加 `token` 字段。
2. **`pkg/jwt`**：不存在则按 `references/api.md` + `references/interceptor.md` 创建；存在则按需扩 Claims 字段（带 `omitempty`）。
3. **签发服务**（如 user）：`ioc/jwt.go` 加 `InitJWTIssuer`；service 层调 `issuer.Sign(...)`；grpc handler 把 token 写进 response。
4. **所有服务**：`ioc/jwt.go` 加 `InitJWTVerifier`；`ioc/grpc.go` 挂 interceptor；配白名单（Login / Register / RefreshToken / reflection）。
5. **业务层**：用 `jwt.UserIDFromContext(ctx)` 取 user_id；取不到返回 `domain.ErrUnauthenticated`，由 grpc 层翻译为 `codes.Unauthenticated`。
6. **冒烟**：
   - 带 access 调业务 RPC → 通过
   - 无 token 调业务 RPC → `Unauthenticated`
   - 调 `Login` 不带 header → 正常返回 token

## 反模式（明确禁止）

- ❌ secret 写死在代码或 yaml。
- ❌ `none` 算法、< 32 字节 HS256 密钥。
- ❌ 把整个 user 对象、email、密码哈希塞进 claims。
- ❌ `service/` 或 `grpc/` handler 里调 `jwt.Parse` / 读 metadata。
- ❌ 把 refresh token 当 access 用。
- ❌ interceptor 把具体 jwt 错误细节透传给客户端（不要暴露 "signature invalid" 之类内部信息）。
- ❌ 日志里打整个 token（debug 也只打前 8 字节）。
- ❌ 多个服务各自维护一份 JWT 工具。
- ❌ gateway 自定义 `http.HandlerFunc` 做"特殊"鉴权 —— 所有 HTTP 鉴权走同一条 grpc interceptor 链。
- ❌ 按"小到刚好能命名"拆 `pkg/jwt` 文件（如 10 行的 `errors.go` 独立成份）。
