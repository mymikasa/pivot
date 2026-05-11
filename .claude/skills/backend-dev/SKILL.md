---
name: backend-dev
description: 用于 Go gRPC 微服务开发 —— 新建服务、修改 .proto、编写 domain/repository/service/ioc/cmd 代码、用 wire 装配依赖、用 buf 生成 gRPC 与 grpc-gateway 代码，或对分层、错误、配置、持久化做决策。技术栈：原生 gRPC + grpc-gateway + buf + wire + gorm + viper，Clean Architecture。
---

# Go gRPC 微服务开发规约

技术栈：原生 gRPC · grpc-gateway · buf · wire · gorm · viper · Clean Architecture。

本 skill 定义三件事：（A）目录与代码约定，（B）分层规则，（C）每次变更的工作流。涉及上述技术栈的后端开发都遵循它。

## 何时适用

- 新建微服务。
- 新增/修改 RPC、请求响应字段、proto enum。
- 给 RPC 加/改 HTTP 映射（`google.api.http` 注解、URL 路径、HTTP method、body 字段）。
- 编写或修改 `app/<svc>/{cmd,domain,grpc,service,repository,ioc}` 下的代码。
- 新增数据库表、查询、迁移，或引入外部依赖。
- 装配 provider（wire）、重新生成 proto（buf）、改动配置（viper）。

任务若完全不涉及以上场景，不要套用本 skill。

## 占位符约定

下文出现的占位符：

- `<module>` — Go module 路径（`go.mod` 第一行）。
- `<svc>` — 微服务名（小写、单数，如 `user`、`order`）。
- `<Svc>` — 同上但首字母大写（用于类型名与 service 名）。
- `<entity>` — 领域实体名（小写）。
- `<APP>` — 项目缩写大写，用作环境变量前缀（启动时由项目约定）。

## 架构（Clean Architecture）

```
  HTTP ─▶ grpc-gateway ─┐
                        ├─▶ grpc adapter ─▶ service ─▶ repository ─▶ dao ─▶ DB
  gRPC ─────────────────┘         │             │            │
                                  └──────── domain ──────────┘   （实体与错误，无外部依赖）

  proto (api/proto) ─▶ buf generate ─▶ api/gen/<svc>/v1/{*.pb.go, *_grpc.pb.go, *.pb.gw.go}
```

**依赖方向单向、向内。** 每一层只能依赖图中右侧的层 + `domain`：

| 层 | 可以 import | 禁止 import |
|---|---|---|
| `domain` | 仅 stdlib | `app/` 下任何其他包 |
| `repository/dao` | `gorm`、stdlib | `service`、`grpc`；DAO 结构体里不出现 `domain` 类型 |
| `repository` | `dao`（通过接口）、`domain` | `service`、`grpc`、gRPC 生成代码 |
| `service` | `repository`（通过接口）、`domain` | `dao`、`gorm`、`viper`、`grpc`、gRPC 生成代码 |
| `grpc` | `service`（通过接口）、`domain`、gRPC 生成代码 | `repository`、`dao`、`gorm` |
| `ioc` | 任何包（组合根） | — |
| `cmd` | 仅 `ioc` | — |

**接口集中在每层的 `types.go`，producer-side 暴露，便于上层 mock 测试。** 每一层在自己的 `types.go` 中声明对外契约，上层通过接口依赖：

- `service/types.go` — `Service` 接口（暴露给 grpc）。
- `repository/types.go` — `Repository` 接口（暴露给 service）。
- `repository/dao/types.go` — `DAO` 接口（暴露给 repository）。
- `grpc/` **没有自己的接口文件**：grpc 层本身就是 proto `<Svc>ServiceServer` 的实现，没有上层需要 mock 它。

接口与实现绑定通过 wire 在 `ioc` 完成。每层单测都 mock 自己依赖的下层接口（grpc mock `service.Service`、service mock `repository.Repository`、repository mock `dao.DAO`），实现层与适配层解耦。

