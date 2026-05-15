# JoJo Personal Assistant — 实现路线图

> 从零搭建一个可扩展的个人 AI Agent，分 8 个阶段、47 个任务，
> 从最基础的目录结构到最终的 Skill + MCP + 定时任务全能力。

---

## 进度说明

| 图标 | 含义 |
|------|------|
| ⬜ | 未开始 |
| 🟡 | 进行中 |
| 🟢 | 已完成 |
| 🔴 | 阻塞中 |
| ⏭️ | 跳过（本期不做） |

---

## 阶段一：项目基础 (Foundation)

> 目标：搭好骨架，能启动、能配置、能打日志。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| F-01 | 创建项目目录结构 | 🟢 | 15min | — | 完整目录树 |
| F-02 | 初始化 Python 项目 (pyproject.toml) | 🟢 | 15min | F-01 | pyproject.toml |
| F-03 | 安装依赖并锁定版本 | 🟢 | 10min | F-02 | requirements.txt / uv.lock |
| F-04 | 实现配置管理 config.py | 🟢 | 30min | F-01 | src/jojo/config.py |
| F-05 | 实现日志系统 logger.py | 🟢 | 20min | F-01 | src/jojo/logger.py |
| F-06 | 实现核心数据模型 models.py | 🟢 | 40min | F-01 | src/jojo/models.py |
| F-07 | 实现 CLI 入口 cli.py (argparse 版) | 🟢 | 30min | F-04,F-05 | src/jojo/cli.py |
| F-08 | 编写第一个启动脚本 run.py | 🟢 | 10min | F-07 | run.py |
| F-09 | 验证：项目能启动并打印配置信息 | 🟢 | 10min | F-08 | — |

**阶段一完成标志**: `python run.py` → 打印配置和 "JoJo Agent initialized."

### 🧑 用户验证清单（阶段一）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | 目录结构完整 | `ls -R src/jojo/` | 看到 config.py, logger.py, models.py, cli.py 等文件 |
| 2 | 依赖安装正确 | `pip list \| grep -E "litellm\|pydantic\|loguru"` | 显示已安装的包及版本 |
| 3 | 配置可加载 | `python -c "from src.jojo.config import config; print(config)"` | 打印配置字典，无报错 |
| 4 | 日志可输出 | `python -c "from src.jojo.logger import logger; logger.info('test')"` | 控制台看到格式化日志 |
| 5 | CLI 可启动 | `python run.py --help` | 显示帮助信息，列出可用命令 |

### 📁 阶段一产出文件树

```
jojo_personal_assistant/
├── pyproject.toml              # 项目配置 + 依赖声明
├── config.yaml                 # 用户配置文件
├── .env.example                # 环境变量模板
├── run.py                      # 启动脚本
├── main.py                     # (预存，空文件)
├── src/
│   └── jojo/
│       ├── __init__.py         # 包标记
│       ├── config.py           # 配置管理 (YAML + ENV → Pydantic)
│       ├── logger.py           # 日志系统 (loguru, 控制台+文件)
│       ├── models.py           # 核心数据模型 (Message/ToolDefinition/AgentConfig/Session)
│       └── cli.py              # CLI 入口 (argparse, version/config 子命令)
├── tests/
│   └── __init__.py
├── skills/
│   └── .gitkeep
├── data/
│   ├── .gitkeep
│   └── jojo.log                # 运行日志
└── docs/
    ├── agent-framework-guide.md
    └── implementation-roadmap.md
```

---

## 阶段二：LLM 适配层 (LLM Adapter)

> 目标：统一调用 LLM，一行代码切换模型。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| LLM-01 | 实现 LLMProvider (同步版) | 🟢 | 40min | F-06 | src/jojo/llm/provider.py |
| LLM-02 | 实现 LLMProvider (流式版) | 🟢 | 30min | LLM-01 | src/jojo/llm/provider.py |
| LLM-03 | 实现 Token 用量统计 | 🟢 | 20min | LLM-01 | src/jojo/llm/usage.py |
| LLM-04 | 编写 LLM 层单元测试 | 🟢 | 30min | LLM-02 | tests/test_llm.py |
| LLM-05 | 验证：用 curl 风格测试多种模型 | 🟢 | 15min | LLM-02 | — |

**阶段二完成标志**: 能调用至少 2 个不同厂商的模型并获得回复。

