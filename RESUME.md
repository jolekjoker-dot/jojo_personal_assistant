# JoJo Personal AI Assistant — 简历项目描述与面试问答

---

## 一、项目概述（简历用）

### 一句话总结

从零搭建的、可扩展的多 Agent 个人 AI 助手框架，实现 ReAct 推理循环、三层记忆系统（含遗忘曲线）、多 Agent 编排（自动路由 / 顺序 / 并行）、Skill 技能系统、MCP 协议集成，以及基于风险等级的人工审批机制。

### 适合写在简历上的项目描述

**项目名称：** JoJo — 个人 AI Agent 框架

**项目周期：** 2026 年 4 月 - 2026 年 5 月（约 6 周）

**技术栈：** Python 3.11+, litellm, Pydantic v2, ChromaDB, SQLite, asyncio, Typer, Rich, PyYAML, APScheduler

**项目亮点（选 3-4 条放简历上）：**

- 从零实现 **ReAct（Reasoning + Acting）推理循环引擎**，Agent 自动完成 Thought → Action → Observation 闭环，支持 Function Calling、流式输出和终止条件检测（防死循环）
- 设计并实现**三层记忆系统**：L1 工作记忆（对话窗口）、L2 短期记忆（LLM 摘要压缩）、L3 长期记忆（SQLite + ChromaDB 混合检索，结合艾宾浩斯遗忘曲线自动衰减淘汰）
- 实现**多 Agent 编排调度器**，支持三种协作模式（LLM 自动路由、顺序流水线、并行执行），集成任务复杂度分类器，自动按 simple/medium/complex 选择 Flash/Pro 模型
- 设计 **Skill 技能系统**（Markdown + YAML Frontmatter 定义可复用能力包），支持关键词触发、加权匹配、自动 Prompt 注入
- 实现 **MCP（Model Context Protocol）客户端**，支持 stdio 和 HTTP 两种传输方式，可动态发现和调用外部 MCP Server 工具
- 构建**工具安全沙箱**：Python 代码执行沙箱（拦截危险调用）+ 文件路径穿越防护 + 基于风险等级（read/write/dangerous）的人工审批流程

---

## 二、项目架构图（面试时可以在白板上画）

```
┌─────────────────────────────────────────────────────────┐
│                   CLI (Typer + Rich)                     │
├─────────────────────────────────────────────────────────┤
│                 ORCHESTRATOR (调度层)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ TaskClassifier│  │    Router    │  │  Orchestrator │  │
│  │ (simple/med/  │  │ (LLM路由)    │  │ (seq/auto/    │  │
│  │  complex)     │  │              │  │  parallel)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│              AGENT REGISTRY (Agent 注册中心)              │
│  ┌──────────┐  ┌──────────┐                             │
│  │ Researcher│  │  Coder   │                             │
│  │ (Flash)   │  │  (Pro)   │                             │
│  └──────────┘  └──────────┘                             │
├─────────────────────────────────────────────────────────┤
│                   ReAct Loop Engine                      │
│  User Input → Memory Retrieve → LLM Think →             │
│  Tool Call? → [Approval?] → Execute → Observe →         │
│  Final Answer → Save Memory                              │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │  TOOLS   │  │  SKILLS  │  │   MCP CLIENT       │    │
│  │ Registry │  │ Registry │  │ (stdio + HTTP)     │    │
│  │ @tool    │  │ .md →    │  │ JSON-RPC 2.0       │    │
│  │ decorator│  │ Prompt   │  │ tools/list/call    │    │
│  └──────────┘  └──────────┘  └────────────────────┘    │
├─────────────────────────────────────────────────────────┤
│                 MEMORY SYSTEM (三层记忆)                  │
│  L1 Working → L2 ShortTerm → L3 LongTerm (SQLite+Chroma)│
│  消息历史       LLM摘要压缩     向量检索 + 遗忘曲线衰减     │
├─────────────────────────────────────────────────────────┤
│              INFRASTRUCTURE (基础设施)                    │
│  LLM Provider (litellm)  │  Config (Pydantic+YAML)      │
│  Logger (loguru)         │  Sandbox (安全沙箱)           │
└─────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详解

### 3.1 ReAct 推理循环 (`src/jojo/agent/react_loop.py`)

```
流程：
  User Input
    → 检索长期记忆（MemoryManager.build_context）
    → 匹配 Skill（SkillRegistry.match → 注入 Prompt）
    → LLM 思考（Thought）
    → 决策：调工具？还是最终回复？
    → 如果要调工具：
        → 检查风险等级（read → 自动放行；write/dangerous → 弹出审批）
        → 用户批准 → 执行 → 观察结果 → 回到 LLM 思考
        → 用户拒绝 → 注入拒绝信息 → 回到 LLM 思考
    → 如果是最终回复：
        → 保存记忆 → 返回答案