**grpc 与 service 是不同层**：grpc 只做 proto request/response ↔ domain 的翻译与错误码映射，**不写业务逻辑**；service 是纯业务逻辑，不依赖任何 gRPC 生成代码。

**grpc-gateway 不是独立的一层，它是 grpc 层的 HTTP 适配器**。所有业务逻辑只写在 service 里，gateway 仅做协议翻译。绝不允许在 gateway 注册自定义 handler 来绕过 gRPC。

## 目录结构

```
<root>/
├── go.mod                              # module: <module>
├── buf.yaml                            # buf workspace 配置
├── buf.gen.yaml                        # 代码生成配置（go / grpc / gateway / openapi）
├── api/
│   ├── proto/<svc>/v1/<svc>.proto      # 唯一真相源，含 google.api.http 注解
│   └── gen/
│       ├── <svc>/v1/                   # *.pb.go / *_grpc.pb.go / *.pb.gw.go
│       └── openapi/<svc>/v1/<svc>.swagger.json   # 可选
├── app/
│   └── <svc>/                          # 每个微服务一个目录
│       ├── cmd/
│       │   ├── main.go                 # 入口：加载配置 → wire → 启动 gRPC + HTTP
│       │   ├── wire.go                 # //go:build wireinject
│       │   ├── wire_gen.go             # 生成产物
│       │   └── config.yaml             # 本地开发配置
│       ├── domain/
│       │   ├── <entity>.go             # 纯结构体，不带 gorm/json tag
│       │   └── errors.go               # 哨兵错误
│       ├── grpc/
│       │   ├── <svc>.go                # gRPC server 实现（嵌入 Unimplemented...Server），调用 service.Service；含 proto ↔ domain 转换函数
│       │   ├── errors.go               # domain 错误 → gRPC status.Error 映射
│       │   └── <svc>_test.go           # mock service.Service
│       ├── service/
│       │   ├── types.go                # Service 接口（暴露给 grpc）
│       │   ├── <svc>.go                # Service 接口的实现（纯业务逻辑）
│       │   └── <svc>_test.go           # mock repository.Repository
│       ├── repository/
│       │   ├── types.go                # Repository 接口（暴露给 service）
│       │   ├── <entity>.go             # Repository 接口的实现，含 dao ↔ domain 转换函数
│       │   ├── <entity>_test.go        # mock dao.DAO
│       │   └── dao/
│       │       ├── types.go            # DAO 接口（暴露给 repository）
│       │       ├── <entity>.go         # gorm model + DAO 接口的实现（CRUD）
│       │       └── <entity>_test.go    # 真实 DB 集成测试
│       └── ioc/
│           ├── wire.go                 # ProviderSet
│           ├── db.go                   # InitDB() *gorm.DB
│           ├── grpc.go                 # InitGRPCServer(...)
│           ├── gateway.go              # InitHTTPGateway(...) — 注册 gateway mux
│           └── config.go               # InitConfig() + 类型化 Config
└── third_party/                        # vendored proto 依赖
    ├── googleapis/google/api/          # annotations.proto / http.proto（gateway 必备）
    └── grpc-gateway/                   # openapiv2 等扩展（可选）
```

## 技术栈约定

### Protobuf + buf

- 文件路径：`api/proto/<svc>/v1/<svc>.proto`，永远带版本号 `v1`。
- 包名遵循 `<org>.<svc>.v1` 形式（如 `acme.user.v1`），与项目约定一致。
- `option go_package = "<module>/api/gen/<svc>/v1;<svc>v1";`
- 时间用 `google.protobuf.Timestamp`，不用 int64。
- field number 永久占用，**不重命名、不复用**。
- 在仓库根执行 `buf generate`，CI 加 `buf lint` + `buf breaking`（against main 分支）。
- 服务命名：`service <Svc>Service { rpc CreateXxx(CreateXxxRequest) returns (CreateXxxResponse); }`。请求响应必须包裹成 message，不直接用标量。
- 每个 RPC 必须带 `google.api.http` 注解（除非明确决定不暴露 HTTP）。范例见下方 grpc-gateway 小节。

