"""
CLI 入口 — 命令行交互界面。
"""

import argparse
import asyncio
import sys

from src.jojo.agent.approval import ApprovalRequest
from src.jojo.config import config, load_config
from src.jojo.logger import setup_logger, logger


# ========== 基础命令 ==========

def cmd_version() -> None:
    print(f"JoJo Agent v{config.version}")


def cmd_config() -> None:
    print(f"Project:      {config.project_name} v{config.version}")
    print(f"Log Level:    {config.log_level}")
    print(f"Model:        {config.llm.default_model}")
    print(f"Flash Model:  {config.orchestrator.flash_model}")
    print(f"Pro Model:    {config.orchestrator.pro_model}")
    print(f"Max Iter:     {config.agent.max_iterations}")
    print(f"Workspace:    {config.agent.workspace_root}")
    print(f"API Keys:     ", end="")
    keys = []
    if config.openai_api_key:
        keys.append(f"OpenAI")
    if config.anthropic_api_key:
        keys.append(f"Anthropic")
    if config.deepseek_api_key:
        keys.append(f"DeepSeek")
    print(", ".join(keys) if keys else "(none)")


# ========== 对话模式 (含自动路由) ==========

def cmd_chat() -> None:
    asyncio.run(_chat_loop())


async def _chat_loop() -> None:
    from src.jojo.orchestrator import Orchestrator, registry
    from src.jojo.agents import create_researcher, create_coder

    orch = Orchestrator(registry)
    orch.register(create_researcher())
    orch.register(create_coder())

    # 默认 Agent（单 Agent 模式也保留）
    from src.jojo.agent import Agent
    single = Agent(
        name="JoJo",
        description="a helpful personal AI assistant",
        max_iterations=config.agent.max_iterations,
        verbose=config.agent.verbose,
        approval_callback=_cli_approval_callback,
    )

    # 自动加载 & 连接 MCP Servers
    from src.jojo.mcp import MCPClient, MCPAdapter, load_mcp_config
    mcp_client = MCPClient()
    mcp_adapter = MCPAdapter(mcp_client)
    mcp_configs = load_mcp_config()
    mcp_tool_count = 0
    for cfg in mcp_configs:
        try:
            mcp_client.register(cfg)
            await mcp_client.connect(cfg.name)
            tools = await mcp_adapter.discover_and_register(cfg.name)
            mcp_tool_count += len(tools)
        except Exception as e:
            logger.warning(f"Failed to connect MCP '{cfg.name}': {e}")

    # 启动定时任务引擎 + 注册工具
    from src.jojo.scheduler import engine as sched_engine
    from src.jojo.scheduler.tools import add_cron_job, remove_cron_job, list_cron_jobs
    from src.jojo.tools.registry import registry as tool_registry
    tool_registry.register_from_decorated(add_cron_job)
    tool_registry.register_from_decorated(remove_cron_job)
    tool_registry.register_from_decorated(list_cron_jobs)
    sched_engine.start()
    sched_jobs = sched_engine.list_jobs()

    print()
    print("=" * 55)
    print("  JoJo Agent — Multi-Agent Chat Mode")
    print(f"  Flash: {config.orchestrator.flash_model}")
    print(f"  Pro:   {config.orchestrator.pro_model}")
    print(f"  Agents: {', '.join(a['name'] for a in registry.list_all())}")
    if mcp_tool_count:
        print(f"  MCP:    {mcp_tool_count} tools from {len([c for c in mcp_configs if c.name in mcp_client.connected_servers])} servers")
    if sched_jobs:
        print(f"  Jobs:   {len(sched_jobs)} scheduled")
    print("  /exit  /verbose  /allowall  /help  /agents")
    print("=" * 55)
    print()

    while True:
        # 检查定时任务通知
        notifications = sched_engine.pop_notifications()
        for note in notifications:
            print(f"\n  {note}\n")

        try:
            # 在线程中运行 input()，不阻塞事件循环（否则调度器冻结）
            loop = asyncio.get_event_loop()
            user_input = (await loop.run_in_executor(
                None, lambda: input("JoJo> ").strip()
            ))
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # 内置命令
        if user_input == "/exit":
            print("Goodbye!")
            break
        if user_input == "/verbose":
            single.verbose = not single.verbose
            print(f"Verbose: {'ON' if single.verbose else 'OFF'}")
            continue
        if user_input == "/allowall":
            single.approval.allow_all()
            print("Write operations auto-approved.")
            continue
        if user_input == "/agents":
            for a in registry.list_all():
                print(f"  - {a['name']}: {a['description'][:80]}...")
            continue
        if user_input == "/help":
            print("  /exit      Quit")
            print("  /verbose   Toggle thought visibility")
            print("  /allowall  Auto-approve write operations")
            print("  /agents    List available agents")
            print("  /help      Show this help")
            continue

        try:
            # 自动路由：分类 → 选模型 → 选 Agent → 执行
            complexity = await orch.classifier.classify(user_input)
            model = orch.classifier.get_model_for(complexity)
            agents = registry.list_all()
            agent_name = await orch.router.route(user_input, agents)

            # 匹配 Skill
            from src.jojo.skills import registry as skill_registry
            matched_skills = skill_registry.match(user_input)

            # Skill → Agent 强制路由 (信息收集类 Skill 走 researcher)
            info_skills = {"daily-summary"}
            if matched_skills:
                skill_names = {s.name for s in matched_skills}
                if skill_names & info_skills:
                    agent_name = "researcher"

            # 路由信息
            parts = [complexity]
            if complexity != "simple":
                parts.append(str(model))
            parts.append(agent_name)
            if matched_skills:
                parts.append(f"skills: {','.join(s.name for s in matched_skills)}")
            print(f"  [{' | '.join(parts)}]")

            if complexity == "simple":
                reply = await single.run(user_input)
            else:
                reply = await orch.auto(user_input, agent_name=agent_name)
            print(f"\nAgent> {reply}\n")
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nAgent> Sorry, an error occurred: {e}\n")


