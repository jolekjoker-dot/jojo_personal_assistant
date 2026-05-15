# JoJo Personal AI Assistant

一个从零搭建的、可扩展的个人 AI Agent 框架。

## 快速开始

### 1. 安装

```bash
pip install -e ".[dev]"
```

### 2. 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```
DEEPSEEK_API_KEY=sk-你的Key
# 或用 OpenAI: OPENAI_API_KEY=sk-你的Key
# 或用 Anthropic: ANTHROPIC_API_KEY=sk-ant-你的Key
```

### 3. 切换模型

编辑 `config.yaml`：

```yaml
llm:
  default_model: deepseek/deepseek-chat   # 改成你用的模型
```

### 4. 启动

```bash
python run.py
```

## CLI 命令参考

### 基础命令

```bash
# 查看帮助
python run.py --help

# 查看版本
python run.py version
# 输出: JoJo Agent v0.1.0

# 查看完整配置
python run.py config
# 输出: 项目名、模型、Flash/Pro 配置、API Key 状态等
```

### 对话模式

```bash
python run.py chat
```

| 选项 | 功能 |
|------|------|
| `-c, --config PATH` | 指定配置文件（默认 `config.yaml`） |

对话内命令：

| 命令 | 功能 |
|------|------|
| `/verbose` | 开启/关闭 Thought → Action → Observation 全链可见 |
| `/allowall` | 写入操作不再逐个审批（高危操作仍拦截） |
| `/agents` | 列出可选 Agent 及其能力 |
| `/help` | 查看帮助 |
| `/exit` | 退出 |

示例：

```
$ python run.py chat

=======================================================
  JoJo Agent — Multi-Agent Chat Mode
  Flash: deepseek/deepseek-chat
  Pro:   deepseek/deepseek-chat
  Agents: researcher, coder
  /exit  /verbose  /allowall  /help  /agents
=======================================================

JoJo> 帮我搜索 Python 3.14 有什么新特性
Agent> [researcher 自动搜索并整理结果...]

JoJo> 写一个 2048 游戏保存到 game.py
Agent> [coder 自动写代码并保存...]
```

### Agent 管理

```bash
# 列出所有已注册的 Agent
python run.py agent list

# 输出:
# Available Agents:
#   researcher      — Searches the web, reads files, and gathers information...
#   coder           — Writes code, executes Python, reads and writes files...
```

### Skill 管理

```bash
# 列出所有已加载的 Skill
python run.py skill list

# 输出:
# Loaded 2 skills:
#   code-review     — Review code changes for security, bugs, and quality issues
#   daily-summary   — Generate a daily work summary from today's conversation...
```

### 多 Agent 编排

```bash
python run.py orchestrate --task <任务描述> [选项]
```

| 选项 | 值 | 说明 |
|------|-----|------|
| `--task` | `"任务描述"` | **必填**，要执行的任务 |
| `--mode` | `auto` (默认) | 自动分类 + 路由 + 模型选择 |
| | `sequential` | 流水线：Agent A → Agent B → Agent C |
| | `parallel` | 并行：多个实例同时执行子任务 |
| `--agents` | `researcher,coder` | 指定 Agent 名，逗号分隔 |

**自动模式（推荐）：**

```bash
# 让系统自动判断复杂度、选模型、选 Agent
python run.py orchestrate --task "搜索 Python 最新版本" --mode auto

# 等价于：
python run.py orchestrate --task "搜索 Python 最新版本"
```

**顺序模式（流水线）：**

```bash
# Researcher 先搜资料，结果传给 Coder 写报告
python run.py orchestrate \
  --task "研究 Python 异步编程现状并生成一份报告" \
  --mode sequential \
  --agents researcher,coder
```

**并行模式：**

```bash
# 用分号分隔多个子任务，同时执行
python run.py orchestrate \
  --task "对比 Python 的性能特点;对比 Go 的性能特点;对比 Rust 的性能特点" \
  --mode parallel \
  --agents researcher
```

## 对话模式

```bash
python run.py chat
```

对话自动启用多 Agent 路由：简单问题直接回复，复杂任务自动调度 Researcher（搜索）或 Coder（写代码）。

```
JoJo> 帮我搜索 Python 最新版本
Agent> [Orchestrator → researcher] 搜索结果...

JoJo> 写一个 2048 游戏
Agent> [Orchestrator → coder (Pro)] 代码已写入 game.py
```

### 对话中可用命令

| 命令 | 功能 |
|------|------|
| `/verbose` | 开启/关闭推理过程可见（Thought → Action → Observation） |
| `/allowall` | 写入操作不再逐个审批（高危操作仍拦截） |
| `/agents` | 列出可选 Agent |
| `/help` | 查看帮助 |
| `/exit` | 退出 |

## 多 Agent 编排

```bash
# 自动路由（推荐）
python run.py orchestrate --task "搜索 Python 最新版本" --mode auto

# 流水线（Researcher 搜完 → Coder 写）
python run.py orchestrate --task "..." --mode sequential --agents researcher,coder

