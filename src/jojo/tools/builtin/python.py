"""
内置工具：execute_python — 安全沙箱执行 Python 代码。

限制:
1. 只能访问工作目录内的文件
2. 禁止危险系统调用
3. 只能导入白名单内的模块
"""

import sys
import io
import traceback

from src.jojo.tools.base import tool
from src.jojo.tools.sandbox import validate_python_code, ALLOWED_IMPORTS
from src.jojo.logger import logger


@tool(
    "execute_python",
    "在安全沙箱中执行 Python 代码。禁止文件删除、系统调用、网络操作等危险操作。"
    "可导入的模块: json, math, re, datetime, collections, itertools, functools 等",
    risk="dangerous",
)
async def execute_python(code: str) -> str:
    """
    在受限环境中执行 Python 代码并返回 stdout 输出。

    Args:
        code: 要执行的 Python 代码（单行或多行）
    """
    try:
        # 1. 安全检查
        validate_python_code(code)

        # 2. 构建受限的全局命名空间
        safe_globals: dict = {
            "__builtins__": _build_safe_builtins(),
        }
        # 注入白名单模块
        for mod_name in ALLOWED_IMPORTS:
            try:
                mod = __import__(mod_name)
                safe_globals[mod_name] = mod
            except ImportError:
                pass

        safe_locals: dict = {}

        # 3. 捕获 stdout
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture

        try:
            exec(code, safe_globals, safe_locals)
        finally:
            sys.stdout = old_stdout

        output = stdout_capture.getvalue()

        # 4. 检查表达式结果
        lines = [line.strip() for line in code.strip().split("\n") if line.strip()]
        if lines:
            last_line = lines[-1]
            try:
                result = eval(last_line, safe_globals, safe_locals)
                if result is not None and not output:
                    output = str(result)
            except Exception:
                pass  # 最后一行不是表达式，忽略

        logger.info(f"Executed Python code ({len(code)} chars)")
        return output if output else "(执行完成，无输出)"

    except Exception as e:
        return f"执行失败: {type(e).__name__}: {e}"


def _build_safe_builtins() -> dict:
    """构建受限的内建函数集合。"""
    import builtins

    blocked = {"__import__", "eval", "exec", "open", "input",
                "compile", "breakpoint", "memoryview",
                "globals", "locals", "vars", "dir"}

    return {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if name not in blocked and not name.startswith("_")
    }