### 🧑 用户验证清单（阶段二）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | 同步调用正常 | `python -c "from src.jojo.llm import LLMProvider; p=LLMProvider('openai/gpt-4o-mini'); print(p.chat([{'role':'user','content':'hi'}]))"` | 返回 LLM 回复文本 |
| 2 | 流式调用正常 | 运行流式测试脚本 | 看到逐字输出的打字机效果 |
| 3 | 模型切换正常 | 将 model 改为 `anthropic/claude-haiku-4-5` 再跑一次 | 另一个模型也正常回复 |
| 4 | Token 统计准确 | 调用后查看 usage 对象 | 显示 prompt_tokens / completion_tokens |
| 5 | 单元测试通过 | `pytest tests/test_llm.py -v` | 全部 PASSED |

### 📁 阶段二新增文件树

```
src/jojo/llm/
├── __init__.py           # 导出 LLMProvider, UsageTracker
├── provider.py           # chat() / stream() / chat_with_tools()
└── usage.py              # Token 用量跟踪 + 按模型汇总
tests/
└── test_llm.py            # 10 测试 (5 UsageTracker + 5 API-skips)

项目完整树:
jojo_personal_assistant/
├── pyproject.toml
├── config.yaml
├── .env                   # DeepSeek API Key
├── .env.example
├── run.py
├── main.py
├── src/jojo/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── models.py
│   ├── cli.py
│   └── llm/
│       ├── __init__.py
│       ├── provider.py
│       └── usage.py
├── tests/
│   ├── __init__.py
│   └── test_llm.py
├── skills/.gitkeep
├── data/
│   ├── .gitkeep
│   └── jojo.log
└── docs/
    ├── agent-framework-guide.md
    └── implementation-roadmap.md
```

---

## 阶段三：工具系统 (Tool System)

> 目标：Agent 的手和脚，能搜索、读文件、执行代码。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| TOOL-01 | 实现 Tool 基类和装饰器 @tool | 🟢 | 30min | F-06 | src/jojo/tools/base.py |
| TOOL-02 | 实现 ToolRegistry 注册中心 | 🟢 | 25min | TOOL-01 | src/jojo/tools/registry.py |
| TOOL-03 | 实现 JSON Schema 自动生成 | 🟢 | 30min | TOOL-01 | src/jojo/tools/schema.py |
| TOOL-04 | 实现内置工具：web_search | 🟢 | 30min | TOOL-02 | src/jojo/tools/builtin/search.py |
| TOOL-05 | 实现内置工具：read_file / write_file | 🟢 | 25min | TOOL-02 | src/jojo/tools/builtin/files.py |
| TOOL-06 | 实现内置工具：execute_python (沙箱) | 🟢 | 40min | TOOL-02 | src/jojo/tools/builtin/python.py |
| TOOL-07 | 编写工具系统单元测试 | 🟢 | 35min | TOOL-04 | tests/test_tools.py |
| TOOL-08 | 验证：注册 3 个工具并检查 Schema 生成 | 🟢 | 15min | TOOL-03 | — |

**阶段三完成标志**: 3 个以上可用的内置工具，LLM 能正确调用。

### 🧑 用户验证清单（阶段三）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | 工具注册正常 | `python -c "from src.jojo.tools.registry import registry; print(registry.list_tools())"` | 列出所有已注册工具的名称和描述 |
| 2 | Schema 生成正确 | 选一个工具，打印其 JSON Schema | 参数类型、必填项、描述完整 |
| 3 | web_search 可调用 | `python -c "from src.jojo.tools.builtin.search import web_search; import asyncio; print(asyncio.run(web_search('Python')))"` | 返回搜索结果列表 |
| 4 | 文件读写正常 | 写一个测试文件再读回来 | 内容一致，无乱码 |
| 5 | Python 沙箱安全 | 执行 `print(1+1)` 和 `import os` | 前者返回 2，后者被拦截 |
| 6 | 单元测试通过 | `pytest tests/test_tools.py -v` | 全部 PASSED |

### 📁 阶段三新增文件树