# ========== 多 Agent 编排 ==========

def cmd_orchestrate(args: argparse.Namespace) -> None:
    asyncio.run(_orchestrate(args))


async def _orchestrate(args: argparse.Namespace) -> None:
    from src.jojo.orchestrator import Orchestrator, registry
    from src.jojo.agents import create_researcher, create_coder

    orch = Orchestrator(registry)
    orch.register(create_researcher())
    orch.register(create_coder())

    print(f"Task: {args.task}")
    print(f"Mode: {args.mode}")
    print()

    if args.mode == "auto":
        result = await orch.auto(args.task)
    elif args.mode == "sequential":
        agents = args.agents.split(",") if args.agents else ["researcher", "coder"]
        print(f"Pipeline: {' → '.join(agents)}")
        result = await orch.sequential(args.task, agents)
    elif args.mode == "parallel":
        subtasks = [s.strip() for s in args.task.split(";") if s.strip()]
        if len(subtasks) < 2:
            subtasks = [args.task, args.task]  # fallback
        agent = args.agents or "researcher"
        result = await orch.parallel(args.task, agent, subtasks)
    else:
        result = f"Unknown mode: {args.mode}"

    print(f"\n{'=' * 50}")
    print(result)
    print(f"{'=' * 50}")


# ========== Agent 管理 ==========

def cmd_agent_list() -> None:
    from src.jojo.orchestrator import registry
    from src.jojo.agents import create_researcher, create_coder

    if len(registry) == 0:
        registry.register(create_researcher())
        registry.register(create_coder())

    print("Available Agents:")
    for a in registry.list_all():
        print(f"  {a['name']:15s} — {a['description'][:70]}...")


def cmd_skill_list() -> None:
    from src.jojo.skills import registry as skill_registry

    skills = skill_registry.list_all()
    if not skills:
        print("No skills loaded.")
        return

    print(f"Loaded {len(skills)} skills:\n")
    for s in skills:
        print(f"  {s.name}")
        print(f"    Description: {s.description}")
        print(f"    Triggers:    {', '.join(s.triggers)}")
        print(f"    Tools:       {', '.join(s.tools_required) or '(none)'}")
        print()


def cmd_mcp_list() -> None:
    from src.jojo.mcp import load_mcp_config

    configs = load_mcp_config()
    if not configs:
        print("No MCP servers configured.")
        print(f"Add entries to {config.mcp_config_path}")
        return

    print(f"MCP Servers ({len(configs)}):\n")
    for c in configs:
        print(f"  {c.name}")
        print(f"    Transport: {c.transport}")
        if c.transport == "stdio":
            print(f"    Command:   {c.command} {' '.join(c.args)}")
        else:
            print(f"    URL:       {c.url}")
        print()


async def _mcp_connect_cmd(name: str) -> None:
    from src.jojo.mcp import MCPClient, MCPAdapter, load_mcp_config

    configs = load_mcp_config()
    cfg = next((c for c in configs if c.name == name), None)
    if not cfg:
        print(f"MCP server '{name}' not found in config.")
        return

    client = MCPClient()
    client.register(cfg)
    await client.connect(name)

    adapter = MCPAdapter(client)
    tools = await adapter.discover_and_register(name)

    print(f"Connected to '{name}', {len(tools)} tools registered:")
    for t in tools:
        print(f"  - {t}")

    await client.disconnect_all()


def cmd_mcp_connect(args: argparse.Namespace) -> None:
    asyncio.run(_mcp_connect_cmd(args.name))


# ========== 定时任务管理 ==========

def _job_wrapper(fn):
    """Wrap sync CLI calls in asyncio for APScheduler."""
    def wrapper(*args, **kwargs):
        asyncio.run(fn(*args, **kwargs))
    return wrapper


@_job_wrapper
async def cmd_job_add(args: argparse.Namespace) -> None:
    from src.jojo.scheduler import engine
    engine.start()
    job = engine.add_job(
        name=args.name, cron=args.cron,
        task=args.task, agent=args.agent or "researcher",
    )
    print(f"Job added: {job.name} ({job.cron}) ID={job.id}")


