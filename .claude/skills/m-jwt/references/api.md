# m-jwt：API 参考

`pkg/jwt` 暴露给业务与 `ioc` 层的全部类型与函数。

## Claims

```go
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

字段约定：

- **`sub`**：留空或写 user_id 字符串形式。业务读 `UserID`（int64，免类型转换）。
- **`iss`**：固定 `"pivot"`（项目缩写）。
- **`aud`**：写服务名（如 `"user"` / `"order"`）；多服务公用 token 用 slice。
- **`Type`**：区分 access / refresh，**业务接口必须断言为 access**。
- **新增 claim**：一律带 `omitempty`，避免老 token 因新字段缺失而解析失败。

## Config

```go
type Config struct {
    Secret     string        `mapstructure:"secret"`
    AccessTTL  time.Duration `mapstructure:"access_ttl"`
    RefreshTTL time.Duration `mapstructure:"refresh_ttl"`
    Issuer     string        `mapstructure:"issuer"`
    Audience   string        `mapstructure:"audience"`
}
```

加载、env 绑定、校验细节见 `ops.md`。

## Issuer

```go
type Issuer struct {
    secret     []byte
    accessTTL  time.Duration
    refreshTTL time.Duration
    issuer     string
    audience   string
    now        func() time.Time  // 注入便于测试
}

func NewIssuer(cfg Config) *Issuer

// Login 流程：一次签出 access + refresh 两个 token
func (i *Issuer) Sign(userID int64, role string) (access, refresh string, err error)

// Refresh 流程：用合法的 refresh claims 签新 access
func (i *Issuer) Refresh(refreshClaims *Claims) (access string, err error)
```

**Refresh 默认不 rotate**（不发新 refresh）。若要 rotate，调用方在 `service.RefreshToken` 里手动再签一次 refresh 并在 RPC 响应里加 `new_refresh_token` 字段。这是约定外的扩展，PR 描述需说明。

## Verifier

```go
type Verifier struct {
    secret   []byte
    issuer   string
    audience string
    now      func() time.Time
}

func NewVerifier(cfg Config) *Verifier

// 校验签名、exp、nbf、iss、aud；返回 claims 或哨兵错误
func (v *Verifier) Parse(token string) (*Claims, error)
```

`Parse` **不**做 Type 断言（access vs refresh）—— 调用方按场景检查（interceptor 校验 access；`RefreshToken` RPC 校验 refresh）。

## 错误哨兵

```go
var (
    ErrMissingToken   = errors.New("missing token")
    ErrTokenInvalid   = errors.New("invalid token")    // 签名错、格式错
    ErrTokenExpired   = errors.New("token expired")
    ErrWrongTokenType = errors.New("wrong token type") // refresh 打业务等
    ErrTokenRevoked   = errors.New("token revoked")    // 仅 denylist 模式
)
```

**`pkg/jwt` 只返回这些哨兵**，不构造 `status.Error`。映射到 gRPC code 由 interceptor 完成，见 `interceptor.md`。

## wire 装配

```go
// app/<svc>/ioc/jwt.go
func InitJWTIssuer(c *Config) *jwt.Issuer   { return jwt.NewIssuer(c.JWT) }
func InitJWTVerifier(c *Config) *jwt.Verifier { return jwt.NewVerifier(c.JWT) }
```

- **签发服务**（user）注入 Issuer。
- **所有服务**注入 Verifier。
- 用 `wire.NewSet` 直接登记，不需要 `wire.Bind`（这里用的是具体类型）。

## 业务层调用范例

```go
// service/user.go —— Login 业务
func (s *UserService) Login(ctx context.Context, username, password string) (string, string, domain.User, error) {
    u, err := s.repo.FindByUsername(ctx, username)
    if err != nil { /* ... */ }
    if err := bcrypt.CompareHashAndPassword([]byte(u.HashedPassword), []byte(password)); err != nil {
        return "", "", domain.User{}, domain.ErrInvalidCredentials
    }
    access, refresh, err := s.issuer.Sign(u.ID, u.Role)  // ← 在 service 层签
    if err != nil { /* ... */ }
    return access, refresh, u, nil
}

// service/user.go —— RefreshToken 业务
func (s *UserService) RefreshToken(ctx context.Context, refreshToken string) (string, error) {
    claims, err := s.verifier.Parse(refreshToken)
    if err != nil { return "", domain.ErrUnauthenticated }
    if claims.Type != jwt.RefreshToken { return "", domain.ErrUnauthenticated }
    return s.issuer.Refresh(claims)
}
```

## 测试

- **表驱动单测**覆盖：签发往返、过期、wrong type、wrong issuer、wrong audience、tampered signature、nbf 未到。
- `now` 字段注入用来测过期与 nbf —— `i.now = func() time.Time { return fixedTime }`。
- 业务测试**不**跑真实 HS256 签名 —— 直接 `jwt.WithClaims(ctx, &jwt.Claims{...})` 构造身份。