# 并行（多个实例同时搜索）
python run.py orchestrate --task "查A;查B;查C" --mode parallel
```

### 可用 Agent

| Agent | 默认模型 | 能力 |
|-------|----------|------|
| **researcher** | Flash | 搜索信息、阅读文件、收集资料 |
| **coder** | Pro | 写代码、执行 Python、操作文件 |

### 自动模型选择

| 复杂度 | 使用模型 | 示例 |
|--------|----------|------|
| simple | Flash | "你好"、"1+1=?" |
| medium | Flash | "搜索 Python"、"读这个文件" |
| complex | Pro | "写 2048 游戏"、"分析数据并画图" |

## Skill 技能系统

Skill 是 Agent 的可复用能力包，Markdown 文件定义，对话中自动匹配。

```bash
# 查看已加载的 Skill
python run.py skill list
```

| Skill | 触发词 | 功能 |
|-------|--------|------|
| **code-review** | "review"、"审查代码" | 按安全→bug→质量→报告四步审查代码 |
| **daily-summary** | "daily"、"总结"、"日报" | 生成今日工作总结（完成/进行中/决策/学习） |

对话中自动匹配：

```
JoJo> 帮我 review 一下 src/jojo/agent/ 目录的代码
  [medium | deepseek-v4-flash | researcher | skills: code-review]
  → Agent 按 code-review Skill 定义的四步流程执行
```

### 人工审批

Agent 调用工具时自动判断风险等级：

| 风险等级 | 行为 | 示例工具 |
|----------|------|----------|
| `read` | 自动放行 | web_search, read_file, list_files |
| `write` | 弹出确认 | write_file |
| `dangerous` | 始终需确认 | execute_python |

提示示例：

```
  [Write] Agent wants to: write_file(path='report.md', content='...')
  [Y] Allow  [n] Deny  [a] Allow all in this session
```

## 内置工具

| 工具 | 功能 | 风险 |
|------|------|------|
| `web_search` | 搜索互联网（DuckDuckGo） | read |
| `read_file` | 读取文件 | read |
| `write_file` | 写入文件（沙箱约束） | write |
| `list_files` | 列出目录 | read |
| `execute_python` | 安全沙箱执行代码 | dangerous |

## 工作目录沙箱

所有文件操作被限制在项目根目录内，路径穿越（如 `../../etc/passwd`）自动拦截。

## 运行测试

```bash
pytest tests/ -v
```

## 项目结构

```
jojo_personal_assistant/
├── pyproject.toml          # Python 项目配置
├── config.yaml             # 用户配置（模型、参数...）
├── .env                    # API Key（不提交到 Git）
├── run.py                  # 启动入口
├── src/jojo/
│   ├── config.py           # 配置管理
│   ├── logger.py           # 日志系统
│   ├── models.py           # 数据模型
│   ├── cli.py              # CLI 入口
│   ├── llm/                # LLM 适配层
│   │   ├── provider.py     # 统一 LLM 调用接口
│   │   └── usage.py        # Token 用量追踪
│   ├── tools/              # 工具系统
│   │   ├── base.py         # Tool 基类 + @tool 装饰器
│   │   ├── schema.py       # 函数签名 → JSON Schema
│   │   ├── sandbox.py      # 工作目录沙箱
│   │   ├── registry.py     # 工具注册中心
│   │   └── builtin/        # 内置工具
│   │       ├── search.py   # web_search
│   │       ├── files.py    # read/write/list files
│   │       └── python.py   # execute_python
│   ├── agent/              # Agent 核心
│   │   ├── react_loop.py   # ReAct 循环引擎
│   │   ├── approval.py     # 人工审批
│   │   ├── prompt.py       # System Prompt 构建
│   │   └── guard.py        # 终止条件检测
│   ├── memory/             # 三层记忆系统
│   │   ├── working.py      # L1 工作记忆
│   │   ├── short_term.py   # L2 短期记忆
│   │   ├── long_term.py    # L3 长期记忆 (SQLite+ChromaDB)
│   │   ├── decay.py        # 遗忘曲线
│   │   └── manager.py      # MemoryManager
│   ├── orchestrator/       # 多 Agent 编排
│   │   ├── registry.py     # Agent 注册中心
│   │   ├── classifier.py   # 任务复杂度分类
│   │   ├── router.py       # Agent 路由
│   │   └── modes.py        # 顺序/路由/并行模式
│   ├── skills/             # Skill 系统
│   │   ├── models.py       # Skill 数据模型
│   │   ├── loader.py       # Markdown 解析
│   │   └── registry.py     # 匹配/发现
│   └── agents/             # 预置 Agent
│       ├── researcher.py   # Researcher (Flash)
│       └── coder.py        # Coder (Pro)
├── skills/                 # Skill 定义文件
│   ├── code/
│   │   └── code-review.md
│   └── productivity/
│       └── daily-summary.md
├── tests/
│   ├── test_llm.py
│   ├── test_tools.py
│   ├── test_agent.py
│   ├── test_memory.py
│   ├── test_multi_agent.py
│   └── test_skills.py
└── docs/
    ├── agent-framework-guide.md       # 框架设计文档
    ├── implementation-roadmap.md      # 实现路线图
    └── memory-system-comparison.md    # 记忆系统对比（面试参考）
```

## 当前进度

已完成阶段一 ~ 六（共十阶段）：

- ✅ 阶段一：项目基础
- ✅ 阶段二：LLM 适配层
- ✅ 阶段三：工具系统（含工作目录沙箱）
- ✅ 阶段四：单 Agent 核心循环（ReAct + 人工审批）
- ✅ 阶段五：三层记忆系统（含遗忘曲线）
- ✅ 阶段六：多 Agent 协作（自动路由 + 模型选择）
- ✅ 阶段七：Skill 技能系统（Markdown 定义，自动匹配）
- ⬜ 阶段八：MCP 协议集成
- ⬜ 阶段九：定时任务
- ⬜ 阶段十：打磨交付

详见 [docs/implementation-roadmap.md](docs/implementation-roadmap.md)
