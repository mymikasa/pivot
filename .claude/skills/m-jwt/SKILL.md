---
name: m-jwt
description: 用于在 Go gRPC 微服务中接入 JWT 鉴权 —— 签发与校验、claims 设计、gRPC interceptor、metadata 传递、refresh 流程、密钥与配置管理。技术栈：golang-jwt/jwt v5 + grpc interceptor + viper，与 backend-dev skill 的分层约定配套。
---

# Go gRPC JWT 鉴权接入规约

技术栈：`github.com/golang-jwt/jwt/v5` · gRPC unary/stream interceptor · viper · 与 `backend-dev` skill 的 Clean Architecture 配套。

本 skill 定义三件事：（A）`pkg/jwt` 共享库的 API 契约，（B）interceptor 与 metadata 的接入方式，（C）密钥、claims、refresh 的工程约定。涉及 JWT 的开发都遵循它。

## 何时适用

- 给现有 gRPC 服务加鉴权（unary 或 stream）。
- 实现登录、登出、refresh token RPC。
- 设计 claims（增减字段、修改 issuer / audience）。
- 切换签名算法（HS256 ↔ RS256）。
- 调试"为什么 metadata 里有 token 但 ctx 里没有 user_id"。

任务若完全不涉及鉴权或 token，不要套用本 skill。

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
│       ├── claims.go                 # Claims 结构体（嵌入 jwt.RegisteredClaims）
│       ├── issuer.go                 # *Issuer：签发 access + refresh
│       ├── verifier.go               # *Verifier：解析 + 校验
│       ├── interceptor.go            # gRPC unary / stream 拦截器
│       ├── context.go                # ctx ↔ user_id / role 存取
│       ├── config.go                 # JWT 配置结构体
│       ├── errors.go                 # 哨兵错误：ErrTokenExpired / ErrTokenInvalid / ErrMissingToken
│       └── *_test.go
└── app/
    └── <svc>/
        └── ioc/
            ├── jwt.go                # InitJWTIssuer / InitJWTVerifier，从 Config 构造
            └── grpc.go               # 把 interceptor 接到 grpc.NewServer(...)
```

**依赖方向**：`pkg/jwt` 只依赖 stdlib + `golang-jwt/jwt/v5` + `google.golang.org/grpc`，**不依赖**任何 `app/<svc>/` 的代码。它是公共工具，不感知业务。

**业务层不直接操作 token**：
- ❌ `service/user.go` 里 `jwt.Parse(...)` —— interceptor 已经做完了。
- ❌ `service/user.go` 里读 grpc metadata —— 取 user_id 走 `jwt.UserIDFromContext(ctx)`。

## Claims 设计

```go
// pkg/jwt/claims.go
package jwt

import jwtv5 "github.com/golang-jwt/jwt/v5"

type TokenType string

const (
    AccessToken  TokenType = "access"
    RefreshToken TokenType = "refresh"
)

type Claims struct {
    jwtv5.RegisteredClaims
    UserID int64     `json:"uid"`
    Role   string    `json:"role,omitempty"`
    Type   TokenType `json:"typ"`
}
```

约定：

- **`sub`** 留空或写 user_id 字符串形式；业务读 `UserID` 字段（int64，免类型转换）。
- **`iss`** 固定 `"pivot"`（项目缩写）。
- **`aud`** 写服务名（如 `"user"`、`"order"`）；多服务公用 token 时用 slice。
- **`Type`** 区分 access / refresh，校验时**必须**断言；refresh token 不允许打业务接口。
- **不要**塞用户名、邮箱、整个 user 对象。token 越小越好，敏感字段更不能塞。
- **新增 claim** 要给 omitempty，避免老 token 解析失败。

## Issuer / Verifier API

```go
// pkg/jwt/issuer.go
type Issuer struct {
    secret        []byte
    accessTTL     time.Duration
    refreshTTL    time.Duration
    issuer        string
    audience      []string
    now           func() time.Time   // 注入便于测试
}

func NewIssuer(cfg Config) *Issuer { ... }

// 一次签发一对 token；refresh 只用来换 access，不打业务
func (i *Issuer) Sign(userID int64, role string) (access, refresh string, err error) { ... }

// 单独签 refresh → access（refresh 流程）
func (i *Issuer) Refresh(refreshClaims *Claims) (access string, err error) { ... }
```

```go
// pkg/jwt/verifier.go
type Verifier struct {
    secret   []byte
    issuer   string
    audience string
    now      func() time.Time
}

func NewVerifier(cfg Config) *Verifier { ... }