```
src/jojo/tools/
├── __init__.py             # 聚合导出 + 自动注册 5 个内置工具
├── base.py                 # Tool 类 + @tool 装饰器
├── schema.py               # 函数签名 → JSON Schema 自动生成
├── sandbox.py              # 工作目录沙箱 + 危险代码检测
├── registry.py             # ToolRegistry 单例
└── builtin/
    ├── __init__.py
    ├── search.py            # web_search (DuckDuckGo, 无需 API Key)
    ├── files.py             # read_file / write_file / list_files
    └── python.py            # execute_python (安全沙箱)
tests/
└── test_tools.py            # 25 个测试 (全通过)

项目累计树:
jojo_personal_assistant/
├── pyproject.toml
├── config.yaml              # +workspace_root / allowed_dirs
├── .env
├── .env.example
├── run.py
├── src/jojo/
│   ├── __init__.py
│   ├── config.py            # +workspace_root / allowed_dirs
│   ├── logger.py
│   ├── models.py
│   ├── cli.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   └── usage.py
│   └── tools/               # ← 新增
│       ├── __init__.py
│       ├── base.py
│       ├── schema.py
│       ├── sandbox.py
│       ├── registry.py
│       └── builtin/
│           ├── __init__.py
│           ├── search.py
│           ├── files.py
│           └── python.py
├── tests/
│   ├── __init__.py
│   ├── test_llm.py
│   └── test_tools.py        # ← 新增
├── skills/.gitkeep
├── data/
│   ├── .gitkeep
│   └── jojo.log
└── docs/
    ├── agent-framework-guide.md
    └── implementation-roadmap.md
```

---

## 阶段四：单 Agent 核心循环 (Core Agent Loop)

> 目标：实现 ReAct 循环，这是整个框架的心脏。内置人工审批机制。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| AGT-01 | 给 Tool 增加风险等级 (risk: read/write/dangerous) | 🟢 | 15min | TOOL-01 | src/jojo/tools/base.py |
| AGT-02 | 实现人工审批回调 Hook | 🟢 | 30min | AGT-01 | src/jojo/agent/approval.py |
| AGT-03 | 实现 ReAct 循环引擎 (含审批拦截) | 🟢 | 60min | LLM-02, TOOL-02, AGT-02 | src/jojo/agent/react_loop.py |
| AGT-04 | 实现 System Prompt 构建器 | 🟢 | 25min | AGT-03 | src/jojo/agent/prompt.py |
| AGT-05 | 实现终止条件检测 | 🟢 | 20min | AGT-03 | src/jojo/agent/guard.py |
| AGT-06 | 实现 Agent 配置类 (内嵌于 Agent.__init__) | 🟢 | 20min | AGT-03 | src/jojo/agent/react_loop.py |
| AGT-07 | CLI 接入 Agent 对话模式 (含审批交互) | 🟢 | 30min | AGT-03, F-07 | src/jojo/cli.py |
| AGT-08 | 编写 Agent 核心循环单元测试 | 🟢 | 40min | AGT-03 | tests/test_agent.py |
| AGT-09 | 验证：对话 10 轮，Agent 调工具 + 审批生效 | 🟢 | 20min | AGT-07 | — |

**阶段四完成标志**: `python run.py chat` → 对话模式，Agent 调工具时弹出审批，用户可控。

### 🧑 用户验证清单（阶段四）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | 对话模式启动 | `python run.py chat` | 进入交互式对话界面 |
| 2 | 简单问答 | 输入 "你好" | Agent 回复，不触发审批 |
| 3 | 只读工具自动放行 | 输入 "搜索 Python" | web_search 自动执行，不需要审批 |
| 4 | 写入工具触发审批 | 输入 "新建 readme.md" | Agent 暂停，弹出 `[?] Agent 想执行 write_file(...)` 审批提示 |
| 5 | 审批通过 | 按 Y | 工具执行，Agent 继续 |
| 6 | 审批拒绝 | 按 n | 工具跳过，Agent 重新思考 |
| 7 | 本次会话全放行 | 按 a | 后续同类工具不再询问 |
| 8 | 终止条件 | 死循环场景 | Agent 在最大迭代后优雅终止 |
| 9 | 单元测试通过 | `pytest tests/test_agent.py -v` | 全部 PASSED |

### 📁 阶段四新增文件树

