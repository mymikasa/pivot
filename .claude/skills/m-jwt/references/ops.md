# m-jwt：运维与流程

密钥管理、配置加载、refresh 流程、撤销策略、错误映射、算法切换 —— 部署期需要做决策的所有约定。

## 密钥与配置

服务的 `ioc/config.go` 嵌入 `pkg/jwt` 的 Config：

```go
type Config struct {
    JWT jwtpkg.Config `mapstructure:"jwt"`
    // ... 其他配置
}
```

`config.yaml`：

```yaml
jwt:
  access_ttl: 15m
  refresh_ttl: 168h
  issuer: pivot
  audience: user
  # secret 永远走环境变量，不进 yaml
```

环境变量：`<APP>_<SVC>_JWT_SECRET`（如 `PIVOT_USER_JWT_SECRET`）。

### viper env 绑定坑

`AutomaticEnv()` **不会**自动覆盖 `Unmarshal` 的嵌套字段，必须显式 `BindEnv`：

```go
for _, key := range []string{"jwt.secret", "db.dsn"} {
    if err := v.BindEnv(key); err != nil {
        return nil, fmt.Errorf("bind env for %s: %w", key, err)
    }
}
```

漏了 `BindEnv` 的症状：env var 设了但启动报"jwt.secret must be at least 32 bytes"。

### 密钥要求

- HS256：≥ 32 字节随机串。生产用 `openssl rand -base64 32` 生成。
- 启动时校验长度，`< 32` 直接 `log.Fatal` —— fail-fast。
- **永远不进**代码、yaml、git、日志（包括 error message 里 `%v` 打整个 config）。
- 测试用固定 weak secret（如 `"test-secret-32-bytes-long-xxxxxx"`），通过 env 或测试 fixture 注入；不要硬编码进生产路径。

## Refresh 流程

- Login RPC 一次返回 access + refresh 两个 token。
- 客户端用 access 打业务；access 过期前几分钟用 refresh 调 `RefreshToken` RPC 换新 access。
- `RefreshToken` RPC **在白名单里**（不需要 access 校验），但 service 实现自己校验 refresh：
  1. `Verifier.Parse(refreshToken)` 校签名 + 过期 + iss + aud
  2. **断言** `claims.Type == RefreshToken`
  3. `Issuer.Refresh(claims)` 签新 access
- **不 rotate**：新 access 沿用原 refresh，refresh 自然过期。
- 想 rotate（每次 refresh 同时换新 refresh）：在 `service.RefreshToken` 里手动 `Issuer.Sign(...)` 多签一对，response 加 `new_refresh_token` 字段。这是 m-jwt skill 之外的扩展，**PR 必须说明**。

## 撤销 / 登出

**默认无状态**：登出由客户端"删本地 token"完成，服务端只在 logout RPC 里记日志（按需），依赖 access 的短 TTL 自然过期。

如果业务需要"立即吊销"（被踢出、改密码后旧 token 失效），加 Redis denylist：

- 给 token 多签一个 `jti` claim（UUID）。
- 登出（或改密码）时把 `jti → exp` 写入 Redis，TTL 设为 token 剩余有效期。
- Verifier 在校验通过后**额外**查 Redis；命中 denylist 返回 `ErrTokenRevoked`。
- 这条路径**增加每次 RPC 一次 Redis 调用**，只在需要时启用。
- 配 `denylist.enabled: true` 之类的开关，默认 off。

实现位置：单独建 `pkg/jwt/denylist.go`，不要污染 verifier 主逻辑。Verifier 通过构造时注入一个可选的 `Denylist` 接口，`nil` 表示禁用。

## 错误处理

`pkg/jwt` 返回这些哨兵（不构造 `status.Error`）：

```go
var (
    ErrMissingToken   = errors.New("missing token")
    ErrTokenInvalid   = errors.New("invalid token")
    ErrTokenExpired   = errors.New("token expired")
    ErrWrongTokenType = errors.New("wrong token type")
    ErrTokenRevoked   = errors.New("token revoked")
)
```

层与层的责任：

| 层 | 看到 jwt 错误怎么办 |
|---|---|
| `pkg/jwt` 内部 | 把第三方库错误（`jwtv5.ErrTokenExpired` 等）归一为本包哨兵 |
| `interceptor` | 全部 → `codes.Unauthenticated "unauthenticated"`，对外消息一致，**不暴露细节** |
| `service` | 调 `Verifier.Parse` 失败（如 `RefreshToken` 流程）→ 转 `domain.ErrUnauthenticated`，由 grpc 层映射 |
| `grpc` handler | 不直接调 `pkg/jwt`；错误已被 service 转成 domain 错误 |

## 算法切换：HS256 → RS256

何时换：

- 服务被外部第三方调用，token 需要给对方校验，但**不想分享 secret**。
- 需要 token 离线校验（CDN / 边缘节点）。

切换步骤：

1. 生成 RSA key pair：
   ```bash
   openssl genrsa -out private.pem 2048
   openssl rsa -in private.pem -pubout -out public.pem
   ```
2. `Config` 加 `PrivateKeyPath` / `PublicKeyPath` 字段；`Secret` 字段保留作兼容期。
3. `NewIssuer` / `NewVerifier` 按 algo 分支构造 `signer` / `keyfunc`。
4. proto 不变，token 体也不变，**仅签名算法换**。
5. 灰度期 Verifier 同时接受新老算法（按 token header `alg` 判定），上完一周后下线 HS256。