// 校验签名、exp、nbf、iss、aud；返回 claims 或哨兵错误
func (v *Verifier) Parse(token string) (*Claims, error) { ... }
```

**Issuer / Verifier 通过 wire 分别构造**（Bind 到接口便于 mock）：

```go
// app/<svc>/ioc/jwt.go
func InitJWTIssuer(c *Config) *jwt.Issuer { return jwt.NewIssuer(c.JWT) }
func InitJWTVerifier(c *Config) *jwt.Verifier { return jwt.NewVerifier(c.JWT) }
```

签发只在签发服务（如 user 服务的 Login）注入 Issuer；其他服务只装 Verifier。

## gRPC Interceptor 接入

```go
// pkg/jwt/interceptor.go

// 白名单：method full name（如 "/pivot.user.v1.UserService/Login"）跳过校验
func UnaryAuth(v *Verifier, whitelist map[string]struct{}) grpc.UnaryServerInterceptor
func StreamAuth(v *Verifier, whitelist map[string]struct{}) grpc.StreamServerInterceptor
```

**装配**（`ioc/grpc.go`）：

```go
func InitGRPCServer(svc *usergrpc.UserServer, v *jwt.Verifier) *grpc.Server {
    whitelist := map[string]struct{}{
        "/pivot.user.v1.UserService/Login":    {},
        "/pivot.user.v1.UserService/Register": {},
        "/grpc.reflection.v1.ServerReflection/ServerReflectionInfo": {},
    }
    s := grpc.NewServer(
        grpc.UnaryInterceptor(jwt.UnaryAuth(v, whitelist)),
        grpc.StreamInterceptor(jwt.StreamAuth(v, whitelist)),
    )
    userv1.RegisterUserServiceServer(s, svc)
    reflection.Register(s)
    return s
}
```

约定：

- **白名单按 method full name**，不按服务/RPC 名分别配，避免漏配。
- **interceptor 解析失败统一返回 `codes.Unauthenticated`**，错误消息不泄漏内部细节（"invalid token" 即可，不要说"signature mismatch"）。
- **token 类型校验**：业务 RPC 只接受 `AccessToken`；refresh 流程例外，由 `/.../Refresh` RPC 自己处理。
- **interceptor 解析后把 claims 放进 ctx**，handler 通过 `jwt.UserIDFromContext(ctx)` 取。

## Metadata 与 HTTP 桥接

gRPC 客户端把 token 放进 metadata：

```
authorization: Bearer <token>
```

HTTP 客户端打 grpc-gateway 时发 `Authorization: Bearer <token>` header；**grpc-gateway 默认会把 `Authorization` 这个 header 转成 `authorization` metadata**，不需要额外配置。

如果业务上还有别的 header（如 `X-Request-Id`）也想透传到 grpc metadata，要在 gateway 注册时显式声明：

```go
mux := runtime.NewServeMux(
    runtime.WithIncomingHeaderMatcher(func(h string) (string, bool) {
        switch strings.ToLower(h) {
        case "authorization", "x-request-id":
            return strings.ToLower(h), true
        default:
            return "", false
        }
    }),
)
```

## Context 存取

```go
// pkg/jwt/context.go
type ctxKey int
const claimsKey ctxKey = 0

func WithClaims(ctx context.Context, c *Claims) context.Context
func ClaimsFromContext(ctx context.Context) (*Claims, bool)

// 业务最常用的两个 helper
func UserIDFromContext(ctx context.Context) (int64, bool)
func RoleFromContext(ctx context.Context) (string, bool)
```

约定：

- **业务代码只用 helper，不直接读 ctx value**。helper 是单一入口，便于未来增减字段。
- **interceptor 是唯一往 ctx 塞 claims 的地方**。service / grpc handler 不许构造 claims 写回 ctx。
- 白名单接口（Login / Register）从 ctx 取不到 user_id，要主动处理 `ok == false`。

## 密钥与配置

`pkg/jwt/config.go`：

```go
type Config struct {
    Secret     string        `mapstructure:"secret"`       // HS256 共享密钥；RS256 走 PrivateKeyPath
    AccessTTL  time.Duration `mapstructure:"access_ttl"`   // 默认 15m
    RefreshTTL time.Duration `mapstructure:"refresh_ttl"`  // 默认 168h
    Issuer     string        `mapstructure:"issuer"`       // 默认 "pivot"
    Audience   string        `mapstructure:"audience"`     // 服务名，如 "user"
}
```

服务 `config.yaml` 加 `jwt` 块：

```yaml
jwt:
  access_ttl: 15m
  refresh_ttl: 168h
  issuer: pivot
  audience: user
  # secret 永远走环境变量，不进 yaml
