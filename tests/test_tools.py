"""
工具系统单元测试。
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.jojo.tools.base import Tool, tool
from src.jojo.tools.schema import function_to_schema
from src.jojo.tools.sandbox import (
    resolve_path, validate_python_code, SandboxViolation,
)
from src.jojo.tools.registry import ToolRegistry


class TestJsonSchema:
    """JSON Schema 自动生成测试。"""

    def test_simple_function(self):
        async def foo(name: str, count: int = 5) -> str: ...
        schema = function_to_schema(foo)
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "count" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["count"]["type"] == "integer"
        assert "name" in schema["required"]       # 无默认值 → 必填
        assert "count" not in schema["required"]   # 有默认值 → 非必填

    def test_all_optional_params(self):
        async def bar(x: int = 1, y: str = "hi") -> str: ...
        schema = function_to_schema(bar)
        assert schema["required"] == []

    def test_no_type_hints(self):
        async def baz(a, b): ...
        schema = function_to_schema(baz)
        # 无类型注解 → 默认 string
        assert schema["properties"]["a"]["type"] == "string"


class TestToolDecorator:
    """@tool 装饰器测试。"""

    def test_decorator_creates_tool(self):
        @tool("test_func", "A test tool")
        async def test_func(x: str) -> str:
            return x

        assert hasattr(test_func, "tool")
        assert isinstance(test_func.tool, Tool)
        assert test_func.tool.name == "test_func"
        assert test_func.tool.description == "A test tool"
        assert "x" in test_func.tool.parameters["properties"]

    def test_tool_execute(self):
        @tool("add", "Add two numbers")
        async def add(a: int, b: int) -> str:
            return str(a + b)

        result = asyncio.run(add.tool.execute(a=1, b=2))
        assert result == "3"

    def test_tool_to_openai_schema(self):
        @tool("my_tool", "desc")
        async def my_tool(q: str) -> str:
            return q

        s = my_tool.tool.to_openai_schema()
        assert s["type"] == "function"
        assert s["function"]["name"] == "my_tool"
        assert s["function"]["description"] == "desc"


class TestToolRegistry:
    """ToolRegistry 测试。"""

    def setup_method(self):
        self.registry = ToolRegistry(_singleton=False)  # 独立实例，不影响全局

    def test_register_and_get(self):
        @tool("t1", "Tool 1")
        async def t1(x: str) -> str:
            return x
        self.registry.register_from_decorated(t1)
        assert self.registry.get("t1") is not None
        assert "t1" in self.registry.list_tools()

    def test_execute_by_name(self):
        @tool("echo", "Echo")
        async def echo(msg: str) -> str:
            return msg
        self.registry.register_from_decorated(echo)
        result = asyncio.run(self.registry.execute("echo", msg="hello"))
        assert result == "hello"

    def test_execute_missing_tool(self):
        with pytest.raises(ValueError, match="not found"):
            asyncio.run(self.registry.execute("nonexistent"))

    def test_to_openai_schemas(self):
        @tool("a", "A")
        async def a(x: str) -> str:
            return x
        self.registry.register_from_decorated(a)
        schemas = self.registry.to_openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "a"

    def test_unregister(self):
        @tool("temp", "Temp")
        async def temp() -> str:
            return ""
        self.registry.register_from_decorated(temp)
        self.registry.unregister("temp")
        assert self.registry.get("temp") is None


class TestSandbox:
    """工作目录沙箱测试。"""

    def test_resolve_valid_path(self):
        result = resolve_path("data/test.txt")
        assert result.is_absolute()
        assert "data" in str(result)

    def test_resolve_path_traversal_blocked(self):
        with pytest.raises(SandboxViolation, match="Path traversal"):
            resolve_path("../../etc/passwd")

    def test_validate_python_code_safe(self):
        validate_python_code("x = 1 + 1\nprint(x)")

    def test_validate_python_code_blocks_os_system(self):
        with pytest.raises(SandboxViolation, match="os.system"):
            validate_python_code("import os; os.system('ls')")

    def test_validate_python_code_blocks_eval(self):
        with pytest.raises(SandboxViolation):
            validate_python_code("eval('1+1')")

    def test_validate_python_code_blocks_exec(self):
        with pytest.raises(SandboxViolation):
            validate_python_code("exec('x=1')")

    def test_validate_python_code_blocks_subprocess(self):
        with pytest.raises(SandboxViolation):
            validate_python_code("import subprocess; subprocess.run('ls')")


class TestFileTools:
    """文件工具集成测试。"""

    def test_read_write_file(self):
        from src.jojo.tools.builtin.files import read_file, write_file

        result = asyncio.run(write_file.tool.execute(
            path="data/test_write.txt",
            content="hello world",
        ))
        assert "成功" in result

        content = asyncio.run(read_file.tool.execute(
            path="data/test_write.txt",
        ))
        assert "hello world" in content

        # Cleanup
        Path("data/test_write.txt").unlink()

    def test_read_nonexistent(self):
        from src.jojo.tools.builtin.files import read_file

        result = asyncio.run(read_file.tool.execute(path="data/nonexistent.xyz"))
        assert "不存在" in result

    def test_list_files(self):
        from src.jojo.tools.builtin.files import list_files

        result = asyncio.run(list_files.tool.execute(path="data"))
        assert "data" in result  # Should show directory name or items


class TestPythonSandbox:
    """Python 沙箱执行测试。"""

    def test_simple_expression(self):
        from src.jojo.tools.builtin.python import execute_python

        result = asyncio.run(execute_python.tool.execute(code="1 + 1"))
        assert "2" in result

    def test_print_output(self):
        from src.jojo.tools.builtin.python import execute_python

        result = asyncio.run(execute_python.tool.execute(
            code="print('hello world')"
        ))
        assert "hello world" in result

    def test_blocked_operation(self):
        from src.jojo.tools.builtin.python import execute_python

        result = asyncio.run(execute_python.tool.execute(
            code="import os; os.system('echo hi')"
        ))
        assert "SandboxViolation" in result or "执行失败" in result


class TestGlobalRegistry:
    """全局 registry 已预加载所有内置工具。"""

    def test_all_builtin_tools_registered(self):
        # 从 registry 模块直接导入，避免 __init__.py 加载时序问题
        from src.jojo.tools.registry import registry
        tools = registry.list_tools()
        assert "web_search" in tools
        assert "read_file" in tools
        assert "write_file" in tools
        assert "list_files" in tools
        assert "execute_python" in tools
