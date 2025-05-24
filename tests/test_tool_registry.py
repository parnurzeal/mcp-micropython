# tests/test_tool_registry.py
import sys
import uasyncio

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.registry import ToolRegistry, ToolError
from tests.common_test_utils import (
    mock_echo_tool,
    mock_add_tool,
    mock_no_params_tool,
    mock_error_tool,
)


# --- ToolRegistry Tests ---
def test_tool_registry_init():
    registry = ToolRegistry()
    assert registry._tools == {}
    print("test_tool_registry_init PASSED")


def test_tool_registry_register_tool():
    registry = ToolRegistry()
    registry.register_tool(
        "echo", "Echoes a message", {"message": {"type": "string"}}, mock_echo_tool
    )
    assert "echo" in registry._tools
    assert registry._tools["echo"]["definition"]["name"] == "echo"
    assert registry._tools["echo"]["handler"] == mock_echo_tool
    print("test_tool_registry_register_tool PASSED")


def test_tool_registry_list_definitions():
    registry = ToolRegistry()
    registry.register_tool(
        "echo", "Echoes", {"message": {"type": "string"}}, mock_echo_tool
    )
    registry.register_tool("info", "No params", {}, mock_no_params_tool)
    registry.register_tool(
        "info_null",
        "No params null schema",
        None,
        mock_no_params_tool,
    )

    defs = registry.list_tool_definitions()
    assert len(defs) == 3

    echo_def = next(d for d in defs if d["name"] == "echo")
    assert echo_def["inputSchema"] == {
        "type": "object",
        "properties": {"message": {"type": "string"}},
    }

    info_def = next(d for d in defs if d["name"] == "info")
    assert info_def["inputSchema"] == {
        "type": "object",
        "properties": {},
    }

    info_null_def = next(d for d in defs if d["name"] == "info_null")
    assert info_null_def["inputSchema"] == {
        "type": "object",
        "properties": {},
    }
    print("test_tool_registry_list_definitions PASSED")


async def test_tool_registry_call_tool_dict_params():
    registry = ToolRegistry()
    registry.register_tool(
        "echo", "Echoes", {"message": {"type": "string"}}, mock_echo_tool
    )
    result = await registry.call_tool("echo", {"message": "hello"})
    assert result == "echo: hello"
    print("test_tool_registry_call_tool_dict_params PASSED")


async def test_tool_registry_call_tool_list_params():
    registry = ToolRegistry()
    registry.register_tool(
        "add", "Adds", {"a": {}, "b": {}}, mock_add_tool, param_names=["a", "b"]
    )
    result = await registry.call_tool("add", [3, 5])
    assert result == 8.0
    print("test_tool_registry_call_tool_list_params PASSED")


async def test_tool_registry_call_tool_no_params():
    registry = ToolRegistry()
    registry.register_tool("info", "No params", None, mock_no_params_tool)
    result = await registry.call_tool("info", None)
    assert result == "no_params_tool_ran"
    print("test_tool_registry_call_tool_no_params PASSED")


async def test_tool_registry_call_tool_not_found():
    registry = ToolRegistry()
    try:
        await registry.call_tool("nonexistent", {})
        assert False, "ValueError not raised for nonexistent tool"
    except ValueError as e:
        assert "Tool 'nonexistent' not found" in str(e)
    print("test_tool_registry_call_tool_not_found PASSED")


async def test_tool_registry_call_tool_handler_error():
    registry = ToolRegistry()
    registry.register_tool("error_tool", "Errors", {}, mock_error_tool)
    try:
        await registry.call_tool("error_tool", {})
        assert False, "ToolError not raised from tool handler"
    except ToolError as e:
        assert "Error executing tool 'error_tool'" in str(e)
        assert "This tool intentionally errors" in str(e)
    print("test_tool_registry_call_tool_handler_error PASSED")


async def run_tool_registry_tests():
    print("--- Running ToolRegistry Tests ---")
    test_tool_registry_init()
    test_tool_registry_register_tool()
    test_tool_registry_list_definitions()
    await test_tool_registry_call_tool_dict_params()
    await test_tool_registry_call_tool_list_params()
    await test_tool_registry_call_tool_no_params()
    await test_tool_registry_call_tool_not_found()
    await test_tool_registry_call_tool_handler_error()
    print("--- ToolRegistry Tests Complete ---")


if __name__ == "__main__":
    uasyncio.run(run_tool_registry_tests())