`buf.gen.yaml` 至少包含四个插件：`protoc-gen-go`、`protoc-gen-go-grpc`、`protoc-gen-grpc-gateway`、`protoc-gen-openapiv2`（openapi 可选但强烈建议）。生成路径统一到 `api/gen/`，与 proto 源同 commit。

### grpc-gateway

gateway 让同一份 proto 同时支持 gRPC 与 RESTful HTTP，**避免**手写一套 HTTP handler。

**proto 注解约定：**

```proto
import "google/api/annotations.proto";

service UserService {
  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse) {
    option (google.api.http) = {
      post: "/api/v1/users"
      body: "*"
    };
  }
  rpc GetUser(GetUserRequest) returns (GetUserResponse) {
    option (google.api.http) = {
      get: "/api/v1/users/{user_id}"
    };
  }
  rpc UpdateUser(UpdateUserRequest) returns (UpdateUserResponse) {
    option (google.api.http) = {
      patch: "/api/v1/users/{user_id}"
      body: "*"
    };
  }
  rpc DeleteUser(DeleteUserRequest) returns (DeleteUserResponse) {
    option (google.api.http) = {
      delete: "/api/v1/users/{user_id}"
    };
  }
}
```

**HTTP 语义规则：**

- **路径**：`/api/v{n}/<plural-resource>[/{id}][/<sub-resource>]`，资源用复数。
- **方法对应**：Create→POST、Get→GET、List→GET、Update→PATCH（部分更新）、Replace→PUT（完整替换）、Delete→DELETE。
- **body**：写操作显式声明 `body: "*"` 或具体字段名；读操作不写 body。
- **路径参数**字段名与 message 字段名严格一致（`/{user_id}` ↔ `string user_id = 1;`）。
- **分页/过滤** 用 query 参数自动映射，不需要额外配置（如 `?page_size=20&page_token=xxx`）。

**装配方式（`ioc/gateway.go`）：**

- 用 `runtime.NewServeMux()` 创建 gateway mux。
- 通过 in-process 连接调用本服务的 gRPC server（`grpc.NewClient` + `passthrough://` 或直接走 bufconn），避免回环到 TCP。
- 同进程内 gRPC server 与 HTTP gateway **分两个端口**监听（如 `:9090` gRPC、`:8080` HTTP），不要用 cmux 在单端口复用 —— 排查问题更困难。
- HTTP 中间件（CORS、auth、access log）在 gateway 这一层加，**不要**污染 gRPC interceptor。

**错误映射：**