```
src/jojo/agent/
├── __init__.py             # 导出 Agent, ApprovalHandler, LoopGuard
├── react_loop.py           # ReAct 循环引擎 (含审批拦截)
├── approval.py             # 人工审批 Hook (read/write/dangerous 三级)
├── prompt.py               # System Prompt 构建器
└── guard.py                # 终止条件检测 (迭代/超时/重复)
src/jojo/tools/base.py      # +risk 字段 (RiskLevel + @tool risk=)
src/jojo/tools/builtin/*    # 所有内置工具标注 risk 等级
src/jojo/cli.py             # +chat 命令 (+ /verbose /allowall /help)
tests/
└── test_agent.py            # 20 测试 (LoopGuard/Approval/Risk/Integration)

项目累计树:
jojo_personal_assistant/
├── pyproject.toml
├── config.yaml
├── .env
├── .env.example
├── run.py
├── src/jojo/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── models.py
│   ├── cli.py               # chat/version/config 三命令
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   └── usage.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py           # +risk 等级
│   │   ├── schema.py
│   │   ├── sandbox.py
│   │   ├── registry.py
│   │   └── builtin/
│   │       ├── __init__.py
│   │       ├── search.py     # risk=read
│   │       ├── files.py      # risk=read/write
│   │       └── python.py     # risk=dangerous
│   └── agent/                # ← 新增
│       ├── __init__.py
│       ├── react_loop.py
│       ├── approval.py
│       ├── prompt.py
│       └── guard.py
├── tests/
│   ├── __init__.py
│   ├── test_llm.py
│   ├── test_tools.py
│   └── test_agent.py         # ← 新增
├── skills/.gitkeep
├── data/
└── docs/
```

---

## 阶段五：记忆系统 (Memory System)

> 目标：Agent 能记住上下文，跨轮次保持连贯。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| MEM-01 | 实现 WorkingMemory (消息历史) | 🟢 | 25min | F-06 | src/jojo/memory/working.py |
| MEM-02 | 实现 ShortTermMemory (会话摘要) | 🟢 | 35min | MEM-01 | src/jojo/memory/short_term.py |
| MEM-03 | 实现 LongTermMemory — SQLite + ChromaDB | 🟢 | 45min | MEM-01 | src/jojo/memory/long_term.py |
| MEM-03a | 实现记忆遗忘曲线 (decay_score) | 🟢 | 30min | MEM-03 | src/jojo/memory/decay.py |
| MEM-04 | 实现 记忆管理器 MemoryManager | 🟢 | 30min | MEM-01,02,03 | src/jojo/memory/manager.py |
| MEM-05 | Agent 接入记忆系统 | 🟢 | 30min | MEM-04, AGT-01 | src/jojo/agent/react_loop.py |
| MEM-06 | 编写记忆系统单元测试 | 🟢 | 40min | MEM-04 | tests/test_memory.py |
| MEM-07 | 验证：跨轮次对话，Agent 记住上文 | 🟢 | 15min | MEM-05 | — |

> **MEM-03a 记忆遗忘曲线设计**:
> ```
> decay_score = time_decay(0.4) + access_boost(0.3) + importance(0.3)
>
> 规则:
>  - time_decay:   半衰期 7 天，30 天未访问 → 自动淘汰
>  - access_boost: 每次被检索命中 → 衰减重置 +20%
>  - importance:   LLM 标记 high/medium/low，high 衰减慢 3 倍
>
> 检索时 decay_score < 0.1 的记忆跳过
> 清理时 decay_score < 0.05 的记忆永久删除
> ```

**阶段五完成标志**: 用户说 "还记得我之前说的吗" → Agent 能正确回忆。不重要的记忆随时间自动淘汰。

### 🧑 用户验证清单（阶段五）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | 短期记忆 | 对话中告诉 Agent 你的名字，下一轮问 "我叫什么？" | Agent 正确说出你的名字 |
| 2 | 工作记忆 | 连续对话 20 轮，问第 5 轮提到的细节 | Agent 能回忆起来（未被压缩前） |
| 3 | 记忆压缩 | 对话超过阈值后，检查是否生成了摘要 | 日志中看到 "memory compressed" 字样 |
| 4 | 长期记忆 | 结束会话后重新启动，问之前讨论过的内容 | Agent 从 SQLite 中检索到相关记忆 |
| 5 | 记忆检索 | 问一个模糊问题，观察检索到的记忆是否相关 | 检索结果与问题语义相关 |
| 6 | SQLite 数据检查 | `sqlite3 data/memory.db "SELECT * FROM memories LIMIT 5;"` | 看到结构化的记忆记录，含 decay_score 字段 |
| 7 | 遗忘曲线生效 | 查看低重要性旧记忆的 decay_score | decay_score < 0.1 的记忆被检索跳过 |
| 8 | 单元测试通过 | `pytest tests/test_memory.py -v` | 全部 PASSED |

