# 个人 AI Agent 框架搭建指南

> 从概念到架构，从对比到实现，一份让你彻底理解 Agent 的文档。

***

## 目录

1. [Agent 是什么](#1-agent-是什么)
2. [Agent 推理架构模式 —— ReAct vs Plan-Execute vs 混合](#2-agent-推理架构模式--react-vs-plan-execute-vs-混合)
3. [主流框架全景对比](#3-主流框架全景对比)
4. [多 Agent 协作架构](#4-多-agent-协作架构)
5. [记忆系统深度解析](#5-记忆系统深度解析)
6. [推荐架构方案](#6-推荐架构方案)
7. [从零搭建步骤](#7-从零搭建步骤)
8. [扩展性设计](#8-扩展性设计)
9. [Skill 技能系统 —— Agent 的可复用能力包](#9-skill-技能系统--agent-的可复用能力包)
10. [MCP 协议集成 —— 连接外部工具的标准协议](#10-mcp-协议集成--连接外部工具的标准协议)
11. [总结](#11-总结)

***

## 1. Agent 是什么

### 1.1 一句话定义

**Agent = LLM + 工具 + 记忆 + 规划**

一个 AI Agent 是一个能够自主感知环境、做出决策、调用工具、并记住上下文的智能体。

### 1.2 核心循环 (Agent Loop)

```
┌─────────────────────────────────────────────────┐
│                  Agent Loop                      │
│                                                  │
│   用户输入                                        │
│      ↓                                           │
│   ┌──────────┐                                   │
│   │ 感知/理解 │ ← 从记忆系统检索相关上下文           │
│   └────┬─────┘                                   │
│        ↓                                         │
│   ┌──────────┐                                   │
│   │ 规划/推理 │ ← LLM 思考要做什么                  │
│   └────┬─────┘                                   │
│        ↓                                         │
│   ┌──────────┐                                   │
│   │ 工具调用  │ ← 执行具体操作 (搜索/代码/API...)    │
│   └────┬─────┘                                   │
│        ↓                                         │
│   ┌──────────┐                                   │
│   │ 观察结果  │ ← 获取工具返回的结果                 │
│   └────┬─────┘                                   │
│        ↓                                         │
│   ┌──────────┐                                   │
│   │ 反思/判断 │ ← 任务完成了? 还需要继续?           │
│   └────┬─────┘                                   │
│        ↓                                         │
│   完成 ← 或 → 回到"规划/推理"继续循环              │
│                                                  │
│   每一步都将关键信息存入记忆系统                     │
└─────────────────────────────────────────────────┘
```

### 1.3 Agent 的四大核心模块

| 模块              | 作用                      | 简单类比   |
| --------------- | ----------------------- | ------ |
| **LLM 大脑**      | 理解意图、推理规划、生成回复          | 人的大脑皮层 |
| **Tool 工具**     | 执行具体操作：搜索网页、读写文件、调用 API | 人的手和脚  |
| **Memory 记忆**   | 存储对话历史、用户偏好、任务上下文       | 人的海马体  |
| **Planning 规划** | 将大任务分解为小步骤，决定执行顺序       | 人的前额叶  |

***

## 2. Agent 推理架构模式 —— ReAct vs Plan-Execute vs 混合

### 2.1 为什么推理架构是 Agent 的灵魂

Agent 的核心循环不是只有一种写法。**不同的推理架构决定了 Agent 的智能程度、执行效率和可靠性。** 选错架构会导致：

- Agent 反复调用工具却无法完成任务（死循环）
- 简单任务耗时过长（过度规划）
- 复杂任务中途丢失上下文（规划不足）
- Token 消耗失控（每一步都带着全量历史）

**一个成熟的 Agent 框架必须支持多种推理模式，并根据任务复杂度自动切换。**

### 2.2 六大推理架构详解

#### 架构 1: ReAct (Reasoning + Acting) — 最经典

```
ReAct = 思考一步 → 执行一步 → 观察结果 → 再思考 → 再执行 → ...

┌──────────────────────────────────────────────────┐
│              ReAct Loop                           │
│                                                   │
│  Thought: "我需要知道今天的天气"                    │
│      ↓                                            │
│  Action: search_weather("北京", "2026-05-13")     │
│      ↓                                            │
│  Observation: "北京今日晴，22°C"                   │
│      ↓                                            │
│  Thought: "天气不错，建议用户出门散步"               │
│      ↓                                            │
│  Action: 无需更多操作                              │
│      ↓                                            │
│  Answer: "今天北京晴天22度，适合出门！"              │
│                                                   │
│  特点: 思考(Thought) → 行动(Action) → 观察(Obs)    │
└──────────────────────────────────────────────────┘
```

```python
# ReAct 的核心实现
class ReActAgent:
    async def run(self, user_input: str) -> str:
        messages = [
            {"role": "system", "content": """
            你使用 ReAct 模式解决问题。

            输出格式:
            Thought: <你的推理>
            Action: <tool_name>(<parameters>)
            Observation: <工具返回结果>
            ... (重复 Thought → Action → Observation)
            Final Answer: <最终回复>
            """},
            {"role": "user", "content": user_input},
        ]

        for _ in range(MAX_ITERATIONS):
            response = await self.llm.chat(messages)

            if "Final Answer:" in response:
                return extract_final_answer(response)

            # 解析 Action，执行工具
            action = parse_action(response)
            observation = await self.execute_tool(action)
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Observation: {observation}"})

        return "达到最大迭代次数"
```

| 优点         | 缺点                     |
| ---------- | ---------------------- |
| 简单直观，易于调试  | 每一步都要 LLM 调用，Token 消耗大 |
| 人类可读的推理链   | 复杂任务容易迷失（上下文窗口膨胀）      |
| 适合中等复杂度任务  | 无法并行执行独立步骤             |
| 每个步骤都有观察反馈 | 可能陷入循环                 |

**适用场景**: 信息检索、带工具的对话、代码调试

***

#### 架构 2: Plan-and-Execute — 先规划再执行

```
Plan-and-Execute = 先做完整计划 → 逐步执行 → 根据反馈调整

┌──────────────────────────────────────────────────┐
│         Plan-and-Execute                          │
│                                                   │
│  Step 1: 制定计划                                 │
│  Plan:                                            │
│    1. 搜索北京今日天气                             │
│    2. 根据天气推荐穿搭                             │
│    3. 检查是否有降雨，决定是否带伞                  │
│                                                   │
│  Step 2: 执行计划                                 │
│    ✓ 任务1: search_weather("北京") → 晴 22°C     │
│    ✓ 任务2: recommend_outfit(22°C, "晴") → T恤+薄外套│
│    ✓ 任务3: check_rain("北京") → 无雨            │
│                                                   │
│  Step 3: 汇总结果                                 │
│    "今天北京晴22度，穿T恤配薄外套即可，不用带伞"    │
│                                                   │
│  特点: 计划先行，执行在后，中间可调整               │
└──────────────────────────────────────────────────┘
```

```python
class PlanExecuteAgent:
    async def run(self, user_input: str) -> str:
        # Phase 1: 制定计划
        plan = await self._create_plan(user_input)
        # plan = [
        #     {"id": 1, "task": "搜索北京天气", "tool": "search_weather", "args": {...}},
        #     {"id": 2, "task": "推荐穿搭", "tool": "recommend_outfit", "args": {...}},
        # ]

        results = {}

        # Phase 2: 逐步执行并收集结果
        for step in plan:
            result = await self._execute_step(step)
            results[step["id"]] = result

            # 可选: 根据中间结果调整后续计划
            if self._need_replan(results):
                plan = await self._replan(plan, results)

        # Phase 3: 汇总生成最终答案
        return await self._summarize(user_input, plan, results)

    async def _create_plan(self, task: str) -> list[dict]:
        """让 LLM 生成一个结构化的执行计划"""
        response = await self.llm.chat([{
            "role": "system",
            "content": f"""将以下任务分解为可执行的步骤。
            可用工具: {self._tools_description()}

            输出 JSON 格式:
            [{{"id": 1, "task": "...", "tool": "...", "args": {{...}}}}]
            """,
        }, {"role": "user", "content": task}])
        return json.loads(response)
```

| 优点                | 缺点             |
| ----------------- | -------------- |
| 全局视野，不易跑偏         | 计划可能不符合实际情况    |
| 可以识别可并行的步骤        | 制定计划本身消耗 Token |
| 中间结果清晰，便于调试       | 动态变化的任务适应性差    |
| Token 消耗比 ReAct 低 | 简单任务会过度规划      |

**适用场景**: 旅行规划、研究调研、项目管理、多步骤工作流

***

#### 架构 3: ReWOO (Reasoning Without Observation) — 高效并行

```
ReWOO = 制定带占位符的计划 → 并行执行所有工具 → 用结果替换占位符 → 生成答案

┌──────────────────────────────────────────────────┐
│              ReWOO                                │
│                                                   │
│  Step 1: 制定计划（不执行，用占位符）              │
│  Plan:                                            │
│    #E1 = search_weather("北京")                   │
│    #E2 = search_air_quality("北京")               │
│    #E3 = search_traffic("北京")                   │
│                                                   │
│  Step 2: 并行执行（E1, E2, E3 同时跑！）           │
│    #E1 → "晴 22°C"                               │
│    #E2 → "AQI 45 优"                             │
│    #E3 → "路况畅通"                               │
│                                                   │
│  Step 3: 用结果替换占位符，生成答案                │
│    "北京今天晴22度，空气质量优，路况畅通"            │
│                                                   │
│  特点: 零观察依赖的步骤可以并行，大幅提速           │
└──────────────────────────────────────────────────┘
```

```python
class ReWOOAgent:
    async def run(self, user_input: str) -> str:
        # Step 1: 生成带占位符的计划
        plan_with_placeholders = await self.llm.chat([{
            "role": "system",
            "content": f"""制定计划，对可并行的工具调用使用占位符 #E1, #E2, ...
            计划中不要等待结果，直接列出所有需要的工具调用。
            输出格式:
            Plan:
            #E1 = tool_name(args)
            #E2 = tool_name(args)
            ...
            """,
        }, {"role": "user", "content": user_input}])

        # Step 2: 解析出所有工具调用
        tool_calls = self._parse_placeholders(plan_with_placeholders)

        # Step 3: 并行执行所有独立的工具调用
        results = await asyncio.gather(*[
            self.execute_tool(call) for call in tool_calls
            if not call.depends_on_others  # 无依赖的并行执行
        ])

        # Step 4: 用实际结果替换占位符
        final_prompt = self._substitute(plan_with_placeholders, results)

        # Step 5: 生成最终答案
        return await self.llm.chat([{
            "role": "user", "content": f"根据以下信息回答: {final_prompt}"
        }])
```

| 优点         | 缺点           |
| ---------- | ------------ |
| 并行执行，速度快   | 无法根据中间结果动态调整 |
| Token 消耗最低 | 占位符解析容易出错    |
| 适合信息聚合类任务  | 不适用需要条件分支的任务 |

**适用场景**: 信息聚合、对比分析、数据收集

***

#### 架构 4: Reflexion — 自我反思改进

```
Reflexion = ReAct + 自我批评 + 记忆重放

┌──────────────────────────────────────────────────┐
│              Reflexion                            │
│                                                   │
│  Episode 1:                                       │
│    Task: "写一个排序函数"                          │
│    Action: 写成冒泡排序                            │
│    Eval: 功能正确，但 O(n²) 不够高效               │
│    Reflection: "下次应该用更高效的算法"              │
│                                                   │
│  Episode 2 (带着上次的反思):                       │
│    Task: "写一个排序函数"                          │
│    Action: 写成快速排序                            │
│    Eval: O(n log n)，但代码可读性一般              │
│    Reflection: "可以加上注释解释分区逻辑"           │
│                                                   │
│  特点: 从失败中学习，越执行越好                     │
└──────────────────────────────────────────────────┘
```

```python
class ReflexionAgent:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reflections: list[str] = []  # 持久化的反思记忆

    async def run(self, user_input: str) -> str:
        # 将历史反思注入 system prompt
        reflection_context = "\n".join(
            f"过去的反思: {r}" for r in self.reflections[-5:]  # 最近5条
        )

        result = await super().run(user_input)

        # 自我评估
        evaluation = await self._evaluate(user_input, result)

        if evaluation["score"] < 0.7:
            # 生成反思
            reflection = await self._generate_reflection(
                user_input, result, evaluation
            )
            self.reflections.append(reflection)

            # 带着反思重试
            return await self.run(user_input)

        return result

    async def _evaluate(self, task: str, result: str) -> dict:
        """让 LLM 评估自己的输出质量"""
        response = await self.llm.chat([{
            "role": "system",
            "content": f"""评估以下任务完成质量 (0-1 分)。
            评估维度: 正确性、完整性、效率、清晰度

            任务: {task}
            结果: {result}

            输出 JSON: {{"score": 0.X, "issues": ["..."]}}
            """,
        }])
        return json.loads(response)
```

| 优点           | 缺点               |
| ------------ | ---------------- |
| 越用越聪明        | Token 消耗极大（多次重试） |
| 适合需要高质量输出的场景 | 延迟高（评估+反思+重试）    |
| 可累积经验        | 过度反思会导致犹豫不决      |

**适用场景**: 代码生成、写作、翻译等需要高质量输出的任务

***

#### 架构 5: LLMCompiler — 并行函数调用图

```
LLMCompiler = 分析依赖关系 → 构建 DAG → 并行执行无依赖节点

┌──────────────────────────────────────────────────┐
│           LLMCompiler (DAG 并行)                   │
│                                                   │
│  Task: "分析竞品A和竞品B，生成对比报告"              │
│                                                   │
│  DAG 依赖图:                                       │
│         ┌─────────────────┐                       │
│         │ search("竞品A") │                       │
│         └────────┬────────┘                       │
│                  ↓                                │
│  ┌───────────────────────────────┐                │
│  │  compare(A_data, B_data)      │ ← 等两个都完成  │
│  └───────────────────────────────┘                │
│                  ↑                                │
│         ┌─────────────────┐                       │
│         │ search("竞品B") │                       │
│         └─────────────────┘                       │
│                                                   │
│  search(A) 和 search(B) 无依赖 → 并行执行          │
│  compare 依赖两者 → 等待完成后执行                  │
│                                                   │
│  总耗时 = max(search时间) + compare时间            │
│  而非 search(A)时间 + search(B)时间 + compare时间 │
└──────────────────────────────────────────────────┘
```

```python
import networkx as nx

class LLMCompilerAgent:
    async def run(self, user_input: str) -> str:
        # Step 1: 生成 DAG 计划
        dag_plan = await self._generate_dag(user_input)
        # {
        #     "nodes": [
        #         {"id": 1, "tool": "search", "args": {"q": "竞品A"}},
        #         {"id": 2, "tool": "search", "args": {"q": "竞品B"}},
        #         {"id": 3, "tool": "compare", "args": {"a": "$1", "b": "$2"}},
        #     ],
        #     "edges": [[1, 3], [2, 3]]  # 1→3, 2→3 的依赖
        # }

        # Step 2: 构建依赖图
        G = nx.DiGraph()
        for node in dag_plan["nodes"]:
            G.add_node(node["id"], task=node)
        for src, dst in dag_plan["edges"]:
            G.add_edge(src, dst)

        # Step 3: 按拓扑顺序并行执行
        results = {}
        for level in self._topological_levels(G):
            # 同一层级的节点无依赖 → 并行执行
            level_results = await asyncio.gather(*[
                self._execute_node(G.nodes[nid]["task"], results)
                for nid in level
            ])
            for nid, result in zip(level, level_results):
                results[nid] = result

        # Step 4: 汇总
        return await self._summarize(results)

    def _topological_levels(self, G: nx.DiGraph) -> list[list[int]]:
        """返回拓扑排序的层级，每层内的节点可并行执行"""
        levels = []
        remaining = set(G.nodes())
        while remaining:
            # 找出所有入度为0的节点
            level = [n for n in remaining if G.in_degree(n) == 0]
            if not level:
                break  # 防止死循环
            levels.append(level)
            remaining -= set(level)
            G.remove_nodes_from(level)
        return levels
```

| 优点        | 缺点        |
| --------- | --------- |
| 最大化并行度    | 依赖分析可能不准确 |
| 理论最优的执行效率 | 实现复杂度高    |
| 适合复杂多步骤任务 | 调试困难      |

**适用场景**: 数据管道、复杂研究任务、多源信息融合

***

#### 架构 6: 混合自适应 (Adaptive Hybrid) — 我们的选择

```
混合模式 = 根据任务复杂度自动选择最合适的推理架构

┌──────────────────────────────────────────────────┐
│           Adaptive Hybrid Router                  │
│                                                   │
│  用户输入                                          │
│      ↓                                            │
│  ┌─────────────────┐                             │
│  │ 任务分类器       │                             │
│  │ (LLM 快速判断)   │                             │
│  └────────┬────────┘                             │
│           ↓                                       │
│  ┌─────────────────────────────────────┐         │
│  │  简单任务 (1-2步)                    │         │
│  │  → Direct Answer (零工具调用)       │         │
│  │  → 延迟: 1-2s, Cost: $              │         │
│  ├─────────────────────────────────────┤         │
│  │  中等任务 (3-5步，无并行机会)         │         │
│  │  → ReAct                            │         │
│  │  → 延迟: 3-8s, Cost: $$             │         │
│  ├─────────────────────────────────────┤         │
│  │  信息聚合任务 (多源查询，可并行)      │         │
│  │  → ReWOO                            │         │
│  │  → 延迟: 2-4s, Cost: $$             │         │
│  ├─────────────────────────────────────┤         │
│  │  复杂多步骤任务 (有依赖关系)          │         │
│  │  → LLMCompiler (DAG 并行)           │         │
│  │  → 延迟: 5-10s, Cost: $$$           │         │
│  ├─────────────────────────────────────┤         │
│  │  高质量要求任务 (需反复打磨)          │         │
│  │  → Reflexion                        │         │
│  │  → 延迟: 10-30s, Cost: $$$$         │         │
│  └─────────────────────────────────────┘         │
│                                                   │
└──────────────────────────────────────────────────┘
```

```python
from enum import Enum

class ReasoningMode(Enum):
    DIRECT = "direct"           # 直接回复，不调工具
    REACT = "react"             # 思考-行动-观察循环
    REWOO = "rewoo"             # 先计划占位，后并行执行
    LLM_COMPILER = "llm_compiler"  # DAG 依赖图并行
    REFLEXION = "reflexion"     # 自我反思迭代
    PLAN_EXECUTE = "plan_execute"  # 先规划再执行

class AdaptiveAgent:
    """
    自适应 Agent — 根据任务自动选择推理模式

    这是推荐在你自己的框架中采用的设计。
    """

    def __init__(self):
        self.mode_handlers = {
            ReasoningMode.DIRECT: DirectHandler(),
            ReasoningMode.REACT: ReActHandler(),
            ReasoningMode.REWOO: ReWOOHandler(),
            ReasoningMode.LLM_COMPILER: LLMCompilerHandler(),
            ReasoningMode.REFLEXION: ReflexionHandler(),
            ReasoningMode.PLAN_EXECUTE: PlanExecuteHandler(),
        }

    async def run(self, user_input: str) -> str:
        # 1. 任务分类
        mode = await self._classify_task(user_input)

        # 2. 根据模式选择处理器
        handler = self.mode_handlers[mode]

        # 3. 执行
        return await handler.execute(user_input)

    async def _classify_task(self, user_input: str) -> ReasoningMode:
        """快速分类任务，选择合适的推理模式"""
        response = await self.llm.chat([{
            "role": "system",
            "content": f"""分析以下任务的复杂度，选择合适的推理模式:

            - direct: 简单问答，不需要工具 (如: "你好", "Python是什么")
            - rewoo: 需要从多个来源收集信息，信息源之间独立 (如: "对比A和B")
            - react: 需要逐步推理，上一步结果影响下一步 (如: "帮我调试这段代码")
            - llm_compiler: 复杂多步骤任务，部分步骤可并行 (如: "研究X并生成报告")
            - reflexion: 需要高质量输出，能接受较长时间 (如: "写一篇重要文章")
            - plan_execute: 需要先制定详细计划 (如: "帮我规划一个项目")

            只输出模式名称，不要解释。
            """
        }, {"role": "user", "content": user_input}])

        # 解析 LLM 返回的模式
        mode_str = response.strip().lower()
        for mode in ReasoningMode:
            if mode.value in mode_str:
                return mode
        return ReasoningMode.REACT  # 默认用 ReAct

    # 用户也可以手动指定模式
    async def run_with_mode(
        self, user_input: str, mode: ReasoningMode
    ) -> str:
        handler = self.mode_handlers[mode]
        return await handler.execute(user_input)
```

### 2.3 六大架构全面对比

| 维度           | ReAct   | Plan-Execute | ReWOO  | Reflexion | LLMCompiler | Adaptive Hybrid |
| ------------ | ------- | ------------ | ------ | --------- | ----------- | --------------- |
| **执行速度**     | 中等      | 较快           | 快      | 慢         | 快           | **根据任务自适应**     |
| **Token 消耗** | 高       | 中等           | 低      | 极高        | 中等          | **按需分配**        |
| **任务适应性**    | 中等      | 好            | 弱      | 好         | 好           | **最优**          |
| **并行能力**     | 无       | 有限           | 强      | 无         | 强           | **按需启用**        |
| **简单任务效率**   | 差(过度思考) | 差(过度规划)      | 差(不必要) | 极差        | 差           | **好(自动降级)**     |
| **实现复杂度**    | 低       | 低            | 中等     | 中等        | 高           | 高               |
| **自我改进**     | 无       | 无            | 无      | 强         | 无           | **可扩展**         |
| **调试难度**     | 低       | 低            | 中等     | 中等        | 高           | 中等              |

### 2.4 推荐的框架策略

```
我们的框架采用: 默认 ReAct + 可选模式切换 + 自动模式路由

Phase 1 (最先实现):
└── ReAct — 作为默认推理引擎
    理由: 简单、可解释、适用范围广、容易 debug

Phase 2 (1周后加入):
├── ReWOO — 用于信息聚合类任务
└── Plan-Execute — 用于多步骤规划类任务

Phase 3 (后续扩展):
├── LLMCompiler — 用于复杂并行任务
├── Reflexion — 用于需要高质量输出的场景
└── 自动模式路由 — LLM 自动判断用哪种模式

总原则: 简单任务不要过度设计，复杂任务不要简单处理
```

### 2.5 为什么默认选 ReAct 而不是其他

```
1. ReAct 是 Agent 界的 "Hello World"
   所有 LLM 都理解 Thought → Action → Observation 格式
   不需要额外训练或微调

2. 人类可读的推理链
   Thought: "我需要先查天气..."
   这让 debug 变得极其简单 — 你能看到 Agent 的"内心独白"

3. 最大兼容性
   所有 Function Calling 模型天然支持 ReAct
   OpenAI、Anthropic、Google 等所有厂商都兼容

4. 渐进增强
   ReAct 是所有其他模式的 Fallback
   当 ReWOO 的占位符解析出错 → Fallback 到 ReAct
   当 LLMCompiler 的依赖图不合理 → Fallback 到 ReAct
```

***

## 3. 主流框架全景对比

### 3.1 框架一览

| 框架                  | 语言             | 定位           | 多Agent     | 记忆系统                            | 学习曲线 | 适用场景       |
| ------------------- | -------------- | ------------ | ---------- | ------------------------------- | ---- | ---------- |
| **LangChain**       | Python/JS      | 通用 LLM 应用框架  | 需自己实现      | ConversationBuffer/MemoryVector | 陡峭   | 原型到生产      |
| **LangGraph**       | Python/JS      | 有状态多Agent工作流 | 原生支持       | 需自己实现                           | 中等   | 复杂流程       |
| **CrewAI**          | Python         | 多Agent协作框架   | 角色分工+顺序/层级 | 短期+长期+实体记忆                      | 低    | 快速搭建多Agent |
| **AutoGen**         | Python         | 对话式多Agent    | 对话驱动+群聊模式  | 需自己实现                           | 中等   | 微软生态       |
| **Dify**            | 可视化            | 低代码平台        | 工作流编排      | 内置对话变量                          | 极低   | 非开发者/快速验证  |
| **Coze**            | 可视化            | 字节跳动平台       | 插件+工作流     | 内置知识库                           | 极低   | 国内场景/快速上线  |
| **Semantic Kernel** | C#/Python/Java | 企业级AI编排      | Planner+流程 | 内置MemoryStore                   | 中等   | 微软/.NET生态  |
| **Agno**            | Python         | 轻量高性能Agent   | 原生多Agent   | 内置Session/AKV                   | 低    | 追求性能与简洁    |

### 3.2 核心维度深度对比

#### 3.2.1 LangChain / LangGraph

```
优点:
├── 生态最丰富，集成最多 (600+ 工具集成)
├── LCEL (LangChain Expression Language) 声明式构建链
├── LangGraph 处理有状态、有分支的复杂流程
└── LangSmith 提供调试追踪能力

缺点:
├── 抽象层太多，代码深追困难
├── 版本迭代快，Breaking Change 多
├── 过度封装，简单任务也写很多代码
└── 学习曲线陡峭

适合: 需要大量第三方集成的生产项目
```

#### 3.2.2 CrewAI

```
优点:
├── 上手极快，5分钟跑通第一个多Agent
├── 角色定义清晰 (Role/Goal/Backstory)
├── 内置多种协作策略 (sequential, hierarchical)
└── 内置记忆系统 (短期/长期/实体/用户)

缺点:
├── 灵活性相对受限，自定义程度不如 LangGraph
├── 复杂流程控制力弱
├── 社区不如 LangChain 成熟
└── 调试困难（黑盒感强）

适合: 快速验证多Agent协作场景，原型开发
```

#### 3.2.3 AutoGen (Microsoft)

```
优点:
├── 对话驱动，Agent 之间通过对话协作
├── 群聊模式 (GroupChat) 让多个 Agent 同时参与
├── 人机协作 (Human-in-the-loop) 设计完善
└── 代码生成和执行一体

缺点:
├── 学习成本不低
├── 概念体系独特 (ConversableAgent, AssistantAgent...)
├── 国内访问相关服务可能受限
└── 记忆系统需要自己集成

适合: 需要人机协作的复杂对话场景
```

#### 3.2.4 Agno (前身为 Phidata)

```
优点:
├── 非常轻量，代码简洁直观
├── 性能优秀（比 LangChain 快 2-10x）
├── 多模态支持好 (文本/图片/音频/视频)
├── 内置 Memory、Knowledge (RAG)、Tools
└── 原生支持 Team (多Agent协作)

缺点:
├── 相对较新，社区较小
├── 文档不够完善
└── 生产案例较少

适合: 追求性能和代码简洁的项目
```

#### 3.2.5 Dify / Coze (低代码平台)

```
优点:
├── 零代码搭建，拖拽式工作流
├── 内置 RAG 知识库、工具市场
├── 可视化调试和日志
└── Coze 国内可直接使用

缺点:
├── 定制能力有限
├── 依赖平台，无法完全自控
├── 高级功能收费
└── 不适合深度定制需求

适合: 非技术人员 / 快速验证想法 / 简单业务场景
```

### 3.3 我的推荐排名

| 排名    | 框架            | 推荐理由                    |
| ----- | ------------- | ----------------------- |
| **1** | **自己搭建**      | 完全可控、深度理解、极致扩展性         |
| **2** | **Agno**      | 轻量高性能，代码直观，适合 Python 项目 |
| **3** | **LangGraph** | 复杂工作流首选，生态完善            |
| **4** | **CrewAI**    | 快速原型，5 分钟用起来            |

***

## 4. 多 Agent 协作架构

### 4.1 三种经典协作模式

```
模式 1: 顺序执行 (Sequential)
─────────────────────────────────
Agent A → Agent B → Agent C → 结果

场景: 写一篇文章
  研究员 → 搜索资料
  写手   → 基于资料写文章
  编辑   → 审校修改 → 输出最终稿

特点: 简单、可预测、适合流水线任务


模式 2: 层级调度 (Hierarchical)
─────────────────────────────────
           Orchestrator (调度者)
          /        |        \
     Agent A   Agent B   Agent C
          \        |        /
           结果汇总 → Orchestrator 判断

场景: 复杂软件开发
  架构师   → 设计方案
  程序员A  → 实现模块A
  程序员B  → 实现模块B
  测试员   → 测试集成
  架构师   → 审核通过/打回修改

特点: 灵活、适合复杂任务、需要调度逻辑


模式 3: 群聊协作 (Group Chat)
─────────────────────────────────
     Agent A ←→ Agent B
       ↕          ↕
     Agent C ←→ Agent D
       (共享上下文 + 自由对话)

场景: 头脑风暴
  4个Agent同时讨论一个方案，各自提出观点
  最终由主持人总结

特点: 自然、涌现性强、控制难度高
```

### 4.2 多 Agent 通信机制

```
┌──────────────────────────────────────────────┐
│              通信方式                          │
│                                               │
│  1. 消息传递 (Message Passing)                 │
│     Agent 之间通过结构化的消息对象通信           │
│     {from, to, type, content, metadata}       │
│                                               │
│  2. 共享黑板 (Blackboard)                     │
│     一个公共的数据空间，Agent 读写共享          │
│     适合需要全局状态的场景                      │
│                                               │
│  3. 事件驱动 (Event Bus)                      │
│     Agent 发布/订阅事件，松耦合通信              │
│     适合异步、解耦的场景                        │
│                                               │
│  4. 任务队列 (Task Queue)                     │
│     任务入队，Agent 竞争消费                    │
│     适合负载均衡、并行处理的场景                 │
└──────────────────────────────────────────────┘
```

### 4.3 多 Agent 的核心挑战

| 挑战          | 描述                 | 解决思路                |
| ----------- | ------------------ | ------------------- |
| **上下文窗口爆炸** | 多Agent对话历史迅速膨胀     | 摘要压缩、分层记忆、滑动窗口      |
| **幻觉传播**    | 一个Agent的错误被下游放大    | 验证节点、交叉审查、置信度标注     |
| **死循环**     | Agent 之间反复调用无法终止   | 最大轮次限制、终止条件检测       |
| **任务分配**    | 谁做什么难以自动决策         | LLM调度 + 能力声明 + 匹配算法 |
| **成本控制**    | 多Agent = 多倍 API 调用 | 小模型做简单任务、缓存复用       |
| **状态一致性**   | 并行Agent修改同一数据的冲突   | 锁机制、乐观锁、CRDT        |

***

## 5. 记忆系统深度解析

### 5.1 记忆分层模型

这是目前业界最主流的记忆设计，类似于人脑的记忆结构：

```
┌─────────────────────────────────────────────────────────┐
│                    记忆系统分层                           │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │          WORKING MEMORY (工作记忆)                │    │
│  │  当前对话窗口内的上下文，直接注入 Prompt            │    │
│  │  容量: ~100K tokens (取决于模型上下文窗口)         │    │
│  │  生命周期: 单次对话                                │    │
│  │  内容: 本轮消息历史 + 工具调用结果                   │    │
│  └─────────────────────────────────────────────────┘    │
│                         ↑  ↓                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │        SHORT-TERM MEMORY (短期记忆)               │    │
│  │  跨轮次会话的摘要和关键信息                        │    │
│  │  存储: Redis / 内存缓存                           │    │
│  │  生命周期: 一次会话 (几小时到几天)                  │    │
│  │  内容: 会话摘要 + 关键决策 + 中间结果               │    │
│  └─────────────────────────────────────────────────┘    │
│                         ↑  ↓                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │        LONG-TERM MEMORY (长期记忆)                │    │
│  │  持久化的知识、偏好、经验                          │    │
│  │  存储: 向量数据库 + SQL + 文件系统                 │    │
│  │  生命周期: 永久                                    │    │
│  │  内容: 用户偏好、学习到的规则、知识库               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 各类记忆的实现方案

```
SHORT-TERM MEMORY (短期记忆)
├── 方案1: 滑动窗口
│   保留最近 N 轮对话，旧的丢弃
│   简单但会丢失较早的信息
│
├── 方案2: 摘要压缩
│   用 LLM 将长对话压缩成摘要
│   保留语义信息但丢失细节
│
└── 方案3: 关键信息提取 (推荐)
    用 LLM 提取关键事实、决策、承诺
    结构化存储，精准检索
    兼顾效率和完整度

LONG-TERM MEMORY (长期记忆)
├── 方案1: 向量检索 (Semantic Memory)
│   text → embedding → 向量数据库
│   适合: "我记得我们讨论过类似的事情..."
│   技术: ChromaDB / Qdrant / Milvus / pgvector
│
├── 方案2: 结构化存储 (Episodic Memory)
│   存储为结构化记录
│   {event, timestamp, agents, decisions, outcome}
│   适合: "上次修复这个 bug 用了什么思路？"
│   技术: SQLite / PostgreSQL
│
├── 方案3: 知识图谱 (Semantic Network)
│   实体 + 关系构成图结构
│   User → works_on → Project → uses → Technology
│   适合: 复杂关系的推理和查询
│   技术: Neo4j / NetworkX
│
└── 方案4: 文件记忆 (Document Memory)
    直接读写文件系统
    适合: 持久化配置、规则、偏好
    技术: JSON / YAML / Markdown 文件
```

### 5.3 记忆检索策略

```
用户输入 → 多路召回 → 融合排序 → 注入Prompt

多路召回包含:
├── 关键词匹配 (BM25)         → 精准匹配
├── 向量相似度 (Embedding)    → 语义匹配
├── 时间衰减 (最近优先)        → 时效性
├── 重要性加权 (关键事件优先)  → 重要度
└── 用户/任务标签过滤          → 相关性

融合排序: 综合多路召回的结果，重排序后取 Top-K
注入Prompt: 将记忆片段格式化后拼入 System Prompt
```

### 5.4 业界记忆系统方案对比（2025-2026）

> 以下分析覆盖了当前主流的 Agent 记忆框架和学术前沿方案。

#### 5.4.1 框架速览

| 框架 | GitHub Star | 技术路线 | 最佳场景 |
|------|-------------|----------|----------|
| **Mem0** | 42.6K+ | 向量检索 + 自动抽取流水线 | 轻量级、15分钟集成 |
| **Letta (MemGPT)** | 19K+ | OS式记忆层级 (Core/Archival/Recall) | 长文档、白盒可观测 |
| **Zep** | — | 时序知识图谱 (Graphiti引擎) | 企业级、多数据源融合 |
| **Hermes Agent** | 50K+ | SQLite + FTS5 + LLM摘要 + 遗忘曲线 | 个人助手、本地持久化 |
| **MemOS** | — | 神经张量记忆 (MemCube) | 前沿研究、可训练记忆 |
| **EverMemOS** | — | 仿生四层记忆架构 | SOTA精度 |
| **Supermemory** | 13.2K | 知识图谱 + 遗忘机制 | 个人第二大脑 |
| **Qdrant** | 21K+ | 纯向量数据库 (Rust) | 自定义记忆方案底座 |

#### 5.4.2 技术路线分化

**路线一：操作系统式记忆（Letta / MemOS / EverMemOS）**

将记忆类比为计算机的存储层级 — 主上下文 = RAM，外存 = 硬盘，Agent 自主通过函数调用在两层间换入换出信息。

```
Letta 三级记忆:
┌──────────────────────────────────────┐
│  Core Memory (RAM)                   │
│  当前对话块 + 工具结果                │
│  容量: LLM 上下文窗口                │
├──────────────────────────────────────┤
│  Archival Memory (HDD)               │
│  无限容量的长期存储                    │
│  通过 search/read 函数按需加载        │
├──────────────────────────────────────┤
│  Recall Memory (Cache)               │
│  智能预取的上下文块                   │
│  预测式加载，减少检索延迟              │
└──────────────────────────────────────┘
```

- **Letta** 在 LoCoMo 基准测试中，仅用文件系统 + gpt-4o-mini 即达 **74.0%** 准确率，超越全上下文基线（72.9%）
- **EverMemOS** 达 LoCoMo **92.3%**，是目前唯一显著超越 Full-context 上限的记忆系统

**路线二：知识图谱关联网络（Zep / Mem0Graph / Supermemory）**

将记忆表示为实体-关系-实体的图结构，支持时序演化和矛盾检测：

```
User → works_on → Project → uses → Technology
  │                              │
  └── prefers ──→ Python ←── belongs_to
```

- **Zep** 在 LongMemEval 上达 **94.8%**，检索延迟 < 200ms
- 自动标记失效事实（`invalid_at`），保留历史演化轨迹
- **Mem0Graph** 用 LLM 自动提取三元组，带冲突检测，LoCoMo **68.4%**

**路线三：本地持久化 + 混合检索（Hermes Agent）**

Hermes Agent 由 Nous Research 于 2025 年 2 月开源，GitHub 50K+ stars，采用完全本地化的记忆方案：

```
Hermes 记忆架构:
┌──────────────────────────────────────────┐
│  SQLite + FTS5 全文检索                  │
│  ├── 倒排索引 → 毫秒级关键词命中          │
│  └── 向量检索 → 语义相似匹配              │
├──────────────────────────────────────────┤
│  LLM 摘要压缩                            │
│  ├── 存储空间降低 82%                     │
│  └── 关键信息完整度 95%+                  │
├──────────────────────────────────────────┤
│  渐进遗忘（艾宾浩斯曲线）                   │
│  ├── 按记忆年龄和访问频率计算衰减权重        │
│  └── 低于阈值的记忆自动淘汰                │
├──────────────────────────────────────────┤
│  自我进化                                 │
│  └── Agent 在执行中自主创建技能并持久化      │
└──────────────────────────────────────────┘
```

核心特色：
- **完全本地运行** — SQLite 文件 + FTS5 引擎，无需外部向量数据库
- **跨会话记忆** — 下次启动自动恢复之前的交互上下文
- **艾宾浩斯遗忘** — 不常访问的记忆随时间衰减，模拟人脑的记忆曲线
- **自主进化** — Agent 在实践中自动提炼技能、保存经验，形成正向飞轮

**路线四：学术前沿 — MEMTIER（OpenClaw 运行时）**

2026 年 5 月随 OpenClaw 项目发布的 MEMTIER 论文（arXiv: 2605.03675）是目前最严谨的记忆架构研究之一：

| 组件 | 功能 |
|------|------|
| Episodic JSONL Store | 结构化情节记忆存储 |
| 5-Signal Weighted Retrieval | 五维度信号加权检索（语义、时序、重要性、频率、上下文） |
| Attention-Attributed Weight Update | 基于注意力信号的动态权重更新 |
| Async Consolidation Daemon | 后台异步将情节记忆提升为语义记忆 |
| PPO-Based Policy | 用强化学习自适应调整检索权重 |

**LongMemEval-S（500题）上的表现：**

| 方案 | 准确率 |
|------|--------|
| Full-context baseline | 5.0% |
| MEMTIER（Qwen2.5-7B, 6GB GPU） | **38.2%** |
| MEMTIER + DeepSeek-V4-Flash | **68.6% – 71.4%** |
| GPT-4o + RAG BM25（对比） | 56.0% |

关键发现：工具执行成功率在 72 小时运行窗口内下降 **14 个百分点** — MEMTIER 的三层加权架构有效缓解了此问题。全部在消费级笔记本（6GB GPU）上运行。

#### 5.4.3 关键基准测试横评

**LoCoMo 基准（2025 年 4 月）— 评估长对话记忆能力：**

| 系统 | 准确率 | 中位延迟 | P95 延迟 |
|------|--------|----------|----------|
| Full-context（上限） | 72.9% | 9.87s | 17.12s |
| **Letta Filesystem** | **74.0%** | — | — |
| EverMemOS | **92.3%** | — | — |
| Mem0Graph（图增强） | 68.4% | 1.09s | 2.59s |
| Mem0（向量版） | 66.9% | 0.71s | 1.44s |

**LongMemEval 基准 — 评估企业级跨会话记忆：**

| 系统 | 得分 |
|------|------|
| MemPalace | ~96.6% |
| Zep | **94.8%** |
| Letta/MemGPT | 83.2% |

#### 5.4.4 对 JoJo 框架的启示

综合以上分析，对当前框架的记忆系统设计有以下关键启示：

**1. Agent 能力 > 检索机制**

Letta 的研究表明，Agent 能否有效使用工具（知道何时调用 search/read，如何组织检索）比底层用向量库还是知识图谱更重要。简单的文件系统工具 + 强 Agent 设计，即可超越复杂的专用记忆工具。

→ **JoJo 策略**: 不需要引入重量级外部记忆框架，直接使用 ChromaDB + SQLite 即可。关键是给 Agent 配好记忆检索工具（`search_memory`、`recall_context`），让它自主决定什么时候查、怎么查。

**2. 遗忘 = 精准，而非缺陷**

EverMemOS 证明，高质量的记忆抽取反而比把所有历史扔给 LLM（Full-context）效果更好 — 过多的上下文会稀释模型注意力。Hermes Agent 的艾宾浩斯遗忘机制也印证了这点。

→ **JoJo 策略**: 实现"提取关键信息 → 按重要性衰减 → 低价值淘汰"的闭环，而非简单的"全部存储"。

**3. 混合检索 > 纯向量检索**

Mem0、Zep、agentmemory 的实践都表明：BM25 关键词 + 向量语义 + 时间衰减 + 重要性加权的多路召回 > 纯向量检索。

→ **JoJo 策略**: 短期记忆用关键词 + 时间衰减，长期记忆用 ChromaDB 向量 + 时间戳排序。

**4. 本地优先、SQLite 为王**

Hermes Agent 50K+ stars 的成功证明：个人 Agent 不需要分布式向量数据库。SQLite FTS5 + 本地向量库足够覆盖绝大多数场景。

→ **JoJo 策略**: SQLite 做主存储、ChromaDB 做语义检索引擎，全部本地化。

***

## 6. 推荐架构方案

### 6.1 总体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI / API / Web UI                       │
│                          (用户入口层)                              │
├──────────────────────────────────────────────────────────────────┤
│                       ORCHESTRATOR (调度层)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ 任务规划器    │  │ Agent 路由器  │  │ 执行监视器             │  │
│  │ Task Planner │  │ Agent Router │  │ Execution Monitor     │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    AGENT REGISTRY (Agent 注册中心)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 通用Agent │  │ 代码Agent │  │ 搜索Agent │  │ 自定义... │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
├──────────────────────────────────────────────────────────────────┤
│                      TOOL REGISTRY (工具注册中心)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 网页搜索  │  │ Python执行│  │ 文件操作  │  │ HTTP请求 │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
├──────────────────────────────────────────────────────────────────┤
│                      MEMORY SYSTEM (记忆系统)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Working Mem  │  │ Short-Term   │  │ Long-Term Memory   │    │
│  │ (消息历史)    │  │ (会话摘要)    │  │ (向量库+SQL+文件)  │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE (基础设施)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ LLM 适配器│  │ 日志/追踪 │  │ 定时任务  │  │ 配置管理  │        │
│  │ (多模型)  │  │ (可观测)  │  │ (Cron)   │  │ (YAML)   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 为什么推荐自己搭建

| 维度       | 使用框架       | 自己搭建         |
| -------- | ---------- | ------------ |
| **理解深度** | 浅，只懂 API   | 深，懂每个细节      |
| **定制能力** | 受框架限制      | 完全自由         |
| **性能优化** | 框架额外开销     | 极简，按需优化      |
| **问题排查** | 堆栈深，难追踪    | 代码自己写的，秒定位   |
| **学习价值** | 低          | 极高           |
| **前期投入** | 低          | 中等（2-3天搭建核心） |
| **长期收益** | 低（受制于框架演进） | 高（资产完全自主）    |

### 6.3 技术选型

```
核心框架:       Python 3.12+
LLM 适配:      litellm (统一多模型接口)
数据验证:       Pydantic v2 (类型安全)
存储:
  ├── SQLite        → 结构化数据 (会话、用户、任务)
  ├── ChromaDB      → 向量存储 (长期记忆、知识库)
  └── JSON/YAML     → 配置文件
异步:           asyncio + anyio
定时任务:        APScheduler (支持 Cron 表达式)
日志:           loguru
CLI:           rich + typer
```

***

## 7. 从零搭建步骤

### 第一步：定义核心抽象 (预计 2-3 小时)

```python
# 核心概念的精确定义

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

# 1. Message - 消息是最基础的通信单元
class Message(BaseModel):
    role: str           # "user" | "assistant" | "system" | "tool"
    content: str
    metadata: dict = {} # 时间戳、来源Agent等

# 2. Tool - 工具是Agent的手和脚
class Tool(BaseModel):
    name: str
    description: str
    parameters: dict     # JSON Schema 格式
    function: callable   # 实际执行的函数

# 3. Agent - 智能体是核心
class Agent(ABC):
    name: str
    description: str
    system_prompt: str
    tools: list[Tool]
    memory: "MemoryManager"

    @abstractmethod
    async def run(self, input: str) -> str:
        """Agent 的主循环"""

# 4. Memory - 记忆系统
class MemoryManager(ABC):
    @abstractmethod
    async def add(self, message: Message) -> None: ...
    @abstractmethod
    async def retrieve(self, query: str, top_k: int) -> list[Message]: ...
    @abstractmethod
    async def summarize(self) -> str: ...
```

### 第二步：实现 LLM 适配层 (1-2 小时)

```python
# 为什么用 litellm：
# 一行代码切换模型 — "openai/gpt-4o" → "anthropic/claude-sonnet-4-6"
# 不需要改任何业务代码

import litellm

class LLMProvider:
    """统一 LLM 调用接口"""

    def __init__(self, model: str = "openai/gpt-4o"):
        self.model = model

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> dict:
        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
        )
        return response.choices[0].message

    async def stream(self, messages: list[dict]) -> ...:
        """流式输出，打字机效果"""
        ...
```

### 第三步：实现 Agent 核心循环 (2-3 小时)

```python
class SimpleAgent:
    """
    核心循环逻辑：
    1. 接收输入
    2. 检索相关记忆
    3. 构建 Prompt（系统提示 + 记忆 + 当前输入）
    4. 调用 LLM
    5. 如果需要调工具 → 执行工具 → 观察结果 → 回到步骤 4
    6. 输出最终回复
    7. 保存到记忆
    """

    async def run(self, user_input: str) -> str:
        MAX_ITERATIONS = 10  # 防止死循环

        # 检索相关记忆
        memories = await self.memory.retrieve(user_input, top_k=5)
        context = self._build_context(user_input, memories)

        messages = [{"role": "system", "content": context}]

        for i in range(MAX_ITERATIONS):
            response = await self.llm.chat(messages, tools=self.tools_schema)

            if response.tool_calls:
                # 需要调用工具
                for tc in response.tool_calls:
                    result = await self._execute_tool(tc)
                    messages.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tc.id,
                    })
                continue  # 继续循环，让 LLM 处理工具结果

            # 没有工具调用 = 最终回复
            final_answer = response.content
            await self.memory.add(Message(role="user", content=user_input))
            await self.memory.add(Message(role="assistant", content=final_answer))
            return final_answer

        raise RuntimeError("Agent 超过最大迭代次数")
```

### 第四步：实现多 Agent 协作 (2-3 小时)

```python
class Orchestrator:
    """
    多 Agent 调度器 — 三种模式：
    1. Sequential: 管道式顺序执行
    2. Router: 按能力路由到最合适的 Agent
    3. Parallel: 并行分派给多个 Agent，汇总结果
    """

    def __init__(self):
        self.agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    async def sequential(self, task: str, agent_names: list[str]) -> str:
        """管道模式：Agent A → Agent B → Agent C"""
        result = task
        for name in agent_names:
            agent = self.agents[name]
            result = await agent.run(result)
        return result

    async def route(self, task: str) -> str:
        """路由模式：LLM 选择最合适的 Agent"""
        capabilities = "\n".join(
            f"- {a.name}: {a.description}" for a in self.agents.values()
        )
        prompt = f"根据任务选择合适的Agent:\n{capabilities}\n\n任务: {task}"
        agent_name = await self.llm.chat([{"role": "user", "content": prompt}])
        return await self.agents[agent_name].run(task)

    async def parallel(self, task: str, agent_names: list[str]) -> str:
        """并行模式：多个 Agent 同时处理，合并结果"""
        results = await asyncio.gather(*[
            self.agents[name].run(task) for name in agent_names
        ])
        # 让 LLM 合并多个结果
        return await self._merge_results(task, results)
```

### 第五步：实现记忆系统 (2-3 小时)

```python
class MemorySystem:
    """三层记忆系统"""

    def __init__(self):
        # 工作记忆 → 内存中
        self.working: list[Message] = []

        # 短期记忆 → Redis 或内存缓存
        self.short_term = ShortTermMemory(ttl=3600)  # 1小时过期

        # 长期记忆 → 向量数据库 + SQLite
        self.vector_store = ChromaDB(collection="memories")
        self.db = aiosqlite.connect("memory.db")

    async def add(self, msg: Message) -> None:
        self.working.append(msg)

        # 自动压缩：当工作记忆超过阈值，压缩到短期记忆
        if len(self.working) > 20:
            summary = await self._compress(self.working)
            await self.short_term.save(summary)

        # 提取可长期保留的关键信息
        key_info = await self._extract_key_info(msg)
        if key_info:
            embedding = await self.embed(key_info)
            await self.vector_store.add(embedding, metadata=msg.metadata)

    async def retrieve(self, query: str, k: int = 5) -> list[Message]:
        # 多路召回
        vector_results = await self.vector_store.search(query, k)
        recent = self.working[-10:]  # 最近10条
        short = await self.short_term.get_recent()

        # 融合去重排序
        return self._fuse_and_rank(vector_results, recent, short)[:k]
```

### 第六步：实现工具系统 (1-2 小时)

```python
from typing import Callable
from functools import wraps

# 装饰器方式注册工具，简单直观
def tool(name: str, description: str):
    """工具装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper.tool_metadata = {
            "name": name,
            "description": description,
            # 自动从函数签名生成 JSON Schema
            "parameters": generate_json_schema(func),
        }
        return wrapper
    return decorator


# 使用示例
@tool("web_search", "搜索互联网获取最新信息")
async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """实际调用搜索API"""
    ...

@tool("execute_python", "在安全沙箱中执行Python代码")
async def execute_python(code: str) -> str:
    """安全执行Python代码并返回结果"""
    ...

@tool("read_file", "读取文件内容")
async def read_file(path: str) -> str:
    """读取指定文件的内容"""
    ...
```

### 第七步：添加定时任务支持 (1-2 小时)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class Scheduler:
    """定时任务管理器，支持 Cron 表达式"""

    def __init__(self, orchestrator: Orchestrator):
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = orchestrator
        self.jobs: dict[str, dict] = {}

    def add_cron_job(
        self,
        name: str,
        cron: str,          # "0 9 * * *" = 每天早上9点
        task: str,          # 任务描述
        agent: str | None = None,  # 指定Agent或自动路由
    ):
        async def execute():
            result = (
                await self.orchestrator.agents[agent].run(task)
                if agent
                else await self.orchestrator.route(task)
            )
            # 结果存入记忆
            await self.orchestrator.memory.add(
                Message(role="system", content=f"定时任务[{name}]结果: {result}")
            )

        self.scheduler.add_job(
            execute,
            trigger=CronTrigger.from_crontab(cron),
            id=name,
        )

    def start(self):
        self.scheduler.start()

# 使用
scheduler.add_cron_job(
    name="morning_briefing",
    cron="0 8 * * *",
    task="整理今天的新闻摘要和工作计划",
)
scheduler.add_cron_job(
    name="code_review_reminder",
    cron="0 17 * * 1-5",
    task="检查今天所有代码变更，生成代码审查摘要",
)
```

***

## 8. 扩展性设计

### 8.1 插件系统

所有核心组件都基于接口/协议，支持热插拔：

```python
# 新 Agent: 实现 Agent 接口即可
class MyCustomAgent(Agent):
    pass

# 新工具: 用 @tool 装饰器
@tool("my_tool", "描述")
async def my_tool(param: str) -> str:
    ...

# 新记忆后端: 实现 MemoryManager
class RedisMemory(MemoryManager):
    pass

# 新 LLM: litellm 已支持 100+ 模型，直接配置
llm = LLMProvider(model="anthropic/claude-sonnet-4-6")
```

### 8.2 配置驱动

```yaml
# config.yaml
agents:
  researcher:
    model: openai/gpt-4o-mini
    tools: [web_search, scrape_url]
    system_prompt: "你是一个研究员..."

  coder:
    model: anthropic/claude-sonnet-4-6
    tools: [execute_python, read_file, write_file]
    system_prompt: "你是一个程序员..."

scheduled_tasks:
  - name: daily_summary
    cron: "0 21 * * *"
    task: "总结今天的工作完成情况"
    agent: researcher
```

### 8.3 未来可扩展方向

```
Phase 1 (现在):  ✅ 单 Agent 核心循环
                  ✅ 基础工具系统
                  ✅ 三层记忆
                  ✅ CLI 交互界面

Phase 2 (1-2周):  → 多 Agent 协作
                  → 定时任务
                  → Web UI (Gradio/Streamlit)
                  → 会话管理

Phase 3 (1个月):  → RAG 知识库
                  → Skill 技能系统（可学习的工具）
                  → 用户身份 + 多用户支持
                  → API Server (FastAPI)

Phase 4 (远期):   → 自主改进（Agent 写自己的工具）
                  → 多模态（图片/语音/视频）
                  → 本地模型支持 (Ollama/llama.cpp)
                  → MCP 协议集成
```

***

## 9. Skill 技能系统 —— Agent 的可复用能力包

### 9.1 什么是 Skill

Skill（技能）是一个**可复用的能力包**，包含：

```
Skill = Prompt模板 + 工具集合 + 执行流程 + 领域知识

和 Tool 的区别:
├── Tool:  单一原子操作 (搜索、读文件、发请求)
└── Skill: 多步骤的复合能力 (代码审查、生成测试、部署应用)
```

**举个例子来理解：**

| <br /> | Tool                | Skill                            |
| ------ | ------------------- | -------------------------------- |
| 粒度     | `web_search` — 搜索网页 | `research_topic` — 深入研究一个主题      |
| 复杂度    | 1 次 LLM 调用          | N 次 LLM 调用 + 多个 Tool             |
| 定义     | 一个函数                | 一份 Markdown/YAML 文档              |
| 例子     | `read_file`         | `code_review` — 读取代码 → 分析 → 生成报告 |

### 9.2 Skill 的定义格式

采用 Markdown + Frontmatter 格式（和 Claude Code 的 Skill 格式兼容）：

```markdown
---
name: code-review
description: 对代码变更进行全面审查，输出安全问题、bug风险、改进建议
version: 1.0.0
author: jojo
tags: [code, review, quality]
requires:
  tools: [read_file, execute_command, grep_search]
  mcp_servers: []  # 可选，依赖的 MCP 服务
triggers:  # 可选，自动触发的关键词
  - "review"
  - "审查代码"
  - "code review"
---

# Code Review Skill

## 目标
对提供的代码变更进行全面审查，关注安全性、正确性、可维护性和性能。

## 执行流程

### Step 1: 理解变更范围
使用 `grep_search` 找到所有被修改的文件。
使用 `read_file` 读取每个变更文件的内容。

### Step 2: 安全检查 (优先级最高)
检查以下安全问题：
- 硬编码的密钥或凭证
- SQL 注入风险（字符串拼接的查询）
- XSS 漏洞（未转义的用户输入）
- 路径遍历风险

如果发现 CRITICAL 问题，立即标记为 BLOCK。

### Step 3: 代码质量检查
- 函数是否过长（>50 行）
- 嵌套是否过深（>4 层）
- 错误处理是否完善
- 命名是否清晰

### Step 4: 生成审查报告
以结构化格式输出审查结果：

| 严重度 | 文件 | 行号 | 问题 | 建议 |
|--------|------|------|------|------|
| CRITICAL | ... | ... | ... | ... |
| HIGH | ... | ... | ... | ... |
| MEDIUM | ... | ... | ... | ... |

## 注意事项
- 不要因为风格偏好（如单引号 vs 双引号）而标记问题
- 如果代码已经有测试且覆盖了变更，说明测试质量
```

### 9.3 Skill 引擎实现

```python
import yaml
import re
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


@dataclass
class Skill:
    """一个可被 Agent 加载和执行的技能"""

    name: str
    description: str
    version: str
    author: str
    tags: list[str]
    requires: dict[str, list[str]]
    triggers: list[str]
    raw_content: str  # 完整的 Markdown 内容（作为 Prompt 注入）

    def to_system_prompt(self) -> str:
        """将 Skill 转换为 Agent 可用的 System Prompt 片段"""
        return f"""
<skill name="{self.name}" description="{self.description}">
{self.raw_content}
</skill>
"""


class SkillRegistry:
    """Skill 注册中心 — 加载、发现、匹配 Skill"""

    def __init__(self, skills_dir: str = "skills/"):
        self.skills_dir = Path(skills_dir)
        self.skills: dict[str, Skill] = {}
        self._load_all()

    def _load_all(self) -> None:
        """从 skills/ 目录加载所有 Skill"""
        for skill_file in self.skills_dir.glob("**/*.md"):
            skill = self._parse_skill_file(skill_file)
            if skill:
                self.skills[skill.name] = skill

    def _parse_skill_file(self, filepath: Path) -> Skill | None:
        """解析 Skill Markdown 文件"""
        content = filepath.read_text(encoding="utf-8")

        # 解析 YAML frontmatter
        match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if not match:
            return None

        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2).strip()

        return Skill(
            name=frontmatter["name"],
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", "unknown"),
            tags=frontmatter.get("tags", []),
            requires=frontmatter.get("requires", {"tools": [], "mcp_servers": []}),
            triggers=frontmatter.get("triggers", []),
            raw_content=body,
        )

    def match(self, user_input: str) -> list[Skill]:
        """
        根据用户输入匹配最相关的 Skill。
        匹配策略：
        1. 关键词触发匹配 (triggers)
        2. 语义相似度匹配 (Embedding)
        3. 标签匹配
        """
        matched = []
        input_lower = user_input.lower()

        for skill in self.skills.values():
            score = 0
            # 关键词触发
            for trigger in skill.triggers:
                if trigger.lower() in input_lower:
                    score += 10  # 精确触发，高分
            # 标签匹配
            for tag in skill.tags:
                if tag.lower() in input_lower:
                    score += 3
            # 名称/描述匹配
            if skill.name.lower() in input_lower:
                score += 5
            if any(word in input_lower for word in skill.description.lower().split()):
                score += 1

            if score > 0:
                matched.append((score, skill))

        # 按分数降序
        matched.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in matched]

    def get_required_tools(self, skill_names: list[str]) -> list[str]:
        """获取执行一组 Skill 所需的所有工具"""
        tools = set()
        for name in skill_names:
            if skill := self.skills.get(name):
                tools.update(skill.requires.get("tools", []))
        return list(tools)

    def get_required_mcp_servers(self, skill_names: list[str]) -> list[str]:
        """获取执行一组 Skill 所需的 MCP 服务器"""
        servers = set()
        for name in skill_names:
            if skill := self.skills.get(name):
                servers.update(skill.requires.get("mcp_servers", []))
        return list(servers)
```

### 9.4 Skill 在 Agent 中的集成方式

```python
class SkillAwareAgent(SimpleAgent):
    """
    增强版 Agent — 能自动发现和调用 Skill
    """

    def __init__(self, *args, skill_registry: SkillRegistry, **kwargs):
        super().__init__(*args, **kwargs)
        self.skill_registry = skill_registry
        self.active_skills: list[Skill] = []

    async def run(self, user_input: str) -> str:
        # 1. 匹配相关 Skill
        matched_skills = self.skill_registry.match(user_input)
        self.active_skills = matched_skills[:3]  # 最多激活 3 个

        # 2. 将 Skill 的 Prompt 注入到系统提示中
        skill_prompts = "\n".join(
            s.to_system_prompt() for s in self.active_skills
        )

        # 3. 确保 Skill 依赖的工具已加载
        required_tools = self.skill_registry.get_required_tools(
            [s.name for s in self.active_skills]
        )
        self._ensure_tools_loaded(required_tools)

        # 4. 增强 System Prompt
        enhanced_system_prompt = f"""
{self.system_prompt}

## 可用的技能 (Skills)

以下是你可以使用的专业技能。当用户请求匹配技能描述时，按照技能中定义的流程执行。

{skill_prompts}

## 使用技能的规则
- 技能定义了完整的执行流程，请严格遵循
- 如果用户请求匹配多个技能，按优先级依次执行
- 技能执行完成后，总结关键发现和操作结果
"""

        # 5. 执行标准 Agent 循环（但现在 Skill Prompt 已注入）
        # ... 调用原有的 run 逻辑
        return await super().run(user_input)
```

### 9.5 Skill 的高级特性

```python
class SkillComposer:
    """
    Skill 组合器 — 将多个 Skill 编排成工作流

    场景: 用户说 "审查代码并部署到测试环境"
    → 自动编排: code_review → run_tests → deploy_test
    """

    async def compose(
        self,
        skills: list[Skill],
        context: dict,
    ) -> list[dict]:
        """按依赖关系将多个 Skill 串联执行"""
        results = []
        shared_context = context  # Skill 之间共享上下文

        for skill in skills:
            result = await self._execute_skill(skill, shared_context)
            results.append(result)
            # 将上一个 Skill 的输出注入下一个的上下文
            shared_context[f"_{skill.name}_output"] = result

        return results


class SkillLearner:
    """
    Skill 学习器 — Agent 可以从成功执行中自动提炼新 Skill

    这是自建框架最大的优势：Agent 能自我进化
    """

    async def extract_skill(
        self,
        conversation: list[Message],
        outcome: str,  # "成功" / "失败"
    ) -> Skill | None:
        """从一次成功的任务执行中提炼 Skill"""
        if outcome != "成功":
            return None

        prompt = f"""
从以下对话历史中提取一个可复用的 Skill。

要求:
1. 为 Skill 命名并写描述
2. 总结执行流程 (Step 1, Step 2, ...)
3. 列出使用的工具
4. 标记适用的触发关键词

对话历史:
{self._format_conversation(conversation)}

输出格式: Markdown with YAML frontmatter
"""
        skill_md = await self.llm.chat([{"role": "user", "content": prompt}])
        return self._parse_and_save(skill_md)
```

### 9.6 Skill 文件目录结构示例

```
skills/
├── code/
│   ├── code-review.md          # 代码审查
│   ├── generate-tests.md       # 生成测试用例
│   └── refactor-suggest.md     # 重构建议
├── data/
│   ├── analyze-csv.md          # 分析 CSV 数据
│   └── generate-report.md      # 生成数据报告
├── productivity/
│   ├── daily-standup.md        # 每日站会总结
│   ├── meeting-notes.md        # 会议纪要
│   └── project-status.md       # 项目状态检查
└── research/
    ├── deep-research.md        # 深度调研
    └── competitor-analysis.md  # 竞品分析
```

### 9.7 Skill vs Tool vs Agent — 三者的分工

```
TOOL (原子操作)
├── 做什么: 执行单一明确的动作
├── 例子: search_web, read_file, send_email
├── 谁定义: 开发者用代码定义
└── 何时用: Agent 在思考过程中按需调用

SKILL (能力包)
├── 做什么: 完成一个复合任务
├── 例子: code_review, deep_research, deploy_app
├── 谁定义: 开发者用 Markdown 定义（Agent 也可以自动提炼）
└── 何时用: 用户请求触发，Agent 按 Skill 定义的流程执行

AGENT (智能体)
├── 做什么: 自主决策、规划、执行
├── 例子: Researcher, Coder, Reviewer
├── 谁定义: 用 System Prompt + Tool + Skill 装配
└── 何时用: 作为独立的工作单元，可以调用多个 Skill 和 Tool
```

***

## 10. MCP 协议集成 —— 连接外部工具的标准协议

### 10.1 什么是 MCP

**MCP (Model Context Protocol)** 是 Anthropic 发布的开放标准，定义了 AI 应用如何安全、标准化地连接外部工具和数据源。

```
MCP 解决的问题:

没有 MCP 之前:
┌──────────┐     自定义代码     ┌──────────┐
│  Agent   │ ───  (每个集成     │  Tool A  │
│          │      都不相同)     └──────────┘
│          │ ─── 另一套代码  ── ┌──────────┐
│          │                    │  Tool B  │
└──────────┘                    └──────────┘
N 个工具 = N 套集成代码，维护噩梦

有了 MCP 之后:
┌──────────┐   标准 MCP 协议   ┌──────────────┐
│  Agent   │ ←──────────────→ │ MCP Server A  │ (管理 Tool A, B, C)
│ (MCP     │   标准 MCP 协议   ├──────────────┤
│  Client) │ ←──────────────→ │ MCP Server B  │ (管理 Tool D, E)
└──────────┘                   └──────────────┘
一个标准协议，所有工具统一接入
```

### 10.2 MCP 架构详解

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP 架构                                 │
│                                                              │
│   Host (宿主应用)                                             │
│   ┌───────────────────────────────────────────────────┐    │
│   │  Claude Code / 你的 Agent / VS Code               │    │
│   │                                                    │    │
│   │  ┌──────────────────────────────────────────┐    │    │
│   │  │        MCP Client (客户端)                │    │    │
│   │  │  - 管理多个 MCP Server 连接                │    │    │
│   │  │  - 发现 Tools / Resources / Prompts       │    │    │
│   │  │  - 路由 LLM 的调用请求到正确的 Server      │    │    │
│   │  └──────────────────────────────────────────┘    │    │
│   └───────────────────┬──────────────────────────────┘    │
│                       │                                     │
│          ┌────────────┼────────────┐                       │
│          ↓            ↓            ↓                       │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│   │MCP Server│ │MCP Server│ │MCP Server│   (远端/本地)    │
│   │ 文件系统  │ │ 数据库   │ │   API    │                  │
│   │          │ │          │ │          │                  │
│   │Tools:    │ │Tools:    │ │Tools:    │                  │
│   │- read    │ │- query   │ │- fetch   │                  │
│   │- write   │ │- insert  │ │- search  │                  │
│   │- list    │ │- migrate │ │- webhook │                  │
│   └──────────┘ └──────────┘ └──────────┘                  │
│                                                              │
│   传输层:                                                     │
│   - stdio (标准输入输出) — 本地进程通信                       │
│   - HTTP + SSE (Server-Sent Events) — 远程服务通信            │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 MCP 的三个核心概念

```
┌─────────────────────────────────────────────────────┐
│                  MCP Server 暴露的能力               │
│                                                      │
│  1. TOOLS (工具)                                     │
│     LLM 可以调用的函数                               │
│     类似: Function Calling                           │
│     例子: search_database, send_email, create_issue │
│                                                      │
│  2. RESOURCES (资源)                                 │
│     暴露给 LLM 的只读数据                            │
│     类似: 文件系统中的文件                            │
│     例子: 文档内容、数据库 Schema、API 文档           │
│                                                      │
│  3. PROMPTS (提示模板)                               │
│     预定义的 Prompt 模板                             │
│     类似: Skill (但由服务端定义)                      │
│     例子: "生成单元测试" 模板、"代码审查" 模板       │
└─────────────────────────────────────────────────────┘
```

### 10.4 在 Agent 框架中实现 MCP Client

```python
import asyncio
import json
from subprocess import Popen, PIPE
from typing import Any
from dataclasses import dataclass
import httpx


@dataclass
class MCPServerConfig:
    """MCP Server 的配置定义"""
    name: str
    transport: str  # "stdio" | "http"
    # stdio 模式
    command: str | None = None
    args: list[str] = None
    # http 模式
    url: str | None = None
    headers: dict[str, str] = None


class MCPClient:
    """
    MCP 客户端 — Agent 通过它和 MCP Server 通信

    支持两种传输方式:
    - stdio: 启动一个子进程，通过 stdin/stdout 通信 (JSON-RPC)
    - http: 通过 HTTP + SSE 与远程 Server 通信
    """

    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}
        self._connections: dict[str, Any] = {}  # 活跃连接
        self._tools_cache: dict[str, list[dict]] = {}  # 工具缓存

    # ========== 服务器管理 ==========

    def register_server(self, config: MCPServerConfig) -> None:
        """注册一个 MCP Server"""
        self.servers[config.name] = config

    def load_from_config(self, config_path: str) -> None:
        """从配置文件批量加载 MCP Server"""
        import yaml
        with open(config_path) as f:
            configs = yaml.safe_load(f)

        for name, cfg in configs.get("mcp_servers", {}).items():
            self.register_server(MCPServerConfig(
                name=name,
                transport=cfg.get("transport", "stdio"),
                command=cfg.get("command"),
                args=cfg.get("args", []),
                url=cfg.get("url"),
                headers=cfg.get("headers"),
            ))

    # ========== 连接管理 ==========

    async def connect(self, server_name: str) -> None:
        """连接到指定的 MCP Server"""
        config = self.servers[server_name]

        if config.transport == "stdio":
            await self._connect_stdio(server_name, config)
        elif config.transport == "http":
            await self._connect_http(server_name, config)

    async def _connect_stdio(self, name: str, config: MCPServerConfig) -> None:
        """通过 stdio 连接本地 MCP Server"""
        # 启动子进程
        process = await asyncio.create_subprocess_exec(
            config.command, *config.args,
            stdin=PIPE, stdout=PIPE, stderr=PIPE,
        )

        # 发送 initialize 请求 (JSON-RPC)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "jojo-agent",
                    "version": "1.0.0",
                },
            },
        }
        response = await self._send_stdio_request(process, init_request)
        self._connections[name] = process

    async def _connect_http(self, name: str, config: MCPServerConfig) -> None:
        """通过 HTTP 连接远程 MCP Server"""
        client = httpx.AsyncClient(
            base_url=config.url,
            headers=config.headers or {},
            timeout=30.0,
        )
        # 发送 initialize 请求
        response = await client.post("/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "jojo-agent", "version": "1.0.0"},
            },
        })
        self._connections[name] = client

    async def _send_stdio_request(
        self, process: asyncio.subprocess.Process, request: dict
    ) -> dict:
        """通过 stdio 发送 JSON-RPC 请求"""
        request_str = json.dumps(request) + "\n"
        process.stdin.write(request_str.encode())
        await process.stdin.drain()

        response_line = await process.stdout.readline()
        return json.loads(response_line.decode())

    async def _send_http_request(
        self, client: httpx.AsyncClient, request: dict
    ) -> dict:
        """通过 HTTP 发送 JSON-RPC 请求"""
        response = await client.post("/mcp", json=request)
        return response.json()

    # ========== 工具发现 ==========

    async def list_tools(self, server_name: str) -> list[dict]:
        """列出某个 MCP Server 提供的所有工具"""
        if server_name in self._tools_cache:
            return self._tools_cache[server_name]

        conn = self._connections.get(server_name)
        if not conn:
            await self.connect(server_name)
            conn = self._connections[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        if isinstance(conn, httpx.AsyncClient):
            response = await self._send_http_request(conn, request)
        else:
            response = await self._send_stdio_request(conn, request)

        tools = response.get("result", {}).get("tools", [])
        self._tools_cache[server_name] = tools
        return tools

    async def list_all_tools(self) -> dict[str, list[dict]]:
        """列出所有已连接 MCP Server 的工具"""
        all_tools = {}
        for name in self.servers:
            try:
                all_tools[name] = await self.list_tools(name)
            except Exception as e:
                all_tools[name] = [{"error": str(e)}]
        return all_tools

    # ========== 工具调用 ==========

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
    ) -> Any:
        """调用指定 MCP Server 的工具"""
        conn = self._connections.get(server_name)
        if not conn:
            await self.connect(server_name)
            conn = self._connections[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        if isinstance(conn, httpx.AsyncClient):
            response = await self._send_http_request(conn, request)
        else:
            response = await self._send_stdio_request(conn, request)

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        return response.get("result", {}).get("content", [])

    # ========== 资源访问 ==========

    async def list_resources(self, server_name: str) -> list[dict]:
        """列出 MCP Server 暴露的资源"""
        conn = self._connections.get(server_name)
        if not conn:
            await self.connect(server_name)
            conn = self._connections[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {},
        }

        if isinstance(conn, httpx.AsyncClient):
            response = await self._send_http_request(conn, request)
        else:
            response = await self._send_stdio_request(conn, request)

        return response.get("result", {}).get("resources", [])

    async def read_resource(
        self, server_name: str, resource_uri: str
    ) -> str:
        """读取指定资源的内容"""
        conn = self._connections.get(server_name)
        if not conn:
            await self.connect(server_name)
            conn = self._connections[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": resource_uri},
        }

        if isinstance(conn, httpx.AsyncClient):
            response = await self._send_http_request(conn, request)
        else:
            response = await self._send_stdio_request(conn, request)

        return response.get("result", {}).get("contents", [])

    # ========== 清理 ==========

    async def disconnect_all(self) -> None:
        """断开所有 MCP Server 连接"""
        for name, conn in self._connections.items():
            if isinstance(conn, httpx.AsyncClient):
                await conn.aclose()
            else:
                conn.terminate()
        self._connections.clear()
        self._tools_cache.clear()
```

### 10.5 MCP 在 Agent 中的集成

```python
class MCPEnabledAgent(SimpleAgent):
    """
    支持 MCP 的 Agent — 自动发现和调用 MCP Server 的工具
    """

    def __init__(self, *args, mcp_client: MCPClient, **kwargs):
        super().__init__(*args, **kwargs)
        self.mcp = mcp_client

    async def _load_mcp_tools(self) -> list[dict]:
        """从所有 MCP Server 加载工具定义，转换为 Agent 可用的格式"""
        all_tools = await self.mcp.list_all_tools()
        converted = []

        for server_name, tools in all_tools.items():
            for tool in tools:
                converted.append({
                    "type": "function",
                    "function": {
                        "name": f"mcp__{server_name}__{tool['name']}",
                        "description": f"[MCP:{server_name}] {tool.get('description', '')}",
                        "parameters": tool.get("inputSchema", {}),
                    },
                })

        return converted

    async def _execute_mcp_tool(
        self, server_name: str, tool_name: str, arguments: dict
    ) -> str:
        """执行 MCP 工具并返回格式化结果"""
        result = await self.mcp.call_tool(server_name, tool_name, arguments)

        # MCP 返回的 content 可能是多种类型的数组
        # 需要格式化成 LLM 能理解的文本
        formatted = []
        for item in result if isinstance(result, list) else [result]:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    formatted.append(item["text"])
                elif item.get("type") == "image":
                    formatted.append(f"[Image: {item.get('data', '')[:50]}...]")
                elif item.get("type") == "resource":
                    formatted.append(f"[Resource: {item.get('uri', '')}]")
            else:
                formatted.append(str(item))

        return "\n".join(formatted)
```

### 10.6 MCP Server 配置示例

```yaml
# mcp_servers.yaml — MCP Server 配置文件

mcp_servers:
  # 本地文件系统 Server
  filesystem:
    transport: stdio
    command: npx
    args:
      - "@anthropic/mcp-server-filesystem"
      - "/path/to/allowed/directory"

  # 数据库 Server
  postgres:
    transport: stdio
    command: npx
    args:
      - "@anthropic/mcp-server-postgres"
    env:
      DATABASE_URL: "postgresql://localhost/mydb"

  # 搜索引擎 Server
  brave-search:
    transport: stdio
    command: npx
    args:
      - "@anthropic/mcp-server-brave-search"
    env:
      BRAVE_API_KEY: "${BRAVE_API_KEY}"

  # GitHub Server
  github:
    transport: stdio
    command: npx
    args:
      - "@anthropic/mcp-server-github"
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"

  # 远程自定义 Server (HTTP 模式)
  custom-api:
    transport: http
    url: https://my-mcp-server.example.com/mcp
    headers:
      Authorization: "Bearer ${API_TOKEN}"
```

### 10.7 Skill + MCP 联动 —— 终极能力组合

这是自建框架最强大的设计 — Skill 可以直接声明依赖的 MCP Server：

```yaml
# skills/research/competitor-analysis.md
---
name: competitor-analysis
description: 分析竞争对手的产品、市场策略和技术栈
requires:
  tools: []
  mcp_servers:
    - brave-search   # 搜索竞品信息
    - github          # 分析竞品的开源项目
---

# 竞品分析 Skill

## 执行流程

### Step 1: 搜索竞品信息
使用 MCP brave-search 工具搜索目标竞品的最新动态。

### Step 2: 分析技术栈
使用 MCP github 工具分析竞品的开源仓库。

### Step 3: 生成报告
整合信息，生成竞品分析报告。
```

```python
class SkillMCPOrchestrator:
    """
    Skill + MCP 编排器

    当一个 Skill 被激活时:
    1. 检查 Skill 依赖的 MCP Server
    2. 自动连接所需的 MCP Server
    3. 将 MCP 工具注入到 Agent 的工具列表中
    4. 执行 Skill 定义的流程
    5. Skill 完成后，可选择断开非必需的 MCP 连接
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        mcp_client: MCPClient,
        agent_factory: callable,  # 创建 Agent 的工厂函数
    ):
        self.skills = skill_registry
        self.mcp = mcp_client
        self.agent_factory = agent_factory

    async def execute_with_skill(
        self, user_input: str
    ) -> str:
        # 1. 匹配 Skill
        matched = self.skills.match(user_input)

        if not matched:
            # 没有匹配的 Skill，用默认 Agent 处理
            agent = self.agent_factory()
            return await agent.run(user_input)

        skill = matched[0]

        # 2. 检查 MCP 依赖
        required_mcps = self.skills.get_required_mcp_servers([skill.name])

        # 3. 连接所需的 MCP Server
        for server_name in required_mcps:
            if server_name not in self.mcp._connections:
                await self.mcp.connect(server_name)

        # 4. 创建带有 Skill + MCP 能力的 Agent
        agent = self.agent_factory(
            skills=[skill],
            mcp_servers=required_mcps,
        )

        # 5. 执行
        result = await agent.run(user_input)

        return result
```

### 10.8 MCP 生态 —— 现成的 MCP Server

你不需要自己写所有的 MCP Server，社区已经有大量可用的：

```
官方/社区 MCP Server 市场:

数据 & 内容:
├── @anthropic/mcp-server-filesystem    — 文件系统操作
├── @anthropic/mcp-server-postgres      — PostgreSQL
├── @anthropic/mcp-server-sqlite        — SQLite
└── mcp-server-brave-search             — Brave 搜索

开发工具:
├── @anthropic/mcp-server-github        — GitHub API
├── @anthropic/mcp-server-git           — Git 操作
└── mcp-server-docker                   — Docker 管理

生产力:
├── mcp-server-slack                    — Slack 消息
├── mcp-server-notion                   — Notion 文档
├── mcp-server-google-calendar          — Google 日历
└── mcp-server-gmail                    — Gmail

AI & 数据:
├── mcp-server-sequential-thinking      — 链式思考
├── mcp-server-memory                   — 持久化记忆
└── mcp-server-puppeteer                — 浏览器自动化
```

***

## 11. 总结

### 11.1 终极公式

```
Agent = LLM + 工具(Tool) + 技能(Skill) + MCP协议 + 记忆 + 规划

1. LLM 是大脑    — 负责理解、推理、生成
2. Tool 是原子操作 — 搜索、读文件、执行代码（单一动作）
3. Skill 是能力包 — 代码审查、深度调研、部署（复合流程）
4. MCP 是标准协议 — 连接外部工具和数据源的标准接口
5. 记忆是经验    — 工作记忆 + 短期记忆 + 长期记忆
6. 规划是思维    — 拆解任务、分配Agent、控制流程

多Agent协作  = 把多个专业Agent组合起来，各司其职
Skill 系统   = 可复用的能力包，Markdown定义，Agent可自我提炼
MCP 集成     = 标准化连接外部世界，一次编写到处使用
```

### 11.2 推荐搭建路径（更新版）

```
第1天: 理解概念 → 搭建单 Agent 核心循环 → 能对话、能调 Tool
第2天: 实现记忆系统 → Agent 能记住之前说过的话
第3天: 实现 Tool 系统 + MCP Client → Agent 能连接外部世界
第4天: 实现 Skill 系统 → Agent 拥有可复用能力包
第5天: 实现多 Agent 协作 → 多个 Agent 配合完成任务
第6天: 添加定时任务 → Agent 能主动执行
第7天: 测试、优化、封装 → 一个可用的个人助手成型
```

### 11.3 自建 vs 框架 —— 最终判断

| 考量            | 自建                 | 用框架    |
| ------------- | ------------------ | ------ |
| **Skill 灵活度** | 完全自定义格式            | 受框架限制  |
| **MCP 深度集成**  | 一等公民               | 依赖框架支持 |
| **自我进化**      | Skill Learner 自动提炼 | 基本做不到  |
| **理解深度**      | 每个细节都懂             | 只懂 API |
| **性能**        | 零额外开销              | 框架负担   |
| **前期投入**      | 约 7 天              | 约 1 天  |

### 11.4 一句话建议

**先用最简单的代码把 Agent 跑通（1天），再逐步加记忆→MCP→Skill→多Agent。不要一开始就引入复杂框架——理解原理比使用工具更重要。当你自己写过一个 Agent，再用任何框架都是降维打击。**

***

> 文档版本: v2.0
> 创建日期: 2026-05-13
> 最后更新: 2026-05-13
> 适用语言: Python 3.12+

