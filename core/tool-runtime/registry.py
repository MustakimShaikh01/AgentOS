"""
core/tool-runtime/registry.py

Tool registry: the central catalogue of all tools available to agents.

Design:
    Tools are registered by name. Agents don't import tools directly —
    they call the registry. This decouples agent logic from tool implementation.

    In Stage 4 (Tool Runtime capability), this becomes MCP-compatible
    and supports permissions, sandboxing, and external plugins.

    For now (Stage 1), it's a simple dict-based registry with a web search
    and a Python calculator as starting tools.
"""

import json
import asyncio
from typing import Callable, Any


class Tool:
    def __init__(self, name: str, description: str, fn: Callable):
        self.name = name
        self.description = description
        self.fn = fn

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}


class ToolRegistry:
    """
    Registry of all tools agents can use.
    Register tools with @registry.register(), call with registry.execute().
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str):
        """Decorator to register a tool function."""
        def decorator(fn: Callable):
            self._tools[name] = Tool(name=name, description=description, fn=fn)
            return fn
        return decorator

    def get_tool_descriptions(self) -> list[dict]:
        """Return all tool metadata for injection into agent prompts."""
        return [t.to_dict() for t in self._tools.values()]

    async def execute(self, tool_name: str, tool_input: dict) -> str:
        """Execute a registered tool and return its result as a string."""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found. Available: {list(self._tools.keys())}"

        try:
            if asyncio.iscoroutinefunction(tool.fn):
                result = await tool.fn(**tool_input)
            else:
                result = tool.fn(**tool_input)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"


# ── Default Tool Registry (Stage 1 tools) ────────────────────────────────────

registry = ToolRegistry()


@registry.register(
    name="web_search",
    description="Search the web for information. Input: {'query': str}"
)
async def web_search(query: str) -> str:
    """
    Stage 1: Mock web search.
    Stage 4: Replace with real Serper/Tavily/DuckDuckGo integration.
    """
    # TODO: Replace with real search API in Stage 4
    return f"[Mock search results for: '{query}']\n1. Result one about {query}\n2. Result two about {query}"


@registry.register(
    name="calculate",
    description="Perform a mathematical calculation. Input: {'expression': str}"
)
def calculate(expression: str) -> str:
    """Safe math evaluator using ast.literal_eval."""
    import ast
    import operator as op

    allowed_ops = {
        ast.Add: op.add, ast.Sub: op.sub,
        ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow,
    }

    def eval_expr(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return allowed_ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
        raise ValueError(f"Unsupported operation: {type(node)}")

    try:
        tree = ast.parse(expression, mode="eval")
        result = eval_expr(tree.body)
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"