### 📁 阶段五新增文件树

```
src/jojo/memory/
├── __init__.py             # 导出全部记忆模块
├── working.py              # L1 工作记忆 (消息历史, 容量阈值)
├── short_term.py           # L2 短期记忆 (LLM 摘要, TTL 过期)
├── long_term.py            # L3 长期记忆 (SQLite + ChromaDB 双存储)
├── decay.py                # 遗忘曲线 (三因子衰减: 时间+访问+重要性)
└── manager.py              # MemoryManager 统一调度三层记忆
src/jojo/agent/react_loop.py  # +MemoryManager 集成 (检索→注入→压缩)
tests/
└── test_memory.py            # 22 测试 (全通过)
data/
├── memory.db                 # SQLite 长期记忆数据库
└── chroma/                   # ChromaDB 向量检索引擎

项目累计树:
jojo_personal_assistant/
├── pyproject.toml
├── config.yaml
├── .env
├── README.md
├── run.py
├── src/jojo/
│   ├── config.py
│   ├── logger.py
│   ├── models.py
│   ├── cli.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py
│   │   └── usage.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── schema.py
│   │   ├── sandbox.py
│   │   ├── registry.py
│   │   └── builtin/
│   │       ├── search.py
│   │       ├── files.py
│   │       └── python.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── react_loop.py      # +记忆集成
│   │   ├── approval.py
│   │   ├── prompt.py
│   │   └── guard.py
│   └── memory/                # ← 新增
│       ├── __init__.py
│       ├── working.py
│       ├── short_term.py
│       ├── long_term.py
│       ├── decay.py
│       └── manager.py
├── tests/
│   ├── test_llm.py
│   ├── test_tools.py
│   ├── test_agent.py
│   └── test_memory.py         # ← 新增
├── data/
│   ├── memory.db              # ← 新增
│   └── chroma/                # ← 新增
├── skills/
└── docs/
```

---

## 阶段六：多 Agent 协作 (Multi-Agent)

> 目标：多个 Agent 分工协作，Orchestrator 统一调度。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| MULT-01 | 实现 AgentRegistry + TaskClassifier (复杂度分类) | 🟢 | 40min | AGT-04 | src/jojo/orchestrator/registry.py, classifier.py |
| MULT-02 | 实现自动模型选择 (simple→Flash, complex→Pro) | 🟢 | 20min | MULT-01 | src/jojo/orchestrator/classifier.py |
| MULT-03 | 实现 Orchestrator：自动路由 + Router | 🟢 | 35min | MULT-01 | src/jojo/orchestrator/router.py, modes.py |
| MULT-04 | 实现 Orchestrator：顺序模式 (流水线) | 🟢 | 30min | MULT-03 | src/jojo/orchestrator/modes.py |
| MULT-05 | 实现 Orchestrator：并行模式 (asyncio.gather) | 🟢 | 40min | MULT-03 | src/jojo/orchestrator/modes.py |
| MULT-06 | 实现预置 Agent：Researcher (Flash) + Coder (Pro) | 🟢 | 30min | MULT-01 | src/jojo/agents/researcher.py, coder.py |
| MULT-07 | CLI orchestrate 命令 + chat 自动路由 | 🟢 | 35min | MULT-03 | src/jojo/cli.py |
| MULT-08 | 编写多 Agent 单元测试 | 🟢 | 35min | MULT-03 | tests/test_multi_agent.py |
| MULT-09 | 验证：自动路由 + 顺序 + 并行 + CLI | 🟢 | 20min | MULT-07 | — |

**阶段六完成标志**: `python run.py chat` → 自动路由，Researcher 搜资料 → Coder 写代码。

### 🧑 用户验证清单（阶段六）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | Agent 列表 | `python run.py agent list` | 列出 researcher + coder |
| 2 | 对话自动路由 | `python run.py chat` → 输入"搜索 Python"和"写个排序" | 简单任务直接回，中等/复杂自动路由 |
| 3 | 顺序模式 | `python run.py orchestrate --mode sequential --task "..." --agents researcher,coder` | Researcher → Coder 流水线 |
| 4 | 并行模式 | `python run.py orchestrate --mode parallel --task "查A;查B;查C"` | 多实例同时搜索，结果汇总 |
| 5 | 模型自动选择 | 输入简单 vs 复杂任务 | 简单→Flash，复杂→Pro |
| 6 | 单元测试通过 | `pytest tests/test_multi_agent.py -v` | 全部 PASSED |

