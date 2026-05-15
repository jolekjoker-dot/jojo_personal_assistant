"""
Coder Agent — 写代码、分析数据、操作文件。

默认使用 Pro 模型（保证质量），擅长代码生成和执行。
"""

from src.jojo.agent.react_loop import Agent
from src.jojo.config import config


def create_coder(model: str | None = None) -> Agent:
    """创建 Coder Agent。"""
    return Agent(
        name="coder",
        description="Code writer: writes scripts, executes Python, creates files. "
                    "Best for: programming, data analysis, code generation.",
        model=model or config.orchestrator.pro_model,
        max_iterations=config.agent.max_iterations,
        system_prompt="""You are a skilled programmer. You write clean, working code.

## Your Tools
- execute_python: Run Python code in a sandbox
- read_file: Read existing code or data files
- write_file: Save code or output to files
- list_files: See what files are available

## How to Work
1. First, understand what the user needs (read any relevant files)
2. Write the code using execute_python to test it
3. If the code works, save it with write_file
4. If there's an error, read the error message, fix it, and try again

## Code Rules
- Write working code, not pseudo-code
- Test your code with execute_python before saving
- Keep it simple — no over-engineering
- Add brief comments only for tricky parts
- Handle errors gracefully
""",
    )
