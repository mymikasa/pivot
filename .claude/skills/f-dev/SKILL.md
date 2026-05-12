---
name: f-dev
description: 用于 frontend/ 下 React 19 + TanStack（Router/Query/Form）+ Vite + Zod + Tailwind v4 + Radix 的开发 —— 新增页面/路由、API 调用、表单、组件、状态、测试、testid 命名。技术栈：vite + tsc + vitest + msw + @hey-api/openapi-ts，事实源在 .claude/guides/frontend/。
---

# Frontend 开发规约入口

技术栈：React 19 · TypeScript 5 · Vite 7 · TanStack Router/Query/Form · Zod 4 · Tailwind v4 · Radix UI · Vitest + Testing Library + MSW · `@hey-api/openapi-ts`。

**本 SKILL.md 是入口**，写决策、硬规则、工作流；具体写法、长例子、命令清单去读 `${CLAUDE_PLUGIN_ROOT}/guides/frontend/*.md`，按需读取。与 `agents/frontend-*.md` 共享同一份事实源。

## 何时适用

- 新增/修改 `frontend/src/` 下的页面、组件、hooks、store、data fetcher。
- 接入新的后端 API（OpenAPI 契约变更后）。
- 写表单、写 Vitest 单测、加 `data-testid`。
- 调路由、改 query options、改 form schema。
- 调试类型检查、构建失败。

任务若完全不涉及 `frontend/`，不要套用本 skill。

## 深入阅读（按触发场景读，不要预先全读）

| 触发场景 | 读 |
|---|---|
| 摸清当前架构事实、目录职责、路由约束 | `${CLAUDE_PLUGIN_ROOT}/guides/frontend/development.md` |
| 写 Query / Router / Form / API / Tailwind | `${CLAUDE_PLUGIN_ROOT}/guides/frontend/patterns.md` |
| 写 Vitest / MSW / 选择器策略 / 异步断言 | `${CLAUDE_PLUGIN_ROOT}/guides/frontend/testing.md` |
| 完成前最低验证命令与门禁 | `${CLAUDE_PLUGIN_ROOT}/guides/frontend/validation.md` |
| 验收门禁、API 一致性、Demo-first 合规 | `${CLAUDE_PLUGIN_ROOT}/guides/frontend/quality.md` |
| `data-testid` 命名与覆盖分级 | `${CLAUDE_PLUGIN_ROOT}/guides/frontend/testid-standards.md` |

入口索引：`${CLAUDE_PLUGIN_ROOT}/guides/frontend/index.md`。

## 当前目录与职责（事实快照）

以 `frontend/src/` 为准；详细见 `guides/frontend/development.md`。

| 路径 | 职责 |
|---|---|
| `routes/` | 文件路由入口，真相在 `routeTree.gen.ts` |
| `components/` | 页面组件、共享 UI、业务组件 |
| `data/` | 查询参数、`queryOptions`、API mutation hooks |
| `hooks/` | 页面状态与复用逻辑 |
| `lib/` | 工具函数、`request.ts`、`api-generated/`（派生物） |
| `stores/` | 全局状态（轻量，少用） |
| `test/` | Vitest setup + MSW mocks |

## 核心硬规则

不读 references 也得记住这 10 条：

1. **API 优先复用生成代码**：从 `frontend/src/lib/api-generated/` 调；不要手写一份 fetch wrapper。OpenAPI 契约变了**先**跑 `npm run generate-api` 再继续写页面。
2. **响应统一过 `handleApiResponse`**：从 axios/生成客户端拿到的 response 不要直接 `.data`，走 `lib/api-utils` 的 helper。
3. **服务端状态走 TanStack Query**：复用现有 `queryKey` 组织、把可复用查询抽成 `queryOptions`；mutation 完成默认 `invalidateQueries`，**不要**默认做 optimistic update。
4. **表单一律 `useAppForm`**：禁用裸 `useForm`；验证用 Zod schema；错误展示用 `getFieldErrorMessage`；提交走 `onSubmit` 回调或 `form.handleSubmit()`。**零 `any`、零不安全断言**。
5. **路由真相在 `routes/` + `routeTree.gen.ts`**：不要把旧模板的租户前缀路径当作默认事实；列表页搜索参数走 `validateSearch`（Zod）。
6. **样式优先复用 `components/ui/` 与现有 utility 组合**：不要为单页平行造一套 token / theme；Tailwind v4 主题定制集中在统一样式入口。
7. **P0/P1/P2 元素必须带 `data-testid`**：命名 `[entity]-[action]-[type]`，kebab-case，页面内唯一。装饰元素（P4）**不要**加 testid。
8. **测试用户可观察行为，不测第三方库实现**：选择器优先 `getByRole` > `getByLabelText` > `getByText` > `getByTestId`；异步用 `findBy*` / `waitFor`，不用 `setTimeout`。
9. **不在 Vitest 里跑页面级 happy-path**：那是 Demo 的事；Vitest 只覆盖 hook / 纯函数 / schema / 内部状态机 / Demo 难稳定覆盖的边界。
10. **完成前必跑** `npm run type-check` 和 `npm run build`（两者都过才算完）。类型错误**不能**留到下一个任务。