- service 返回 gRPC `status.Error`，grpc-gateway 默认会按 [HTTP↔gRPC code 映射表](https://github.com/grpc-ecosystem/grpc-gateway/blob/main/runtime/errors.go) 翻译。
- 需要自定义错误体格式时，用 `runtime.WithErrorHandler` 注入统一 handler；不要在 service 里塞 HTTP-specific 字段。

### wire（依赖注入）

- 每个服务有且仅有一个 `ProviderSet`，定义在 `ioc/wire.go`，至少包含：DB、gRPC server、HTTP gateway、Logger、Config。
- `cmd/wire.go` 调用 `wire.Build(ioc.ProviderSet, grpc.NewServer)`，返回 `*App`（包含 gRPC server、HTTP server、cleanup）。
- 三层接口到实现都用 `wire.Bind` 显式绑定：
  - `wire.Bind(new(service.Service), new(*service.UserService))`
  - `wire.Bind(new(repository.Repository), new(*repository.UserRepository))`
  - `wire.Bind(new(dao.DAO), new(*dao.UserDAO))`
- 任何 provider 变更后重新执行 `go generate ./app/<svc>/cmd/...`，**不要手改 `wire_gen.go`**。

### gorm

- DAO 返回 **自己的** 结构体（`dao.User`），不返回 `domain.User`。映射由 repository 负责。
- 所有 DAO 方法第一个参数是 `ctx context.Context`，内部调用 `db.WithContext(ctx)`。
- 生产代码路径中**不允许** `db.AutoMigrate`。迁移走独立工具（`golang-migrate` 或纯 SQL 文件，二选一并坚持）。
- 软删除（`gorm.DeletedAt`）只在业务真实需要时使用，默认硬删。
- `*gorm.DB` 不暴露出 dao 包。

### viper

- 每个服务在 `ioc/config.go` 定义一个类型化 `Config` 结构体，至少包含 `GRPC.Addr`、`HTTP.Addr`、`DB`、`Log` 几块。
- 禁止在业务代码里散落 `viper.GetString("foo.bar")`。
- 配置文件路径由环境变量决定，约定一个统一前缀 `<APP>_<SVC>_CONFIG`，缺省 `./config.yaml`。
- 环境变量覆盖前缀 `<APP>_<SVC>_`（如 `<APP>_USER_DB_DSN`、`<APP>_USER_HTTP_ADDR`）。
- 启动时校验必填字段，fail fast。

### 错误处理

- 领域错误声明为哨兵变量，放在 `domain/errors.go`：`var ErrUserNotFound = errors.New("user not found")`。
- dao 把基础设施错误（`gorm.ErrRecordNotFound` 等）映射为领域错误后返回，**不向上泄漏** `gorm` 错误。
- repository 透传领域错误，需要附加上下文时用 `fmt.Errorf("...: %w", domain.ErrXxx)`。
- service 只返回领域错误，**不构造** gRPC `status.Error`，保持业务层与 gRPC 解耦。
- grpc adapter 在 `grpc/errors.go` 集中映射领域错误 → gRPC `status.Error(codes.NotFound, ...)`，封装一个 `toGRPCError(err)` 工具函数。grpc handler 调用 service 后统一走该函数。
- HTTP 状态码由 grpc-gateway 自动从 gRPC code 翻译，**禁止**在 service 或 grpc adapter 里直接返回 HTTP 状态。

### 跨层数据转换

跨层传递数据时**必须**封装独立的转换函数，**不要**把映射逻辑塞进业务方法体：

- `repository/<entity>.go` —— `toDomain(dao.User) domain.User`、按需 `fromDomain(domain.User) dao.User`。
- `grpc/<svc>.go` —— `toProto(domain.User) *userv1.User`、按需 `fromProto(*userv1.CreateUserRequest) domain.NewUserInput`。

这是"重复消除"规则的**例外**：转换函数无论调用一次还是多次都独立写。原因：

- **可读性** —— 业务流程不被字段拼装淹没，主方法专注控制流。
- **可测性** —— 字段错位是高发 bug，独立函数表驱动一次覆盖。
- **可维护性** —— 加字段只改一处，不会漏更新别的调用点。

命名：单实体用 `toDomain` / `toProto`；同一包内有多个实体时按实体区分（`toDomainUser`、`toDomainOrder`）。批量转换用 `range` 调用单元素函数，不要写双层版本。

### Context 与日志

- 所有跨层、做 IO、可取消的方法，第一个参数必须是 `ctx context.Context`。
- 日志统一用 `log/slog`（标准库），通过 wire 注入 `*slog.Logger`；不在 service 代码里使用包级默认 logger。
- 日志字段用 `slog.String("user_id", id)`，不要拼字符串。
- HTTP 请求 ID（如 `X-Request-Id`）在 gateway 中间件里读取并塞进 ctx；gRPC interceptor 从 metadata 读取同名 key。两侧统一注入 logger 的 with 字段。

### 测试

- `domain/`：纯单测，表驱动。
- `repository/dao/`：对真实 DB 的集成测试（testcontainers 或 docker-compose 启动）。慢的标 `//go:build integration`。
- `repository/`：单测，mock `DAO` 接口，重点验证 dao ↔ domain 的映射与错误转换。
- `service/`：单测，mock `Repository` 接口，验证业务规则与领域错误。
- `grpc/`：单测，mock `service.Service` 接口，验证 proto ↔ domain 字段映射与领域错误 → gRPC code 的翻译。
- mock 工具：手写 fake 或 gomock，**全项目二选一并坚持**。生成的 mock 放在被 mock 接口同包下的 `mocks_test.go`（避免污染生产构建）。
- gateway 不单测：HTTP↔gRPC 翻译由生成代码完成；用端到端测试覆盖（启动 `*App`，用 `net/http` 客户端打真实路由）。
- `cmd/`：冒烟测试，确保 wire 能编译、`main` 能启动。

## 工作流 checklist（每次变更）

当用户要求加功能或加 RPC 时，按以下顺序推进，**不要跳步**：

1. **先写 proto + HTTP 注解。** 修改/新建 `api/proto/<svc>/v1/<svc>.proto`，给每个 RPC 加 `google.api.http`。跑 `buf lint` 再 `buf generate`，确认 `*.pb.gw.go` 与 `*.swagger.json` 一同生成。proto 与所有生成产物同一个 commit。
2. **domain。** 在 `app/<svc>/domain/` 加/改实体和哨兵错误。
3. **dao 接口与实现。** 在 `app/<svc>/repository/dao/types.go` 按需扩展 `DAO` 接口；在 `app/<svc>/repository/dao/<entity>.go` 加 gorm model 与 CRUD 方法（实现 `DAO`），同步写集成测试。dao 内部把 `gorm.ErrRecordNotFound` 等映射为领域错误。
4. **repository 接口与实现。** 在 `app/<svc>/repository/types.go` 按需扩展 `Repository` 接口；在 `app/<svc>/repository/<entity>.go` 实现，通过 `dao.DAO` 接口调用底层，**独立写** `toDomain` / `fromDomain` 转换函数；写 mock DAO 单测。
5. **service 接口扩展。** 在 `app/<svc>/service/types.go` 按本次 RPC 需要扩展 `Service` 接口。
6. **service 实现。** 在 `app/<svc>/service/<svc>.go` 实现 `Service` 接口对应方法（纯业务逻辑，**不构造** gRPC error），写 mock `repository.Repository` 单测。
7. **grpc 实现。** 在 `app/<svc>/grpc/<svc>.go` 实现 `<Svc>ServiceServer` 对应方法：调用 `service.Service`、通过 `toGRPCError` 映射错误；proto ↔ domain 走**独立**的 `toProto` / `fromProto` 转换函数。写 mock `service.Service` 单测。
8. **wire。** 新增 constructor 要在 `app/<svc>/ioc/wire.go` 注册，并显式 `wire.Bind` 三层接口到实现。跑 `go generate ./app/<svc>/cmd/...`。
9. **配置。** 引入新配置项要同时改类型化 `Config`、`config.yaml`、并记录对应环境变量名。
10. **编译与测试。** `go build ./...` 然后 `go test ./app/<svc>/...`，集成测试单独跑。
11. **端到端冒烟。** 启动服务，用 `grpcurl` 验证 gRPC，用 `curl` 验证 HTTP 路径，两侧响应一致。
12. **复核 wire diff。** 检查 `wire_gen.go` 的改动，应当最小且显然正确。

## 新建微服务脚手架

当用户要求"新建 `<svc>` 服务"时，一次性完成以下步骤，再按工作流推进第一个 RPC：

1. 按目录结构创建所有目录，包括 `third_party/googleapis/google/api/`。
2. 创建 `api/proto/<svc>/v1/<svc>.proto`，先放空 `service <Svc>Service {}`，预先 `import "google/api/annotations.proto";`。
3. 确认仓库根有 `buf.yaml` 与 `buf.gen.yaml`，且 `buf.gen.yaml` 包含 `protoc-gen-go`、`protoc-gen-go-grpc`、`protoc-gen-grpc-gateway`、`protoc-gen-openapiv2` 四个插件。
4. 创建 `app/<svc>/domain/<entity>.go`（即使是空 stub）和 `domain/errors.go`。
5. 创建 `app/<svc>/repository/dao/types.go`（`DAO` 接口可以为空）、`repository/dao/<entity>.go`（gorm model + 实现 `DAO`）、`repository/types.go`（`Repository` 接口可以为空）、`repository/<entity>.go`（实现 `Repository`，含 `toDomain` 转换函数）。
6. 创建 `app/<svc>/service/types.go`（`Service` 接口可以为空）与 `service/<svc>.go`（实现 `Service` 接口；**不嵌入** `Unimplemented...Server`，service 是纯业务层）。
7. 创建 `app/<svc>/grpc/<svc>.go`（嵌入 `Unimplemented<Svc>ServiceServer`，构造函数接收 `service.Service` 接口）与 `grpc/errors.go`（`toGRPCError` 工具函数）。grpc 层本身就是 gRPC server 实现，**不再单独定义接口**。
8. 创建 `app/<svc>/ioc/{wire.go,db.go,grpc.go,gateway.go,config.go}`，定义唯一的 `ProviderSet`，包含三层接口的 `wire.Bind`。gateway provider 必须能 in-process 连接到本服务的 gRPC server。
9. 创建 `app/<svc>/cmd/{main.go,wire.go,config.yaml}`。`main.go` 同时启动 gRPC 与 HTTP gateway，监听不同端口。
10. 在 `cmd/wire.go` 加 `//go:generate wire` 指令。
11. 执行 `go generate ./app/<svc>/cmd/...` 生成 `wire_gen.go`。
12. `go build ./app/<svc>/...` 必须通过，再进入下一步。

仓库中第一个跑通的服务即作为后续服务的参考样板 —— 复制其**结构**，不复制其 import。

## 反模式（明确禁止）

- ❌ repository 返回 `*gorm.DB` 或 DAO 结构体。
- ❌ `service/` 里 import `gorm`、`google.golang.org/grpc` 或 `api/gen/`。service 是纯业务层。
- ❌ `grpc/` 里 import `gorm`、`repository/dao` 或 `repository`。grpc 只依赖 `Service` 接口。
- ❌ service 直接返回 `status.Error(...)`。gRPC 状态映射只在 `grpc/errors.go` 发生。
- ❌ grpc adapter 里写业务规则（校验之外的领域判断、跨实体协调等）。业务逻辑只在 service。
- ❌ 在 grpc handler 里直接 new 一个具体 `*service.UserService`。必须通过 `Service` 接口注入。
- ❌ Repository 直接持有 `*dao.UserDAO` 具体类型。必须通过 `dao.DAO` 接口。
- ❌ 接口散落多个文件。位置固定：`service/types.go` 含 `Service`，`repository/types.go` 含 `Repository`，`repository/dao/types.go` 含 `DAO`。
- ❌ 在 `Repository` 实现 / gRPC handler 方法体里写字段拼装（`User{ID: x.ID, Username: x.Username, ...}`）。跨层映射必须放进独立的 `toDomain` / `toProto` / `fromProto` 函数，详见"跨层数据转换"。
- ❌ 在 `grpc/` 下创建 `types.go`/`port.go` 之类的接口文件。grpc 层就是 `<Svc>ServiceServer` 的实现，没有上游需要 mock 它。
- ❌ `main` 之外 `panic`。返回 error，`main` 只在启动失败时 `log.Fatal`。
- ❌ 包装过的错误用 `==` 比较哨兵。用 `errors.Is`。
- ❌ 多个服务共用同一个 `ioc/wire.go`。每个服务一份。
- ❌ 手改 `wire_gen.go` 或 `*.pb.go` / `*.pb.gw.go`。
- ❌ 用 `init()` 做对外可见的事情。组合发生在 `ioc` + `cmd`。
- ❌ `fmt.Println` 或 `log.Printf` 打日志。用注入的 `*slog.Logger`。
- ❌ 业务深处随手 `context.Background()`。必须透传调用方的 ctx。
- ❌ `app/<a>/` 与 `app/<b>/` 互相 import。服务之间只通过 gRPC 通信。
- ❌ 在 gateway 上挂手写的 `http.HandlerFunc` 实现业务逻辑。所有 HTTP 必须经 proto + grpc-gateway。
- ❌ 同一个 RPC 既走 gateway 又额外暴露一个手写 HTTP 路径。一份 proto 一份 HTTP 契约。
- ❌ 在 service 里读 HTTP header / cookie。需要的元数据通过 gRPC metadata 传，gateway 负责 header → metadata 的桥接；grpc adapter 从 metadata 取出后以普通参数传入 service。

## 优化与重构

当代码偏离本 skill 的约定时主动执行优化，**不要等用户提醒**。优化是独立动作，不与新功能混在一个 PR 里。

### 触发条件（命中任一即启动）

- **风格违规**：命名不符 Go 风格、文件位置错误、import 顺序混乱、`gofmt` / `golangci-lint` 报错。
- **分层违规**：跨层 import（如 `service/` import `gorm`、`grpc/` import `repository`）、依赖方向反向。
- **接口缺失或位置错误**：dao/repo/service 实现没有对应接口，或接口不在 `service/types.go` / `repository/types.go` / `repository/dao/types.go`。
- **错误处理违规**：service 构造 `status.Error`、dao 把 `gorm.ErrRecordNotFound` 直接外抛、用 `==` 比较包装过的错误。
- **内联映射**：方法体里散落跨层字段拼装，没有抽到独立的 `toDomain` / `toProto` / `fromProto` 函数。
- **重复代码**：相同的错误映射、相同的字符串处理在三处以上散落（**不含**跨层转换 —— 转换函数无门槛）。
- **未使用代码**：失效的 `Unimplemented...` 方法、不再被调用的 helper、被注释掉的 dead code。
- **测试缺口**：实现层无对应单测，或 mock 与真实接口签名不一致（被改了一边漏掉另一边）。
- **context 滥用**：业务深处出现 `context.Background()` / `context.TODO()`。

### 优化优先级（从高到低）

1. **正确性** —— 分层 / 错误处理 / 依赖方向违规：立刻修。
2. **可测试性** —— 缺失的 `types.go` 接口、无法 mock 的具体依赖：立刻补。
3. **风格一致性** —— 命名、文件结构、import 分组：同 PR 修。
4. **重复消除** —— 抽 helper / 工具函数三处以上重复才抽，避免过度抽象。**例外**：跨层数据转换函数（`toDomain` / `toProto` / `fromProto`）无门槛，调用一次也独立写。

### 操作流程

1. **静态工具先行。** `gofmt -w ./...`、`go vet ./...`、`golangci-lint run` 把工具能发现的问题批量修。
2. **对照反模式 grep 自检。** 高价值检查项：
   - `grep -rn "gorm" app/<svc>/service app/<svc>/grpc`
   - `grep -rn "status.Error\|codes\." app/<svc>/service`
   - `grep -rn "context.Background()\|context.TODO()" app/<svc>` 排除 `main` / `_test.go`
   - `grep -rn "fmt.Println\|log.Printf" app/<svc>`
3. **接口契约自检。** `service/types.go` 与 `repository/types.go` 是否覆盖了所有实现的公开方法；mock 是否同步更新。
4. **跑测试。** `go test ./app/<svc>/...`，集成测试单独跑确认未回归。
5. **独立提交。** `refactor: ...` 开头的 commit，不混入功能改动；wire_gen.go 若被触发变更需一起 commit。

### 禁止

- ❌ 在新功能 PR 里"顺手"重构无关代码 —— 拆开提。
- ❌ 优化时改变外部契约（proto 字段、HTTP 路径、gRPC code、错误消息文案）—— 那是另一类变更。
- ❌ 为"看起来更整洁"引入额外抽象层、interface、generic helper —— 重复未到三处不抽。**例外**：跨层数据转换函数无门槛。
- ❌ 批量重命名跨多个服务 —— 一次只动一个 `app/<svc>/`，便于 review 与回滚。