```

环境变量：`<APP>_<SVC>_JWT_SECRET`（如 `PIVOT_USER_JWT_SECRET`）。

**密钥要求**：

- HS256：≥ 32 字节随机串（生产用 `openssl rand -base64 32`）。
- 启动时校验长度，`< 32` 直接 `log.Fatal`。
- **永远不进代码、不进 git、不进日志**（包括 error message 里 `%v` 整个 config）。
- 测试用一个固定的 weak secret（如 `"test-secret-32-bytes-long-xxxxxx"`），通过环境变量或测试 fixture 注入，不要硬编码进生产路径。

## Refresh 流程

- Login RPC 一次返回 access + refresh 两个 token。
- 客户端用 access 打业务；access 过期前几分钟用 refresh 调 `Refresh` RPC 换新 access。
- `Refresh` RPC **在白名单里**（不需要 access），但要校验 refresh token 本身：签名、exp、`Type == RefreshToken`。
- 换发出的 access 可以续 access 的 TTL；refresh **不** rotate（除非启用"refresh rotation"策略，那是单独的复杂度，按需开）。

## 撤销 / 登出

**默认无状态**：登出由客户端"删本地 token"完成，服务端不维护状态，依赖 access 的短 TTL 自然过期。

如果业务需要"立即吊销"（被踢出、密码改了），加 Redis denylist：

- 给 token 多签一个 `jti` claim（UUID）。
- 登出时把 `jti → exp` 写入 Redis，TTL 设为剩余有效期。
- Verifier 在校验通过后**额外**查 Redis；命中 denylist 返回 `ErrTokenRevoked`。
- 这条路径增加每次 RPC 一次 Redis 调用，**只在需要时启用**，不要默认开。

## 错误处理

```go
// pkg/jwt/errors.go
var (
    ErrMissingToken = errors.New("missing token")
    ErrTokenInvalid = errors.New("invalid token")    // 签名错、格式错
    ErrTokenExpired = errors.New("token expired")
    ErrTokenRevoked = errors.New("token revoked")    // 仅 denylist 模式
    ErrWrongTokenType = errors.New("wrong token type") // refresh 打业务等
)
```

约定：

- `pkg/jwt` 返回**领域错误**（哨兵），**不构造** `status.Error`。
- interceptor 内部做映射：所有 jwt.Err* → `codes.Unauthenticated`，外部消息统一 `"unauthenticated"`，不区分具体原因。
- 与 `backend-dev` skill 的错误处理风格一致：领域 → status 的映射只在适配层（这里是 interceptor）。

## 测试

- **`pkg/jwt`**：纯单测，覆盖签发、过期、wrong type、wrong issuer、wrong audience、tampered signature。`now` 字段注入用来测过期与 nbf。
- **interceptor**：用 `httptest`/bufconn 起一个 gRPC server 测白名单、metadata 缺失、token 错误三类。
- **service / grpc handler**：mock 时通过 `WithClaims(ctx, ...)` 直接构造带身份的 ctx，不走真实签发。
- 不要在业务测试里跑真实 HS256 签名 —— 慢且无信息量。

## 反模式（明确禁止）

- ❌ 把 secret 写死在代码或 yaml。
- ❌ 用 `none` 算法、短于 32 字节的 HS256 密钥。
- ❌ 把 user 对象、email、密码哈希塞进 claims。
- ❌ `service/` 里 import `pkg/jwt` 然后调 `Parse`。业务只读 ctx。
- ❌ `grpc/` handler 里读 metadata 取 token。interceptor 已经处理。
- ❌ 把 refresh token 当 access 用。
- ❌ interceptor 把具体 jwt 错误透传给客户端（"signature invalid" / "audience mismatch" 都不要外泄）。
- ❌ 在 error 日志里打整个 token（即使 debug 也只打前 8 字节）。
- ❌ 多个服务各自维护一份 JWT 工具代码。统一在 `pkg/jwt`。
- ❌ 在 gateway 自定义 `http.HandlerFunc` 做"特殊"鉴权。所有 HTTP 鉴权走同一条 grpc interceptor 链。

## 工作流 checklist（新增鉴权）

1. **proto 不变**。鉴权是 transport 层关注点，**不**在 proto 里加 `token` 字段。
2. **`pkg/jwt`**：如不存在则按本 skill 创建；存在则按需扩 Claims 字段（带 omitempty）。
3. **签发服务（如 user）**：
   - `ioc/jwt.go` 加 `InitJWTIssuer`，注册到 `ProviderSet`。
   - 在 `service/<svc>.go` 的 Login 业务里调 `issuer.Sign(...)`，**不要**在 grpc handler 里调。
   - grpc handler 把 access / refresh 写进 response message。
4. **所有服务**：
   - `ioc/jwt.go` 加 `InitJWTVerifier`。
   - `ioc/grpc.go` 把 interceptor 挂到 `grpc.NewServer`。
   - 配 `Login` / `Register` / `Refresh` / reflection 的白名单。
5. **业务层**：所有要"按当前用户操作"的 service 方法用 `jwt.UserIDFromContext(ctx)`；取不到就返回 `domain.ErrUnauthenticated`，由 grpc 层翻译为 `codes.Unauthenticated`。
6. **冒烟**：
   - `grpcurl -plaintext -H "authorization: Bearer <token>" ...` 验业务调用。
   - 不带 header 调业务 RPC 应得 `Unauthenticated`。
   - 调 `/Login` 不带 header 应能正常返回 token。
