# Function Calling Demo 设计

## 概述

实现一个基于 OpenAI 兼容协议的 Function Calling demo，让 LLM 能够调用项目中已有的知识库搜索能力回答用户问题。

## 技术方案

- 使用 `openai` Python SDK，兼容国内模型（DeepSeek、通义千问、智谱 GLM 等）
- 注册一个工具 `search_knowledge_base`，内部调用 `src.pipeline.search.search_chunks()`
- 采用多轮对话模式，LLM 自主决定是否调用搜索工具

## 架构

```
用户输入 → OpenAI SDK → LLM
                         ↓ tool_call: search_knowledge_base
                    search_chunks()
                         ↓ 搜索结果
                    OpenAI SDK → LLM 生成最终回答
                         ↓
                    输出给用户
```

## 工具定义

`search_knowledge_base`：
- `query`（string）：搜索关键词
- `kb_id`（integer）：知识库 ID
- `top_k`（integer，默认 5）：返回结果数

## 配置

在 `config.yaml` 新增 `llm` 配置节：
- `api_key`：LLM API Key
- `api_base`：API Base URL
- `model`：模型名称（如 `deepseek-chat`）

在 `Settings` 中对应新增字段。

## 阶段一：命令行脚本

文件：`src/demo_function_calling.py`

功能：
- 循环读取用户输入
- 多轮对话支持（保留 message history）
- 打印 tool_call 决策过程和最终回答
- 命令行参数接受 `--kb-id`

## 阶段二：FastAPI 端点

新增 `POST /api/chat`：
- 接收 `message`、`kb_id`、可选 `history`
- 返回 LLM 回答 + 引用的搜索结果

## 依赖

新增 `openai` 包。
