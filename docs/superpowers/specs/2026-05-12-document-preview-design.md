# 文档预览功能设计文档

## 概述

为知识库文档增加预览功能，支持文本类文件（TXT/MD/CSV/JSON）、PDF 和图片（JPG/PNG/GIF 等），其他类型提示不支持。预览在新页面中展示，PDF 用原生 iframe 渲染。

## 范围

| 项目 | 决策 |
|---|---|
| 支持文件类型 | 文本类 + PDF + 图片，其他类型提示"暂不支持预览" |
| 交互方式 | 新页面 `/kb/$kbId/docs/$docId` |
| PDF 渲染 | 原生 iframe（data URL） |
| 后端改动 | 无，复用 `DownloadDocumentSimple` 端点 |
| 新增依赖 | 无 |

## 数据流

```
预览页加载 → queryOptions 调用 DownloadDocumentSimple → 返回 {filename, content_type, data(base64)}
→ 根据 content_type 选择渲染方式 → 渲染预览内容
```

## 文件类型与渲染

| content_type 分类 | 匹配规则 | 渲染方式 |
|---|---|---|
| 文本 | `text/*`、`application/json` | base64 解码 → `<pre>` 代码块 |
| PDF | `application/pdf` | `data:application/pdf;base64,...` → `<iframe>` |
| 图片 | `image/*` | `data:{type};base64,...` → `<img>` |
| 其他 | 不在上述范围 | 显示"暂不支持预览"+ 下载按钮 |

## 前端改动

### 新增文件

`src/routes/_authenticated/kb/$kbId.$docId.tsx` — 预览页面

- 顶部：返回按钮（回到 `/kb/$kbId`）+ 文件名 + 下载按钮
- 中部：根据 content_type 渲染预览内容
- 状态：loading spinner → 预览内容 / 错误提示 / 不支持提示

### 修改文件

| 文件 | 改动 |
|---|---|
| `src/data/kb.ts` | 新增 `documentPreviewOptions(kbId, docId)` |
| `src/routes/_authenticated/kb/$kbId.tsx` | 文档表格文件名列加 `<Link>` 指向预览页 |
| `src/routeTree.gen.ts` | 自动重新生成 |

### 预览页布局

```
┌──────────────────────────────────────────────┐
│ ← 返回    hello.txt                [下载]    │
├──────────────────────────────────────────────┤
│                                              │
│  Hello World                                 │
│  This is a test document.                    │
│  ...                                         │
│                                              │
└──────────────────────────────────────────────┘
```

## 错误处理

| 场景 | 处理 |
|---|---|
| 文档不存在 | 显示错误提示，提供返回按钮 |
| 文档还在上传中（status=uploading） | 显示"文档上传中，请稍后重试" |
| 不支持的文件类型 | 显示"暂不支持该文件类型预览"+ 下载按钮 |
| base64 数据过大导致渲染卡顿 | PDF/图片超过一定大小时提示"文件较大，建议下载查看" |
