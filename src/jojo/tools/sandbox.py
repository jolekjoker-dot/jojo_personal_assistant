"""
工作目录沙箱 — 确保所有文件/Python 操作被限制在 workspace_root 内。
"""

from pathlib import Path

from src.jojo.config import config


class SandboxViolation(Exception):
    """沙箱违规异常。"""
    pass


def resolve_path(file_path: str) -> Path:
    """
    解析文件路径并校验是否在工作目录内。

    规则:
    1. 将相对路径转为工作目录下的绝对路径
    2. 拒绝路径穿越攻击 (../../etc/passwd)
    3. 只允许访问 workspace_root 及其子目录
    """
    root = Path(config.agent.workspace_root).resolve()
    target = (root / file_path).resolve()

    # 检查是否在 workspace_root 之内
    try:
        target.relative_to(root)
    except ValueError:
        raise SandboxViolation(
            f"Path traversal blocked: '{file_path}' resolves to '{target}' "
            f"which is outside workspace '{root}'"
        )

    return target


def validate_python_code(code: str) -> None:
    """
    校验 Python 代码安全性。

    拦截危险操作:
    - 系统调用 (os.system, subprocess, ...)
    - 文件删除 (os.remove, shutil.rmtree, ...)
    - 模块热加载 (importlib.reload, ...)
    - 网络操作（允许 requests/httpx）
    """
    dangerous = [
        "os.system", "subprocess", "shutil.rmtree", "shutil.move",
        "os.remove", "os.rmdir", "os.unlink",
        "importlib.reload", "__import__",
        "eval(", "exec(",
        "open(",           # 文件操作由 file_tools 提供
        "sys.exit", "os.exit", "quit(",
    ]

    code_lower = code.lower()
    for pattern in dangerous:
        if pattern.lower() in code_lower:
            raise SandboxViolation(
                f"Dangerous operation blocked: '{pattern}' is not allowed in sandbox"
            )


ALLOWED_IMPORTS = {
    "json", "math", "re", "datetime", "collections",
    "itertools", "functools", "typing", "dataclasses",
    "copy", "hashlib", "base64", "uuid",
    "random", "statistics", "decimal", "fractions",
    "string", "textwrap", "unicodedata",
    "csv", "io", "pathlib",
    "operator", "enum", "types",
}
