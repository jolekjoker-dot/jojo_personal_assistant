"""
内置工具：文件读写 — 受工作目录沙箱约束。
"""

from pathlib import Path

from src.jojo.tools.base import tool
from src.jojo.tools.sandbox import resolve_path
from src.jojo.logger import logger


@tool(
    "read_file",
    "读取指定文件的内容。只能访问工作目录内的文件",
    risk="read",
)
async def read_file(path: str) -> str:
    """
    读取文件内容。

    Args:
        path: 文件路径（相对于工作目录，或绝对路径在工作目录内）
    """
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"文件不存在: {path}"
        if not target.is_file():
            return f"路径不是文件: {path}"
        content = target.read_text(encoding="utf-8")
        logger.info(f"Read file: {target} ({len(content)} chars)")
        return content
    except Exception as e:
        return f"读取失败: {e}"


@tool(
    "write_file",
    "将内容写入指定文件。只能写入工作目录内的文件",
    risk="write",
)
async def write_file(path: str, content: str) -> str:
    """
    写入文件内容。

    Args:
        path: 文件路径（相对于工作目录）
        content: 要写入的内容
    """
    try:
        target = resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info(f"Wrote file: {target} ({len(content)} chars)")
        return f"写入成功: {path} ({len(content)} 字符)"
    except Exception as e:
        return f"写入失败: {e}"


@tool(
    "list_files",
    "列出指定目录下的文件和子目录。只能查看工作目录内的路径",
    risk="read",
)
async def list_files(path: str = ".") -> str:
    """
    列出目录内容。

    Args:
        path: 目录路径（相对于工作目录）
    """
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"目录不存在: {path}"
        if not target.is_dir():
            return f"路径不是目录: {path}"

        items = []
        for item in sorted(target.iterdir()):
            prefix = "📁 " if item.is_dir() else "📄 "
            items.append(f"{prefix}{item.name}")

        if not items:
            return f"目录为空: {path}"

        return f"目录 {path} 的内容 ({len(items)} 项):\n" + "\n".join(items)
    except Exception as e:
        return f"列出目录失败: {e}"