### 📁 阶段六新增文件树

```
src/jojo/orchestrator/
├── __init__.py             # 导出 Orchestrator, Registry, Classifier, Router
├── registry.py             # AgentRegistry 注册中心
├── classifier.py           # 任务复杂度分类器 (Flash 判断 → 自动选模型)
├── router.py               # LLM 路由 (自动选最合适的 Agent)
└── modes.py                # Orchestrator: auto / sequential / parallel
src/jojo/agents/
├── __init__.py
├── researcher.py           # Researcher Agent (Flash, 搜索+查阅)
└── coder.py                # Coder Agent (Pro, 写代码+执行+文件)
src/jojo/cli.py             # +orchestrate / +agent list / chat 升级为自动路由
src/jojo/config.py          # +OrchestratorConfig
config.yaml                 # +orchestrator 配置段
tests/
└── test_multi_agent.py      # 12 测试 (注册/分类/Agent创建)

项目累计树:
jojo_personal_assistant/
├── pyproject.toml
├── config.yaml              # +orchestrator 段
├── .env
├── README.md
├── run.py
├── src/jojo/
│   ├── config.py            # +OrchestratorConfig
│   ├── logger.py
│   ├── models.py
│   ├── cli.py               # +orchestrate / agent / chat 升级
│   ├── llm/
│   ├── tools/
│   ├── agent/
│   ├── memory/
│   ├── orchestrator/        # ← 新增
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── classifier.py
│   │   ├── router.py
│   │   └── modes.py
│   └── agents/              # ← 新增
│       ├── __init__.py
│       ├── researcher.py
│       └── coder.py
├── tests/
│   ├── test_llm.py
│   ├── test_tools.py
│   ├── test_agent.py
│   ├── test_memory.py
│   └── test_multi_agent.py  # ← 新增
├── data/
├── skills/
└── docs/
```

---

## 阶段七：Skill 技能系统 (Skill System)

> 目标：Agent 拥有可复用的能力包，Markdown 定义，自动匹配。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| SKL-01 | 实现 Skill 数据模型 | 🟢 | 20min | F-06 | src/jojo/skills/models.py |
| SKL-02 | 实现 SkillLoader (解析 Markdown + Frontmatter) | 🟢 | 35min | SKL-01 | src/jojo/skills/loader.py |
| SKL-03 | 实现 SkillRegistry (匹配/发现) | 🟢 | 30min | SKL-02 | src/jojo/skills/registry.py |
| SKL-04 | 编写第一个 Skill：code-review | 🟢 | 30min | SKL-02 | skills/code/code-review.md |
| SKL-05 | 编写第二个 Skill：daily-summary | 🟢 | 20min | SKL-02 | skills/productivity/daily-summary.md |
| SKL-06 | Agent 接入 Skill 系统 (直接集成到 react_loop) | 🟢 | 25min | SKL-03, AGT-01 | src/jojo/agent/react_loop.py |
| SKL-07 | 编写 Skill 系统单元测试 | 🟢 | 30min | SKL-03 | tests/test_skills.py |
| SKL-08 | 验证：Skill 自动匹配并注入 System Prompt | 🟢 | 15min | SKL-06 | — |

**阶段七完成标志**: `python run.py skill list` → 2 个 Skill；对话说 "review my code" → 自动匹配 code-review。

### 🧑 用户验证清单（阶段七）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | Skill 加载 | `python run.py skill list` | 列出 code-review + daily-summary |
| 2 | 关键词匹配 | `python run.py chat` → 输入 "帮我 review 这段代码" | 路由信息显示 `skills: code-review` |
| 3 | Skill 执行 | 提供一段有问题的代码 | Agent 按 Skill 定义的步骤审查 |
| 4 | 单元测试通过 | `pytest tests/test_skills.py -v` | 全部 PASSED |

### 📁 阶段七新增文件树

