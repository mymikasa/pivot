# m-jwt：Interceptor 与 Context

`pkg/jwt/interceptor.go` 覆盖：unary / stream interceptor、metadata 解析、ctx 存取 helper。

## 公开 API

```go
func UnaryAuth(v *Verifier, whitelist map[string]struct{}) grpc.UnaryServerInterceptor
func StreamAuth(v *Verifier, whitelist map[string]struct{}) grpc.StreamServerInterceptor

func WithClaims(ctx context.Context, c *Claims) context.Context
func ClaimsFromContext(ctx context.Context) (*Claims, bool)
func UserIDFromContext(ctx context.Context) (int64, bool)
func RoleFromContext(ctx context.Context) (string, bool)
```

## 装配

```go
// app/<svc>/ioc/grpc.go
var authWhitelist = map[string]struct{}{
    "/pivot.user.v1.UserService/Login":                               {},
    "/pivot.user.v1.UserService/Register":                            {},
    "/pivot.user.v1.UserService/RefreshToken":                        {},
    "/grpc.reflection.v1.ServerReflection/ServerReflectionInfo":      {},
    "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo": {},
}

func InitGRPCServer(svc *usergrpc.UserServer, v *jwt.Verifier) *grpc.Server {
    s := grpc.NewServer(
        grpc.UnaryInterceptor(jwt.UnaryAuth(v, authWhitelist)),
        grpc.StreamInterceptor(jwt.StreamAuth(v, authWhitelist)),
    )
    userv1.RegisterUserServiceServer(s, svc)
    reflection.Register(s)
    return s
}
```

## 白名单约定

- **按 method full name** 写（如 `/pivot.user.v1.UserService/Login`），不按服务/RPC 名分别配。
- 必须加 `/Login` `/Register` `/RefreshToken`、reflection 服务（**v1 + v1alpha 都要**，否则 `grpcurl` 调通不了）。
- **不要**通配符 / 前缀匹配 —— 显式列出更安全，加新 RPC 时强制 review。

## 解析流程（interceptor 内部）

1. 命中白名单 → 直接 `handler(ctx, req)`，跳过所有校验。
2. 读 `authorization` metadata；缺失 → `codes.Unauthenticated "unauthenticated"`。
3. 校 `Bearer ` 前缀（大小写不敏感）；不对 → 同上。
4. `Verifier.Parse(token)` 校签名、exp、nbf、iss、aud；失败 → 同上。
5. **断言 `claims.Type == AccessToken`**（业务 RPC 不接受 refresh）；不是 → 同上。
6. `WithClaims(ctx, claims)` 把 claims 写进 ctx，调 handler。

**所有失败统一外抛 `codes.Unauthenticated` + `"unauthenticated"`**，不区分原因。**绝不**把 "signature mismatch" / "audience mismatch" 等内部细节透传给客户端。

## Stream 包装

`StreamAuth` 用一个 `wrappedStream` 把 `Context()` 重写为塞了 claims 的 ctx：

```go
type wrappedStream struct {
    grpc.ServerStream
    ctx context.Context
}
func (w *wrappedStream) Context() context.Context { return w.ctx }
```

下游 stream handler 用 `jwt.UserIDFromContext(stream.Context())` 取 user_id，写法与 unary 完全一致。

## Context 存取约定

- **业务代码只用 helper**：`UserIDFromContext` / `RoleFromContext` / `ClaimsFromContext`，不直接读 ctx value。helper 是单一入口，便于未来增减字段。
- **interceptor 是唯一往 ctx 塞 claims 的地方**：service / grpc handler **不许** 调 `WithClaims` 写回 ctx。
- **白名单接口里取不到 claims**：Login / Register 等从 ctx 取 user_id 时 `ok == false`，要主动处理；不要假设非 nil。

## HTTP gateway 桥接

gRPC 客户端发：
```
authorization: Bearer <token>
```

HTTP 客户端打 grpc-gateway 时发 `Authorization: Bearer <token>` header；**grpc-gateway 默认会把 `Authorization` header 转成 `authorization` metadata**，不需要额外配置。

如果业务还要透传别的 header（如 `X-Request-Id`），在 gateway 注册时显式声明：

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

## 测试

- 用 `bufconn` 起一个真实 gRPC server，跑三类场景：
  - 白名单方法不带 token → 通过
  - 业务方法不带 token → `Unauthenticated`
  - 业务方法带过期 / 无效 / 错类型 token → `Unauthenticated`
- mock service / grpc handler 时直接 `ctx := jwt.WithClaims(ctx, &jwt.Claims{UserID: 1, Role: "admin", Type: jwt.AccessToken})` 构造身份，**不走真实签发**。
