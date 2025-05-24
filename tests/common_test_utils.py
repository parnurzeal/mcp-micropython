# tests/common_test_utils.py
import sys

# Ensure the project root is in the path if this file is run directly for some reason,
# or if other test files import from it and their own path setup isn't sufficient.
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.registry import ToolRegistry


# --- Mock Tool Handlers ---
async def mock_echo_tool(message: str):
    return f"echo: {message}"


async def mock_add_tool(a, b):
    return float(a) + float(b)


async def mock_no_params_tool():
    return "no_params_tool_ran"


async def mock_error_tool():
    raise ValueError("This tool intentionally errors.")


# Helper to create a registry with common mock tools for tests
def setup_test_registry():
    registry = ToolRegistry()
    registry.register_tool(
        "echo", "Echoes", {"message": {"type": "string"}}, mock_echo_tool
    )
    registry.register_tool(
        "add",
        "Adds",
        {"a": {"type": "number"}, "b": {"type": "number"}},
        mock_add_tool,
        param_names=["a", "b"],
    )
    registry.register_tool("info", "No params", None, mock_no_params_tool)
    registry.register_tool("error_tool", "Errors", {}, mock_error_tool)
    return registry