```
src/jojo/skills/
├── __init__.py             # 导出 Skill, SkillLoader, SkillRegistry
├── models.py               # Skill 数据模型
├── loader.py               # Markdown + YAML Frontmatter 解析器
└── registry.py             # SkillRegistry (关键词加权匹配)
skills/
├── code/
│   └── code-review.md      # 代码审查 Skill (4 步流程)
└── productivity/
    └── daily-summary.md    # 日报总结 Skill (5 步流程)
src/jojo/agent/react_loop.py  # +Skill 自动匹配注入
src/jojo/cli.py               # +skill list 命令 + 路由信息含 skills
tests/
└── test_skills.py            # 16 测试 (模型/加载/匹配/全局)
```

---

## 阶段八：MCP 协议集成 (MCP Integration)

> 目标：通过标准 MCP 协议连接外部工具和数据源。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| MCP-01 | 实现 MCPServerConfig 配置模型 | 🟢 | 15min | F-06 | src/jojo/mcp/config.py |
| MCP-02 | 实现 MCPClient (stdio + HTTP 双传输) | 🟢 | 60min | MCP-01 | src/jojo/mcp/client.py |
| MCP-03 | 实现 MCP 工具 → Agent Tool 转换 (MCPAdapter) | 🟢 | 30min | MCP-02, TOOL-01 | src/jojo/mcp/adapter.py |
| MCP-04 | 从 YAML 加载 MCP Server 配置 (兼容 Claude Code 格式) | 🟢 | 25min | MCP-01, F-04 | src/jojo/mcp/loader.py |
| MCP-05 | CLI 接入 MCP (mcp list / mcp connect) | 🟢 | 25min | MCP-02 | src/jojo/cli.py |
| MCP-06 | Chat 启动时自动连接 MCP + 工具注册 | 🟢 | 20min | MCP-03, AGT-01 | src/jojo/cli.py |
| MCP-07 | 编写 MCP 单元测试 + 验证 | 🟢 | 30min | MCP-02 | tests/test_mcp.py |

**阶段八完成标志**: YAML 配置 → 自动连接 → 工具注册 → Agent 可调用。

### 🧑 用户验证清单（阶段八）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | MCP Server 列表 | `python run.py mcp list` | 列出 configs/mcp_servers.yaml 中配置的 Server |
| 2 | 连接验证 | `python run.py mcp connect <name>` | 连接成功，列出已注册工具 |
| 3 | Chat 自动连接 | `python run.py chat` 启动后查看启动信息 | 显示 MCP tools 数量 |
| 4 | 单元测试通过 | `pytest tests/test_mcp.py -v` | 全部 PASSED |

### 📁 阶段八新增文件树

```
src/jojo/mcp/
├── __init__.py             # 导出 MCPServerConfig, MCPClient, MCPAdapter
├── config.py               # MCPServerConfig 模型 (stdio/HTTP)
├── client.py               # MCPClient (JSON-RPC, 双传输)
├── adapter.py              # MCP 工具 → Agent Tool (mcp__<srv>__<tool>)
└── loader.py               # YAML → MCPServerConfig (兼容 Claude Code 格式)
configs/
└── mcp_servers.yaml        # MCP Server 配置 (${VAR} 环境变量展开)
src/jojo/cli.py             # +mcp list / mcp connect / chat 自动连接
tests/
└── test_mcp.py              # 12 测试 (模型/加载/客户端/适配器)
```

---

## 阶段九：定时任务 & 主动执行 (Scheduler)

> 目标：Agent 能主动在预定时间执行任务。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| SCH-01 | 实现 Scheduler 封装 (APScheduler) | ⬜ | 35min | F-04 | src/jojo/scheduler/engine.py |
| SCH-02 | 实现 CronJob 数据模型 | ⬜ | 15min | F-06 | src/jojo/scheduler/models.py |
| SCH-03 | 实现 Job 持久化 (SQLite) | ⬜ | 30min | SCH-02, MEM-03 | src/jojo/scheduler/store.py |
| SCH-04 | CLI 管理定时任务 (add/list/remove) | ⬜ | 30min | SCH-01, F-07 | src/jojo/cli.py |
| SCH-05 | 验证：设置一个每天 9 点的定时任务并触发 | ⬜ | 15min | SCH-04 | — |

**阶段九完成标志**: 定时任务按时触发，Agent 执行并将结果存入记忆。

