# AGENTS.md 

本仓库中 AI 编程代理的行为指南。

# 项目语言规范

- **日常交流**：使用简体中文。
- **代码注释**：使用中文。
- **Git Commit**：使用中文，格式遵循 "feat: 新增功能"。
- **Thinking**： 你在思考问题时思考过程必须使用中文。

## 项目概述

Pivot 是一个 monorepo，顶层目录结构如下：

- `src/` — 核心源代码
- `tests/` — 测试文件，结构与 `src/` 对应
- `frontend/` — Web 前端/应用代码
- `pkgs/ragflow/` — RAG（检索增强生成）工作流包

## 构建 / Lint / 测试命令

> **注意：** 本项目尚处于早期脚手架阶段。以下命令应随工具链的引入及时更新。
> 当添加包管理器或配置文件时，请立即更新本节。

### 通用

- **Python 包管理：** 使用 `uv`。项目已配置 `pyproject.toml`。
- **安装依赖：** `uv sync`
- **添加依赖：** `uv add <package>`
- **添加开发依赖：** `uv add --dev <package>`
- **移除依赖：** `uv remove <package>`
- **运行 Python 脚本：** `uv run python <script>`
- **构建：** 查找 `package.json`、`Makefile` 或 `pyproject.toml` 中的构建脚本。

### 运行测试

- **全部测试：** `uv run pytest`
- **单个测试文件：** `uv run pytest tests/path/to/test_file.py`
- **单个测试用例（按名称）：** `uv run pytest tests/path/to/test_file.py -k "test_name"`

### Lint 与格式化

- 运行已配置的 linter（如 `ruff check .`、`eslint .`、`biome check .`）。
- 提交前运行格式化工具（如 `ruff format .`、`prettier --write .`）。
- 如果存在 `Makefile`，优先使用 `make lint` / `make fmt`。
- 如果尚未配置 linter，**不要**自行引入，需先询问用户。

## 代码风格指南

### 通用原则

- 遵循所编辑文件中已有的惯例。新建文件时，参考相邻文件的风格。
- 优先使用短小、职责单一的函数，而非冗长的逻辑块。
- 避免过早抽象——当重复模式明显时再引入，而非看到两次就抽象。
- 除非用户明确要求，否则**不要**添加注释。代码应通过清晰的命名自文档化。

### 导入（Imports）

- 按以下顺序分组，各组之间用空行分隔：
  1. 标准库
  2. 第三方包
  3. 本地/应用模块
- 尽量使用绝对导入，而非相对导入。
- 不要使用通配符导入（`from module import *`）。
- 提交前移除未使用的导入。

### 格式化

- 与每个文件中已有的格式风格保持一致。
- 默认列宽限制：Python/ruff 88 字符，JS/TS 80–100 字符。
- 缩进因语言而异：Python 4 空格，JS/TS 2 空格。
- 文件末尾保留一个换行符。
- 不允许行末空白。

### 类型

- 如项目使用 TypeScript，优先严格类型——除非确属不可避免，否则避免使用 `any`。
- 如项目使用 Python 类型注解，为所有函数签名添加类型标注。
- TypeScript 中对象形状优先使用 `interface` 而非 `type` 别名。
- 数据不应被修改时，优先使用 `readonly`。

### 命名规范

- **Python：** 函数、方法、变量、模块用 `snake_case`。类用 `PascalCase`。常量用 `UPPER_SNAKE_CASE`。
- **TypeScript/JavaScript：** 函数、方法、变量用 `camelCase`。类、组件、类型、接口用 `PascalCase`。常量用 `UPPER_SNAKE_CASE`。
- **文件命名：**
  - Python：`snake_case.py`
  - TypeScript/JavaScript：工具文件用 `camelCase.ts` / `camelCase.tsx`，React 组件用 `PascalCase.tsx`。
  - 测试文件：`test_*.py` 或 `*_test.py`（Python），`*.test.ts` / `*.spec.ts`（JS/TS）。

### 错误处理

- 优先显式错误处理，而非静默失败。
- 当错误需要区分时，使用自定义错误类型/类。
- 不要静默捕获并吞掉异常——至少要记录日志。
- 异步代码中，使用 async/await 时优先 `try/catch` 而非 `.catch()` 链式调用。

### 测试惯例

- 测试文件位于 `tests/` 目录，结构与 `src/` 目录镜像对应。
- 每个测试文件应对应一个源文件。
- 使用描述性的测试名称，读起来像自然语言句子（如 `test_returns_404_when_resource_not_found`）。
- 优先编写集成风格的测试，测试真实行为，而非重度 mock。
- 仅 mock 外部服务或 I/O；谨慎 mock 内部模块。

## 项目特定说明

### `pkgs/ragflow/`

本包处理 RAG 工作流逻辑。在此目录工作时：

- 保持检索（Retrieval）、增强（Augmentation）和生成（Generation）关注点清晰分离。
- 文档处理和转换管道优先使用纯函数。
- 在 API 边界处验证输入，而非在内部函数中。


## Git 规范

- 提交信息使用祈使语气（如 "add feature"，而非 "added feature"）。
- 保持提交原子性——每次提交一个逻辑变更。
- 不要提交密钥、凭证或 `.env` 文件。
- 除非用户明确要求，否则不要推送。

## 重要提醒

- 编辑前务必先读取文件。
- 创建新文件时，先检查相邻文件的惯例。
- 修改后如已有 lint 和类型检查命令，务必运行。
- 除非用户明确要求，否则不要提交更改。
- 遇到模糊需求时，向用户提问而非猜测。
- 如尚未建立构建/测试工具链，不要自行引入，需先询问用户。
