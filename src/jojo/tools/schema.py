"""
JSON Schema 自动生成 — 从 Python 函数签名生成 LLM 可读的 JSON Schema。
"""

import inspect
from typing import Any, Callable, get_type_hints


# Python 类型 → JSON Schema type 映射
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def python_type_to_json_type(py_type: type) -> str:
    """Python 类型 → JSON Schema 类型名。"""
    origin = getattr(py_type, "__origin__", None)
    if origin is not None:
        return "array" if origin is list else _TYPE_MAP.get(origin, "string")

    return _TYPE_MAP.get(py_type, "string")


def function_to_schema(func: Callable) -> dict[str, Any]:
    """
    从函数签名自动生成 JSON Schema。

    解析参数名、类型注解和默认值，生成符合 JSON Schema 规范的参数定义。

    Args:
        func: Python 函数

    Returns:
        {"type": "object", "properties": {...}, "required": [...]}
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        py_type = hints.get(param_name, str)
        json_type = python_type_to_json_type(py_type)

        prop: dict[str, Any] = {
            "type": json_type,
            "description": f"Parameter: {param_name}",
        }

        # 有默认值 → 非必填
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