```

关键设计：
- **LoopGuard**：三重保护 — 最大迭代次数（30）、最大执行时间（120s）、连续重复检测（3 次触发终止）
- **ApprovalHandler**：三级风险 — `read`（自动放行）、`write`（会话级 allow_all 可跳过）、`dangerous`（始终审批）
- **DeepSeek V4 Pro 兼容**：回传 `reasoning_content`（推理链），保留模型思考过程

### 3.2 三层记忆系统 (`src/jojo/memory/`)

| 层级 | 存储 | 生命周期 | 容量 | 实现 |
|------|------|----------|------|------|
| L1 Working | 内存 list | 单次对话 | 20 条消息 | 简单的 append + 阈值检测 |
| L2 ShortTerm | 内存 dict | 会话级（TTL 1h） | 不限 | LLM 摘要压缩，自动触发 |
| L3 LongTerm | SQLite + ChromaDB | 永久 | 不限 | 向量检索 + 关键词回补 + 遗忘曲线 |

**遗忘曲线算法（`decay.py`）：**

```python
decay_score = time_decay × 0.4 + access_score × 0.3 + importance_score × 0.3

time_decay:      指数衰减，半衰期 7 天（2^(-t / 7days)）
access_score:    每次检索命中 +0.25，上限 1.0，近期访问额外 +0.3
importance:      LLM 标记的 high(1.0) / medium(0.6) / low(0.15)
检索阈值:  score < 0.1 → 跳过
清理阈值:  score < 0.05 → 永久删除
```

**混合检索策略：**
1. ChromaDB 向量语义召回（top_k × 2 候选）
2. SQLite LIKE 关键词回补（前 3 个关键词）
3. 重新计算 decay_score 并过滤低于阈值的
4. 按分数降序返回 top_k

**上下文窗口管理：**
- 工作记忆超过阈值 → LLM 自动摘要压缩
- 保留最近 5 条消息 + 摘要
- 同时提取关键信息存入长期记忆（key point extraction）

### 3.3 多 Agent 编排 (`src/jojo/orchestrator/`)

**三种执行模式：**

| 模式 | 逻辑 | 适用场景 |
|------|------|----------|
| **Auto（自动路由）** | classify → route → execute | 单 Agent 任务，自动选最合适的 |
| **Sequential（顺序流水线）** | Agent A → Agent B → Agent C | 调研→写报告 等上下游任务 |
| **Parallel（并行执行）** | 多个 Worker 同时执行 + Merger 汇总 | 多源信息对比、批量搜索 |

**TaskClassifier（任务复杂度分类器）：**
- 用 Flash 模型快速判断复杂度（simple/medium/complex）
- simple → Flash 模型（省钱）: 问候、闲聊、简单问答
- medium → Flash 模型: 1-2 个工具调用
- complex → Pro 模型（保证质量）: 代码执行、多步骤任务
- 极短输入（< 10 字符且无问号/"帮"）直接判 simple，不调 LLM

**Router（Agent 路由器）：**
- LLM 读取所有 Agent 的能力描述，选择最合适的
- 不是硬编码 if-else，让 LLM 自己判断
- 容错：路由失败时返回第一个 Agent

### 3.4 Skill 技能系统 (`src/jojo/skills/`)

**Skill = Prompt 模板 + 工具依赖 + 触发规则 + 执行流程**

```markdown
---
name: code-review
description: 审查代码变更，检查安全问题、Bug 和代码质量
triggers: ["review", "code review", "审查", "代码审查"]
requires:
  tools: [read_file, list_files]