## 工作流 checklist（新增页面 / 改 API）

1. **API 契约变更**（如果有）：跑 `npm run generate-api` 同步 `api-generated/`，并 commit 生成产物。
2. **`data/` 层**：抽 `queryOptions` 或 mutation hook；走 `handleApiResponse`。
3. **路由**：新页面放 `routes/`，搜索参数用 Zod `validateSearch`；不绕过文件路由。
4. **组件**：优先复用 `components/ui/`；表单走 `useAppForm` + Zod schema。
5. **testid**：可交互元素（按钮、输入、下拉）必须加；命名按 `guides/frontend/testid-standards.md`。
6. **测试**：
   - 页面 happy-path → Demo（**不**写同路径 Vitest）
   - 纯逻辑 / 异常分支 → Vitest + MSW
   - mock handler 用 `server.use(...)` 覆盖，**不**改全局 handler
7. **完成前最小验证**（在 `frontend/`）：
   ```bash
   npm run type-check
   npm run build
   ```
   失败修到通过，**最多 3 轮**；3 轮还过不了停下来诊断根因。

## 反模式（明确禁止）

- ❌ 手写 API 请求绕过 `api-generated/`。
- ❌ 表单用 `useForm` 而不是 `useAppForm`；用 `any` 或 `as FormData` 强转。
- ❌ 在 Vitest 里请求真实后端 API，或测页面完整 happy-path（那是 Demo 范围）。
- ❌ 用脆弱选择器（DOM 层级、纯样式类名、CSS-in-JS hash 类名）。
- ❌ 用 `setTimeout` 等异步，正式测试改成 `findBy*` / `waitFor`。
- ❌ 把 `frontend/src/test/test-utils.tsx` 当全局标准 wrapper —— 现状是按需在测试文件内创建最小 wrapper。
- ❌ 改全局 MSW handler 来覆盖单测；用 `server.use(...)` 局部覆盖。
- ❌ 给装饰元素（图标、分隔线）加 `data-testid`。
- ❌ 重复造样式 token / theme —— Tailwind v4 主题集中在统一样式入口。
- ❌ 提交"类型检查有错误"的任务为完成 —— 类型必须 0 errors。
- ❌ 把旧模板里的租户前缀路径作为默认路由约定。

## 完成门禁

P0（必须通过，缺一不可）：

- `npm run type-check` —— **0 errors**
- `npm run build` —— 通过
- `npm run test:run` —— 现有用例通过（如果改了被覆盖的代码）
- API 一致性 —— 路径、方法、关键参数、关键响应与后端对得上

P1（应通过）：

- `npm run lint` —— 无阻塞错误
- 表单零 `any`、零不安全断言

详细门禁定义、报告字段、API 一致性导出方式见 `guides/frontend/quality.md`。

## 与 backend-dev / m-jwt 的协作

- 后端 API 契约改动（proto 加字段、改 HTTP path）：先后端跑 `buf generate`，再前端 `npm run generate-api`，**同一个 PR 提**两边生成产物。
- JWT token 存取：access/refresh 走 `stores/auth.ts` 的 helper；axios interceptor 自动加 `Authorization: Bearer`；refresh 流程参见 m-jwt skill 的 refresh 约定。
- 字段命名：后端默认 snake_case JSON（grpc-gateway `UseProtoNames`），前端类型一律 snake_case；`int64` 序列化为 `string`，TypeScript 类型用 `string`。