@_job_wrapper
async def cmd_job_list() -> None:
    from src.jojo.scheduler import engine
    engine.start()
    jobs = engine.list_jobs()
    if not jobs:
        print("No scheduled jobs.")
        return
    for j in jobs:
        status = "enabled" if j.enabled else "disabled"
        last = f"last: {j.last_run_at}" if j.last_run_at else "never"
        print(f"  [{j.name}] {j.cron} → {j.agent}: {j.task} ({status}, {last})")


@_job_wrapper
async def cmd_job_remove(args: argparse.Namespace) -> None:
    from src.jojo.scheduler import engine
    engine.start()
    if engine.remove_by_name(args.name):
        print(f"Job '{args.name}' removed.")
    else:
        print(f"Job '{args.name}' not found.")


# ========== 审批回调 ==========

async def _cli_approval_callback(req: ApprovalRequest) -> str:
    from src.jojo.agent.approval import ApprovalHandler
    handler = ApprovalHandler()
    print(handler.build_prompt(req), end=" ")
    try:
        return input().strip() or "y"
    except (EOFError, KeyboardInterrupt):
        return "n"


# ========== 参数解析 ==========

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jojo",
        description="JoJo Personal AI Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jojo                              Show config info
  jojo version                      Print version
  jojo config                       Print current configuration
  jojo chat                         Start interactive multi-agent chat
  jojo orchestrate --task "..."     Auto-route task to best agent
  jojo agent list                   List all available agents
        """,
    )
    parser.add_argument("-c", "--config", default="config.yaml",
                        help="Path to config file")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("version", help="Print version number")
    sub.add_parser("config", help="Print current configuration")
    sub.add_parser("chat", help="Start interactive multi-agent chat mode")

    # orchestrate
    orch = sub.add_parser("orchestrate", help="Run a task with multi-agent orchestration")
    orch.add_argument("--task", required=True, help="Task description")
    orch.add_argument("--mode", default="auto",
                      choices=["auto", "sequential", "parallel"],
                      help="Orchestration mode (default: auto)")
    orch.add_argument("--agents", help="Agent names, comma-separated")

    # agent
    ag = sub.add_parser("agent", help="Agent management")
    ag_sub = ag.add_subparsers(dest="agent_cmd")
    ag_sub.add_parser("list", help="List all agents")

    # skill
    sk = sub.add_parser("skill", help="Skill management")
    sk_sub = sk.add_subparsers(dest="skill_cmd")
    sk_sub.add_parser("list", help="List all loaded skills")

    # mcp
    mcp = sub.add_parser("mcp", help="MCP server management")
    mcp_sub = mcp.add_subparsers(dest="mcp_cmd")
    mcp_sub.add_parser("list", help="List configured MCP servers")
    mcp_conn = mcp_sub.add_parser("connect", help="Connect to an MCP server")
    mcp_conn.add_argument("name", help="MCP server name")

    # job
    job = sub.add_parser("job", help="Scheduled job management")
    job_sub = job.add_subparsers(dest="job_cmd")
    job_sub.add_parser("list", help="List all scheduled jobs")
    job_add = job_sub.add_parser("add", help="Add a scheduled job")
    job_add.add_argument("--name", required=True, help="Job name")
    job_add.add_argument("--cron", required=True, help="Cron expression (e.g. '0 9 * * *')")
    job_add.add_argument("--task", required=True, help="Task description")
    job_add.add_argument("--agent", help="Agent name (default: researcher)")
    job_rm = job_sub.add_parser("remove", help="Remove a job by name")
    job_rm.add_argument("name", help="Job name")

    return parser


def main(args: list[str] | None = None) -> None:
    if args is None:
        args = sys.argv[1:]

    parsed = build_parser().parse_args(args)

    global config
    config = load_config(parsed.config)
    setup_logger()

    logger.info(f"JoJo Agent v{config.version} initializing...")

    if parsed.command == "version":
        cmd_version()
    elif parsed.command == "config":
        cmd_config()
    elif parsed.command == "chat":
        cmd_chat()
    elif parsed.command == "orchestrate":
        cmd_orchestrate(parsed)
    elif parsed.command == "agent":
        if parsed.agent_cmd == "list":
            cmd_agent_list()
        else:
            print("Usage: jojo agent list")
    elif parsed.command == "skill":
        if parsed.skill_cmd == "list":
            cmd_skill_list()
        else:
            print("Usage: jojo skill list")
    elif parsed.command == "mcp":
        if parsed.mcp_cmd == "list":
            cmd_mcp_list()
        elif parsed.mcp_cmd == "connect":
            cmd_mcp_connect(parsed)
        else:
            print("Usage: jojo mcp list | jojo mcp connect <name>")
    elif parsed.command == "job":
        if parsed.job_cmd == "list":
            cmd_job_list()
        elif parsed.job_cmd == "add":
            cmd_job_add(parsed)
        elif parsed.job_cmd == "remove":
            cmd_job_remove(parsed)
        else:
            print("Usage: jojo job list | jojo job add --name ... --cron ... --task ... | jojo job remove <name>")
    else:
        print("=" * 50)
        print("  JoJo Personal AI Assistant")
        print("=" * 50)
        cmd_config()
        print("=" * 50)
        print("JoJo Agent initialized.")


if __name__ == "__main__":
    main()