### 🧑 用户验证清单（阶段九）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | 添加定时任务 | `python run.py job add --name "test" --cron "*/5 * * * *" --task "打印当前时间"` | 显示 "Job test created" |
| 2 | 查看任务列表 | `python run.py job list` | 列出所有定时任务及其下次执行时间 |
| 3 | 任务触发 | 等待 5 分钟，查看日志 | 日志中看到定时任务执行记录 |
| 4 | 结果存储 | 任务执行后，检查记忆数据库 | 任务结果已存入 long-term memory |
| 5 | 删除任务 | `python run.py job remove test` | 任务被移除，不再触发 |
| 6 | 持久化 | 重启程序后查看 job list | 之前添加的定时任务还在 |

---

## 阶段十：打磨 & 交付 (Polish)

> 目标：好用、好看、可扩展。

| ID | 任务 | 状态 | 预估 | 依赖 | 产出文件 |
|----|------|------|------|------|----------|
| POL-01 | CLI 升级为 rich 美化界面 | ⬜ | 40min | F-07 | src/jojo/cli.py |
| POL-02 | 支持 YAML 配置文件驱动所有组件 | ⬜ | 35min | F-04 | config.yaml |
| POL-03 | 实现会话管理 (保存/恢复/列表) | ⬜ | 35min | MEM-04 | src/jojo/session.py |
| POL-04 | 编写完整的集成测试套件 | ⬜ | 60min | ALL | tests/test_integration.py |
| POL-05 | 编写 README 和快速开始指南 | ⬜ | 30min | POL-01 | README.md |
| POL-06 | 性能优化：Token 缓存、连接池 | ⬜ | 45min | ALL | 多文件 |
| POL-07 | 最终验证：端到端测试完整流程 | ⬜ | 30min | POL-04 | — |

**阶段十完成标志**: 完整可用的个人 AI 助手，配置驱动，开箱即用。

### 🧑 用户验证清单（阶段十）

| # | 验证项 | 操作步骤 | 预期结果 |
|---|--------|----------|----------|
| 1 | YAML 配置驱动 | 修改 `config.yaml` 中的 model，重启后生效 | 无需改代码，配置切换模型 |
| 2 | Rich 界面 | `python run.py chat` | 彩色输出、Markdown 渲染、对话面板美观 |
| 3 | 会话管理 | `python run.py session save` / `python run.py session list` / `python run.py session resume` | 会话可保存、查看、恢复，历史不丢失 |
| 4 | 端到端测试 | `pytest tests/test_integration.py -v` | 覆盖主要用户流程，全部 PASSED |
| 5 | README 可用 | 按照 README.md 的步骤从零安装 | 另一个开发者能跑通全部流程 |
| 6 | 帮助信息完整 | `python run.py --help` 和各个子命令 `--help` | 每个命令都有清晰的用法说明 |

---

## 任务统计

| 阶段 | 名称 | 任务数 | 预估总时间 |
|------|------|--------|------------|
| 一 | 项目基础 | 9 | ~3h |
| 二 | LLM 适配层 | 5 | ~2.5h |
| 三 | 工具系统 | 8 | ~4h |
| 四 | 单 Agent 核心循环 | 9 | ~4.5h |
| 五 | 记忆系统 | 8 | ~4h |
| 六 | 多 Agent 协作 | 9 | ~5h |
| 七 | Skill 技能系统 | 8 | ~4h |
| 八 | MCP 协议集成 | 7 | ~3.5h |
| 九 | 定时任务 | 5 | ~2h |
| 十 | 打磨交付 | 7 | ~5h |
| **合计** | | **75** | **~37.5h** |

约 **1-2 周** 可完成全部阶段（按每天 4-6 小时计算）。

---

## 执行策略

```
MVP (最小可用)      = 阶段一 + 阶段二 + 阶段三 + 阶段四
                      → 一个能聊天、能调工具的单 Agent

增强版              = MVP + 阶段五 + 阶段六
                      → 有记忆、多 Agent 协作

完整版              = 增强版 + 阶段七 + 阶段八 + 阶段九
                      → Skill 系统 + MCP + 定时任务

生产版              = 完整版 + 阶段十
                      → 打磨完善，可日常使用
```

**建议**: 先冲到 MVP（约 13h），跑通整个 Agent 循环，获得正反馈后再逐阶段叠加。

---

> 版本: v1.0 | 创建: 2026-05-13 | 关联文档: docs/agent-framework-guide.md