---
# 技能正文（Markdown 格式的执行流程）
```

**匹配策略（加权计分）：**
- 关键词触发（triggers）: +10 分
- 标签匹配（tags）: +3 分
- 名称匹配: +5 分
- 描述匹配: +1 分/词
- 最多返回 3 个匹配 Skill，注入到 System Prompt

**设计优势：**
- 和 Claude Code 的 Skill 格式兼容
- Markdown 定义，非技术人员也能编写
- Agent 自动匹配，无需手动指定
- 支持工具依赖声明（缺工具时不激活）

### 3.5 工具系统与安全沙箱 (`src/jojo/tools/`)

**Tool 注册机制：**
- `@tool` 装饰器注册，自动从函数签名生成 JSON Schema
- 单例 ToolRegistry 管理所有工具
- OpenAI Function Calling 格式导出

**安全沙箱（`sandbox.py`）：**
- **路径穿越防护**：`resolve_path()` 校验所有文件操作在 workspace_root 内
- **Python 代码安全校验**：拦截 `os.system`、`subprocess`、`eval`、`exec`、`shutil.rmtree` 等危险调用
- **白名单导入**：只允许安全的 Python 标准库模块

**风险等级审批：**
- `read`（web_search, read_file, list_files）→ 自动放行
- `write`（write_file）→ 会话级 allow_all 可跳过
- `dangerous`（execute_python）→ 始终审批

### 3.6 LLM 适配层 (`src/jojo/llm/`)

- 基于 **litellm** 实现统一多模型接口
- 支持 OpenAI、Anthropic、DeepSeek 等 100+ 模型，一行代码切换
- 同步/异步/流式三种调用模式
- 自动 Token 用量追踪（UsageTracker）
- 支持 Function Calling（chat_with_tools）
- DeepSeek V4 Pro 的 reasoning_content 回传

### 3.7 MCP 协议客户端 (`src/jojo/mcp/`)

- 实现 JSON-RPC 2.0 协议
- 支持 **stdio**（本地子进程）和 **HTTP+SSE**（远程服务）两种传输
- 工具发现（`tools/list`）、工具调用（`tools/call`）、资源访问（`resources/list`、`resources/read`）
- 配置驱动：`configs/mcp_servers.yaml`
- 工具名称命名空间隔离：`mcp__{server}__{tool}`

---

## 四、技术决策与架构思考

### 为什么不用 LangChain / CrewAI，而是自己搭建？

| 维度 | 使用框架（LangChain/CrewAI） | 自己搭建（JoJo） |
|------|---------------------------|-----------------|
| 理解深度 | 只懂 API，不懂原理 | 每个细节了如指掌 |
| 定制能力 | 受框架抽象限制 | 完全自由 |
| 性能 | 框架额外开销 | 零额外开销，路径最短 |
| Debug | 堆栈深，难追踪 | 代码自写，秒级定位 |
| 学习价值 | 低（学会用工具） | 高（学会造工具） |
| Skill 灵活度 | 受限于框架格式 | Markdown 自定义格式 |
| 自我进化 | 基本无法实现 | Skill Learner 可自动提炼 |

### 为什么默认用 ReAct 而不是 Plan-Execute？

1. ReAct 所有模型都原生支持（Function Calling 天然兼容）
2. 人类可读的推理链（Thought → Action → Observation），Debug 极其简单
3. 最大兼容性 — ReAct 是所有其他模式的 Fallback
4. 渐进增强 — 先在 ReAct 上跑通，再加 ReWOO/Plan-Execute 等其他模式

### 为什么选择 litellm？

- 一行代码切换模型，不需要改任何业务逻辑
- 支持 100+ 模型提供商
- 统一的 Function Calling 接口
- 内置 Token 用量统计
- 社区活跃，更新快

### 为什么用 ChromaDB 而不是 Qdrant/Milvus/Pinecone？

- **本地化优先**：ChromaDB 嵌入式运行，无需单独部署服务
- **轻量级**：内存/持久化两种模式，个人项目够用
- **API 简洁**：`add` / `query` / `delete` 语义清晰
- **SQLite 兜底**：向量检索失败时回退到关键词匹配

---

## 五、面试常见问题及回答

### Q1: 请简单介绍这个项目？

**回答框架：**
> 我从零搭建了一个个人 AI Agent 框架，约 2000+ 行 Python 代码。核心实现包括：1）ReAct 推理循环引擎（Thought → Action → Observation）；2）三层记忆系统（工作记忆 + 短期摘要 + 长期向量存储，含遗忘曲线）；3）多 Agent 编排调度器（自动路由/顺序/并行三种模式）；4）Skill 技能系统（Markdown 定义的可复用能力包）；5）MCP 协议客户端（连接外部工具的标准协议）。技术栈是 Python + litellm + ChromaDB + SQLite + Pydantic。做这个项目的初衷是想深入理解 AI Agent 的底层原理，而不是停留在使用 LangChain 等框架的 API 调用层面。

---

### Q2: 你的 Agent 循环具体怎么实现的？

**回答要点：**
1. 先解释 ReAct 循环的概念：思考 → 行动 → 观察 → 再思考 → 最终回复
2. 讲清楚每一步的输入输出
3. 提到防死循环的三重保护（迭代次数/时间/重复检测）
4. 提到风险审批机制

**参考回答：**
> 我实现的是 ReAct 模式的 Agent 循环。用户输入后，先通过 MemoryManager 检索相关长期记忆，再通过 SkillRegistry 匹配相关技能，增强 System Prompt。然后进入循环：调用 LLM（带工具 Schema），LLM 返回后判断是否有 tool_calls — 如果有，走审批流程（read 自动放行、write/dangerous 需要用户确认），执行工具后把结果反馈给 LLM 继续思考；如果没有 tool_calls，说明是最终回复，保存记忆后直接返回。循环有 LoopGuard 做三重保护：最大迭代 30 次、最大执行 120 秒、连续 3 次相同输出自动终止。

---

### Q3: 你的记忆系统怎么设计的？和普通聊天记录有什么区别？

**回答要点：**
1. 三层架构 vs 单纯的聊天记录列表
2. 遗忘曲线的设计思路
3. 混合检索策略
4. 自动压缩机制

**参考回答：**
> 普通聊天应用只是把历史消息存下来，问题是：上下文窗口有限（放不下长历史）、相关信息检索困难（只能靠时间排序）、存储无法持久化。
>
> 我的三层记忆系统：
> - **L1 工作记忆**：当前对话的消息历史，直接注入 Prompt，最多 20 条
> - **L2 短期记忆**：当 L1 满了，触发 LLM 摘要压缩，保留最近 5 条 + 摘要
> - **L3 长期记忆**：SQLite 存结构化数据 + ChromaDB 做向量检索，同时从对话中提取关键信息（偏好、决策、事实）自动存入
>
> 最特别的是**遗忘曲线**：综合时间衰减（指数半衰期 7 天）、访问频率（每次命中 +0.25）、重要性（high/medium/low 三档）三个维度计算 decay_score，低于阈值的记忆自动在检索中跳过或永久删除。这模拟了人脑的记忆规律 — 重要的、经常用的记得牢，不重要的自然遗忘。
>
> 检索时采用**混合召回**：ChromaDB 向量语义 + SQLite 关键词回补 + 时间戳排序，保证了查全率和查准率。

---

### Q4: 多 Agent 之间怎么协作？怎么决定让哪个 Agent 处理任务？

**回答要点：**
1. 三种协作模式及其适用场景
2. 任务分类器的设计
3. Router 不是硬编码

**参考回答：**
> 我设计了一个 Orchestrator 调度器，支持三种模式：
>
> 1. **Auto 自动路由**：先由 TaskClassifier（用便宜的 Flash 模型）快速判断任务复杂度 — simple（问候）→ Flash 模型、medium（搜索）→ Flash、complex（写代码）→ Pro 模型。然后 Router 用 LLM 读取所有 Agent 的能力描述，选出最合适的。
>
> 2. **Sequential 顺序流水线**：Agent A 的输出作为 Agent B 的输入。比如 Researcher 先搜资料 → Coder 基于资料写报告。
>
> 3. **Parallel 并行执行**：同一任务的多个子任务同时分派给独立的 Agent 实例（避免消息交叉污染），最后用一个 Merger Agent 汇总。
>
> 关键是 Router 不是硬编码 if-else，而是让 LLM 自己读能力描述做判断。这样加新 Agent 时不需要改路由逻辑。

---

### Q5: 你的工具系统是怎么设计的？怎么保证安全？

**回答要点：**
1. @tool 装饰器 + 自动 Schema 生成
2. 风险分级审批
3. 安全沙箱

**参考回答：**
> 工具系统有三个核心设计：
>
> **注册机制**：通过 `@tool(name, description, risk)` 装饰器把普通 Python 函数注册为工具，自动从函数签名 + 类型注解生成 JSON Schema（OpenAI Function Calling 格式），存到单例 ToolRegistry 中。
>
> **安全沙箱**：文件操作方面，所有路径先 resolve 再校验，如果不在 workspace_root 内（比如 `../../etc/passwd`）直接拒绝；Python 代码执行方面，用黑名单拦截 `os.system`、`subprocess`、`eval`、`exec`、`shutil.rmtree` 等危险调用，同时维护白名单限制可导入的模块。
>
> **风险审批**：每个工具有风险等级（read/write/dangerous）。read 操作（搜索、读文件）自动放行；write 操作（写文件）首次需要确认，用户可选"本次会话全部放行"；dangerous 操作（执行代码）每次都需要审批。这个设计保证了 Agent 的自主性和安全性的平衡。

---

### Q6: Skill 系统和 Tool 有什么区别？为什么需要 Skill？

**回答要点：**
1. Tool 是原子操作，Skill 是复合流程
2. Skill 的定义和执行方式
3. 实际例子说明

**参考回答：**
> Tool 和 Skill 是不同粒度的抽象：
> - **Tool** 是单一原子操作，比如 `web_search`、`read_file`，一个 LLM 调用即可完成
> - **Skill** 是多步骤的复合能力包，比如 `code-review` Skill 包含"读取代码 → 安全检查 → Bug检查 → 质量检查 → 生成报告"五个步骤，需要多次 LLM 调用 + 多个 Tool
>
> 技术上，Skill 是用 Markdown + YAML Frontmatter 定义的。Frontmatter 声明名称、描述、触发关键词、依赖工具；正文是给 Agent 看的执行流程。Agent 收到用户输入后，SkillRegistry 通过加权计分（关键词 +10、标签 +3、名称 +5、描述 +1）自动匹配最相关的 Skill，把 Skill 正文注入 System Prompt，Agent 就按 Skill 定义的步骤执行。
>
> 为什么需要 Skill？因为 Tool 太细粒度了，LLM 容易在复杂任务中迷失方向。Skill 相当于给了 Agent 一个 SOP（标准操作流程）。

---

### Q7: MCP 协议是什么？你在项目中怎么用的？

**回答要点：**
1. MCP 的定义和解决的问题
2. 两种传输方式的实现
3. 在 Agent 中的集成方式

**参考回答：**
> MCP（Model Context Protocol）是 Anthropic 发布的开放标准，解决的是 AI 应用如何标准化连接外部工具的问题。没有 MCP 之前，每接一个外部工具（GitHub API、数据库、Slack 等）都要写一套集成代码；有了 MCP，所有工具通过统一协议接入，Agent 只需要实现一个 MCP Client。
>
> 我在项目中实现了一个 MCP Client，支持两种传输方式：**stdio**（启动本地子进程，通过 stdin/stdout 走 JSON-RPC 2.0）和 **HTTP**（通过 httpx 调用远程服务）。实现了初始化握手、工具发现（tools/list）、工具调用（tools/call）、资源访问（resources/list & read）四个核心流程。工具名称用 `mcp__{server}__{tool}` 命名空间隔离。
>
> 配置用 `configs/mcp_servers.yaml` 管理，可以接入社区已有的 MCP Server（文件系统、数据库、GitHub、Brave 搜索等），也可以接自己写的。在 Agent 中，MCP 工具和内置工具一起注册到 ToolRegistry，LLM 调用时无感知差异。

---

### Q8: 你在开发过程中遇到的最大挑战是什么？怎么解决的？

**建议从以下选 1-2 个答：**

**挑战一：LLM 工具调用的 JSON 解析不够健壮**
> LLM 返回的工具参数有时是 JSON 字符串有时是 dict，有时 JSON 格式不合法。我做了 `_parse_args` 方法统一处理：如果是 dict 直接返回，如果是字符串尝试 `json.loads`，解析失败返回空 dict 并记录日志，不让整个循环崩溃。

**挑战二：DeepSeek V4 Pro 的 reasoning_content 回传**
> DeepSeek V4 Pro 在 Function Calling 时需要把上一轮的 `reasoning_content`（CoT 推理链）原样回传，否则 API 报错。我修改了 `chat_with_tools` 的返回结构和消息构建逻辑，保留了 reasoning_content 字段。

**挑战三：上下文窗口管理**
> 多轮工具调用后消息历史迅速膨胀，容易超出 LLM 上下文限制。我的解决方案是：1）工作记忆超过 20 条自动触发 LLM 摘要压缩；2）只保留最近 5 条完整消息，其余用摘要替代；3）摘要同时提取关键事实存入长期记忆。

**挑战四：多 Agent 并行时的消息交叉污染**
> 并行模式下，如果多个 Worker 共享同一个 Agent 实例，消息历史会交叉污染。解决方案是每个 Worker 创建独立的 Agent 实例，执行完毕即销毁。

---

### Q9: 如果要你把这个项目变成生产级的，你会怎么做？

**回答要点（体现工程思维）：**

> 1. **持久化会话**：当前会话在内存中，需要加 SQLite/Redis 持久化，支持断点续聊
> 2. **API Server**：用 FastAPI 包装成 REST API，支持 Web/移动端接入
> 3. **可观测性**：加 OpenTelemetry 追踪（LLM 调用的延迟、Token 消耗、工具调用成功率）、结构化日志
> 4. **测试覆盖**：当前单元测试覆盖核心模块，需要加集成测试（Mock LLM 的端到端测试）和 E2E 测试
> 5. **错误恢复**：LLM 调用失败的重试机制（指数退避）、工具执行超时处理
> 6. **多用户支持**：用户身份隔离、记忆隔离、配额管理
> 7. **更多推理模式**：在 ReAct 基础上加 ReWOO（并行执行无依赖步骤）、Reflexion（自我反思迭代）
> 8. **容器化部署**：Docker + docker-compose，ChromaDB 可选独立部署

---

### Q10: litellm 在你的项目中扮演什么角色？为什么要用它？

> litellm 是我的 LLM 适配层的基础。它提供了一个统一的接口来调用 OpenAI、Anthropic、DeepSeek 等 100+ 模型。我把它封装在 `LLMProvider` 类中，提供 `chat()`（同步）、`chat_with_tools()`（带工具调用）、`stream()`（流式）三种方法。
>
> 选 litellm 的原因：
> 1. **一行代码切换模型**：`LLMProvider("deepseek/deepseek-chat")` → `LLMProvider("openai/gpt-4o")`
> 2. **统一的 Function Calling**：不同厂商的工具调用格式不同（OpenAI 的 tool_calls、Anthropic 的 tool_use），litellm 统一了差异
> 3. **内置 Token 统计**：每次调用自动记录 prompt_tokens 和 completion_tokens
> 4. **社区活跃**：新模型出来后通常几天内就能支持
>
> 但我不依赖 litellm 做更多事情（如 Agent 循环、记忆管理），它只是 LLM 调用的薄封装层。

---

### Q11: 你的配置管理是怎么做的？为什么用 Pydantic？

> 我用 Pydantic + YAML + .env 三层配置管理：
> - **Pydantic**：定义配置的数据模型（Config、LLMConfig、MemoryConfig 等），提供类型安全、默认值、自动验证
> - **YAML**：用户可读的配置文件（config.yaml），包含模型选择、记忆参数、调度器配置等
> - **.env**：敏感信息（API Key），不提交到 Git
>
> 优先级是 `环境变量 > YAML 文件 > 默认值`。`load_config()` 用 `@lru_cache` 缓存，确保全局单例。
>
> Pydantic 的好处：1）配置写错时启动即报错（fail fast），而不是跑到一半才炸；2）IDE 有类型提示；3）嵌套配置模型清晰，比如 `config.memory.working_max_messages`。

---

### Q12: ChromaDB 和 SQLite 在你的项目中分别承担什么角色？为什么同时用两个？

> 它们是互补的：
> - **ChromaDB** 负责语义检索。记忆存入时自动生成 embedding 向量，检索时通过余弦相似度找到语义相近的记忆。这解决的是"我想不起来了但意思差不多"的问题。
> - **SQLite** 负责结构化存储和关键词检索。记忆的元数据（创建时间、访问次数、重要性、标签）存在 SQLite 表中，检索时用 LIKE 做关键词匹配。这解决的是精准查找和元数据管理的问题。
>
> 为什么同时用？因为纯向量检索有盲区：1）专业术语或代码片段（embedding 对代码的语义理解不够好）；2）精确关键词匹配（"jojo" 这个项目名在向量空间里没有好的对应）。所以我的策略是：向量检索出候选 → 关键词回补 → 统一计算 decay_score 过滤 → 排序返回。这叫混合检索（Hybrid Search）。

---

### Q13: 你的项目里用了哪些设计模式？

> 1. **单例模式**：ToolRegistry、SkillRegistry、Config 都用单例（或 lru_cache 缓存），确保全局一致
> 2. **装饰器模式**：`@tool` 装饰器把普通函数增强为带有 Schema 和风险等级的 Tool 对象
> 3. **注册表模式**：AgentRegistry、ToolRegistry、SkillRegistry 都是"注册-查找-调用"模式，核心组件解耦
> 4. **策略模式**：Orchestrator 的三种执行模式（auto/sequential/parallel）本质是不同策略
> 5. **模板方法**：Skill 定义执行流程（Step 1 → Step 2 → ...），Agent 按模板执行但每个步骤具体实现由 LLM 动态决定
> 6. **工厂模式**：Agent 的创建（researcher/coder 用不同模型、不同 System Prompt）

---

### Q14: 如果面试官问"你觉得自己写的 Agent 和 ChatGPT 有什么区别？"

> ChatGPT 是一个产品，用户通过统一的对话界面与单一模型交互。JoJo 是一个 Agent 框架，区别在于：
> 1. **工具调用**：JoJo 的 Agent 能主动调用工具（搜索、读写文件、执行代码）并观察结果后继续推理；ChatGPT 虽然也有工具但用户看不到完整的思考-行动循环
> 2. **模型无关**：JoJo 通过 litellm 适配任意模型（DeepSeek/OpenAI/Anthropic），ChatGPT 绑定 OpenAI 自家模型
> 3. **多 Agent 协作**：JoJo 支持多个专业 Agent 协作（研究者 + 编程者），ChatGPT 是单一 Agent
> 4. **记忆系统**：JoJo 有独立的三层记忆 + 遗忘曲线，跨会话持久化；ChatGPT 的记忆是平台功能，用户不可控
> 5. **可扩展性**：JoJo 可以通过 MCP 协议连接任意外部工具、通过 Skill 系统定义可复用流程，ChatGPT 的 GPTs/Plugins 受平台限制

### Q15: OpenClaw 和 Hermes Agent 都是很优秀的开源 Agent 项目，为什么你要自己搭建一个？

**回答框架：**

这个问题面试官其实在考察两点：1）你是不是调研过业界方案再做决策的（而非闭门造车）；2）你对这些方案的理解深度。

**回答要点：**

**1. 先说清楚 OpenClaw 和 Hermes Agent 是什么（证明你调研过）：**

> **Hermes Agent**（Nous Research, 2025 年 2 月开源, GitHub 50K+ stars）是一个完全本地化的个人 Agent 运行时。核心特色是 SQLite + FTS5 全文检索做记忆、艾宾浩斯遗忘曲线、以及 Agent 自我进化（在执行中自动提炼技能）。它在长对话记忆方面做得很好，用一个简单的 SQLite 文件就实现了跨会话记忆。
>
> **OpenClaw / MEMTIER**（2026 年 5 月发布）是最新的学术级 Agent 记忆架构。其核心是 MEMTIER 论文提出的五维度信号加权检索（语义、时序、重要性、频率、上下文），配合 Attention-Attributed Weight Update 和 PPO 强化学习自动调整检索权重。在 LongMemEval-S 基准上达到 68.6%-71.4%，且只需要消费级 GPU（6GB）。其工具执行成功率在 72 小时运行窗口内仅下降 14 个百分点。

**2. 解释为什么没有直接用它们：**

> **定位差异**：
> - Hermes Agent 是一个**完整的运行时产品**，像一个"安装即用"的个人助手。它的设计目标是开箱即用，而非作为一个可嵌入的框架/SDK。如果你想在 Hermes 上做深度定制（比如换一套自己的记忆后端、加一个自定义的 Agent 协作模式），非常困难 — 它不是为这个设计的。
> - OpenClaw 更像一个**前沿研究项目**，论文刚发、代码较新，API 稳定性不可预期。它的核心创新在记忆层（MEMTIER），但多 Agent 编排、Skill 系统、MCP 集成等方面并不完备。
>
> **架构耦合度**：
> - Hermes Agent 的记忆系统和 Agent 循环是紧耦合的 — 你无法单独把它的遗忘曲线模块换成另一套算法而不改主体代码。
> - JoJo 的每个子系统（记忆 / 编排 / 工具 / Skill / MCP）都通过明确的接口解耦，可以独立替换。比如你可以把 ChromaDB 换成 Qdrant，只需要改 `LongTermMemory` 一个文件。
>
> **学习价值**：
> - 如果直接用 Hermes 或 OpenClaw，我对 Agent 的理解会停留在"怎么用这个工具"的层面。
> - 通过自己搭建，我理解了每一个设计决策背后的 trade-off：为什么 ReAct 比 Plan-Execute 更适合作为默认模式？为什么记忆系统用混合检索而不是纯向量？为什么遗忘曲线用三因子加权而不是简单的 TTL？这些理解是用框架永远得不到的。

**3. 说明你参考了它们的最佳实践（证明不是闭门造车）：**

> 实际上，JoJo 的设计大量参考了这两个项目的精华：
> - 借鉴了 Hermes Agent 的**艾宾浩斯遗忘曲线**思路（写入 `src/jojo/memory/decay.py`），在它的二因子模型上增加了一个"近期访问加成"维度
> - 借鉴了 Hermes Agent 的 **SQLite 本地优先**理念（`LongTermMemory` 同时用 SQLite 和 ChromaDB，SQLite 做主存、ChromaDB 做语义检索引擎）
> - 借鉴了 MEMTIER 的**多信号加权检索**思路，在 JoJo 中实现了"向量语义 + 关键词回补 + 时间衰减 + 重要性加权"的四路混合召回
> - 同时在它们薄弱的领域做了扩展：多 Agent 编排、Skill 系统、MCP 协议、风险审批 — 这些是 Hermes 和 MEMTIER 都没有的

**4. 一句话总结（让面试官记住）：**

> JoJo 不是一个"替代 Hermes/OpenClaw"的项目，而是一个"吸收了业界最佳实践的、模块化可扩展的、用于理解 Agent 底层原理的"教学级框架。把 JoJo 的每个模块单独拆出来，都可以在自己的项目中复用。

**如果面试官追问：既然让你重新选，你会直接用 OpenClaw 吗？**

> 这取决于目标。如果目标是快速上线一个个人助手产品，我会优先选 Hermes Agent 或 OpenClaw 作为基座。但如果目标是深入理解 Agent 架构、为团队后续的技术选型建立判断力，我还是会先自己搭一遍。因为写过一次 ReAct 循环之后，再去看 LangChain 的 AgentExecutor 源码，会发现"原来它就是在做这个" — 这种降维打击式的理解是用框架得不来的。

**如果面试官追问：你的项目和 Hermes Agent 比，技术上差在哪里？**

> 坦诚地说：
> 1. **工程成熟度**：Hermes 是 50K+ stars 的项目，经过了大量用户的实战检验，Bug 修复、边界条件处理肯定比我全面
> 2. **自我进化能力**：Hermes 的 Agent 可以从执行中自动提炼技能并持久化，这是一个正向飞轮；JoJo 目前只是预留了这个设计的接口，还没有完整实现
> 3. **FTS5 全文检索**：Hermes 用 SQLite FTS5 做高效的倒排索引，JoJo 目前用的是 LIKE 模糊匹配（简单但不够高效）。不过这也说明我的代码很简单，容易理解
> 4. **社区生态**：Hermes 有活跃的社区贡献插件和工具
>
> 但 JoJo 也有 Hermes 没有的优点：
> 1. **多 Agent 编排**：Hermes 是单 Agent 架构，没有 Orchestrator 这种调度器
> 2. **Skill 系统**：JoJo 的 Markdown 格式 Skill 更易编写、更易分享、和 Claude Code 格式兼容
> 3. **MCP 原生集成**：JoJo 从一开始就设计了 MCP Client，Hermes 目前没有
> 4. **代码量的精简**：核心约 2000 行 Python，读一遍只需要 30 分钟 — 这对学习和二次开发极其友好

> 正确的态度不是"谁比谁强"，而是"我从它们身上学到了什么，我自己的方案在什么场景下更合适"。

---

## 六、简历上的项目描述模板

### 版本 A：简洁版（适合中文简历，3-4 行）

> **JoJo — 个人 AI Agent 框架** | Python, litellm, ChromaDB, SQLite | 2026.04-2026.05
> - 从零实现 ReAct 推理循环引擎，支持 Function Calling、终止条件检测、基于风险等级的人工审批
> - 设计三层记忆系统（工作/短期/长期），实现混合检索（向量 + 关键词）和艾宾浩斯遗忘曲线衰减机制
> - 构建多 Agent 编排调度器，支持自动路由/顺序流水线/并行执行，集成任务复杂度分类器动态选择模型
> - 实现 Skill 技能系统（Markdown 定义的可复用能力包）和 MCP 协议客户端（stdio + HTTP 传输）

### 版本 B：详细版（适合英文简历 / LinkedIn）

> **JoJo — Extensible Multi-Agent AI Framework** | Python 3.11+, litellm, ChromaDB, SQLite | 2026
>
> Built a personal AI agent framework from scratch, achieving deep understanding of agent architecture beyond framework-level API usage.
>
> **Core implementations:**
> - **ReAct Loop Engine** — Thought → Action → Observation cycle with LoopGuard (iteration/duration/repetition limits) and risk-based human-in-the-loop approval (read/write/dangerous)
> - **Three-Layer Memory System** — L1 working memory (conversation window), L2 short-term (LLM summarization with auto-compression), L3 long-term (SQLite + ChromaDB hybrid retrieval with Ebbinghaus forgetting curve decay)
> - **Multi-Agent Orchestrator** — Task complexity classifier (simple/medium/complex → Flash/Pro model routing), LLM-based agent routing, sequential pipeline, and parallel execution with result merging
> - **Skill System** — Reusable capability packages defined in Markdown + YAML frontmatter with weighted keyword matching and automatic prompt injection
> - **MCP Client** — Model Context Protocol integration supporting stdio and HTTP transports, JSON-RPC 2.0, dynamic tool discovery
> - **Security Sandbox** — Path traversal prevention, Python code safety validation (blacklist + whitelist), risk-tiered approval flow
>
> **Tech Stack:** Python, litellm, Pydantic v2, ChromaDB, SQLite, asyncio, Typer, Rich, PyYAML, APScheduler

### 版本 C：一句话版本（适合技能栏）

> 深入理解 AI Agent 底层原理：从零实现 ReAct 推理循环、三层记忆系统（含遗忘曲线）、多 Agent 编排调度、Skill 技能系统、MCP 协议集成

---

## 七、项目中的定量数据（面试加分项）

| 指标 | 数据 |
|------|------|
| 总代码量 | ~2000+ 行 Python（不含测试和文档） |
| 源文件数 | 30+ 个 Python 模块 |
| 测试文件 | 7 个测试文件（覆盖 llm/tools/agent/memory/multi_agent/skills/mcp） |
| 支持的 LLM 厂商 | 通过 litellm 支持 100+ 模型 |
| 内置工具数 | 5 个（web_search / read_file / write_file / list_files / execute_python） |
| 预置 Agent | 2 个（Researcher / Coder） |
| 预置 Skill | 2 个（code-review / daily-summary） |
| 记忆检索延迟 | ChromaDB 向量检索 < 50ms，关键词回补 < 10ms |
| 遗忘半衰期 | 7 天 |
| 工作记忆容量 | 20 条消息（可配置） |

---

> **文档版本**: v1.0
> **生成日期**: 2026-05-15
> **适用场景**: 面试准备、简历撰写、项目介绍
