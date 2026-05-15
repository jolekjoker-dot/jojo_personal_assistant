from src.jojo.tools.base import Tool, tool
from src.jojo.tools.registry import ToolRegistry, registry
from src.jojo.tools.schema import function_to_schema

# 注册所有内置工具
from src.jojo.tools.builtin.search import web_search
from src.jojo.tools.builtin.files import read_file, write_file, list_files
from src.jojo.tools.builtin.python import execute_python

registry.register_from_decorated(web_search)
registry.register_from_decorated(read_file)
registry.register_from_decorated(write_file)
registry.register_from_decorated(list_files)
registry.register_from_decorated(execute_python)

__all__ = [
    "Tool",
    "tool",
    "ToolRegistry",
    "registry",
    "function_to_schema",
]
