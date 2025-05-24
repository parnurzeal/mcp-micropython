# tests/test_tool_handlers.py
import sys
import uasyncio
import ujson

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.stdio_server import process_mcp_message
from tests.common_test_utils import setup_test_registry

# --- Tool Handler Tests (via process_mcp_message) ---


async def test_process_mcp_initialize():
    registry = setup_test_registry()
    req = {"jsonrpc": "2.0", "method": "initialize", "id": "init-1"}
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "init-1"
    assert "result" in resp
    assert "serverInfo" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "MicroPython MCP Server"
    assert resp["result"]["serverInfo"]["version"] == "0.1.0"
    assert "capabilities" in resp["result"]
    assert "tools" in resp["result"]["capabilities"]
    assert resp["result"]["capabilities"]["tools"] == {"listChanged": False}
    # Also check for resources capability as it's part of initialize
    assert "resources" in resp["result"]["capabilities"]
    assert resp["result"]["capabilities"]["resources"] == {
        "subscribe": False,
        "listChanged": False,
    }
    assert resp["result"]["protocolVersion"] == "2025-03-26"
    print("test_process_mcp_initialize PASSED")


async def test_initialize_response_includes_protocol_version():
    registry = setup_test_registry()
    req = {"jsonrpc": "2.0", "method": "initialize", "id": "init-spec-1"}
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "init-spec-1"
    assert "result" in resp
    assert "serverInfo" in resp["result"]
    assert resp["result"]["serverInfo"]["name"] == "MicroPython MCP Server"
    assert resp["result"]["serverInfo"]["version"] == "0.1.0"
    assert "protocolVersion" in resp["result"]
    assert resp["result"]["protocolVersion"] == "2025-03-26"
    print("test_initialize_response_includes_protocol_version PASSED")


async def test_process_mcp_tools_list():
    registry = setup_test_registry()
    req = {"jsonrpc": "2.0", "method": "tools/list", "id": "list-1"}
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "list-1"
    assert "result" in resp
    assert "tools" in resp["result"]
    tools_list = resp["result"]["tools"]
    assert len(tools_list) == 4
    echo_tool_def = next(t for t in tools_list if t["name"] == "echo")
    assert echo_tool_def["description"] == "Echoes"
    assert echo_tool_def["inputSchema"] == {
        "type": "object",
        "properties": {"message": {"type": "string"}},
    }
    info_tool_def = next(t for t in tools_list if t["name"] == "info")
    assert info_tool_def["description"] == "No params"
    assert info_tool_def["inputSchema"] == {
        "type": "object",
        "properties": {},
    }
    print("test_process_mcp_tools_list PASSED")


async def test_process_mcp_tools_call_echo():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "micropython"}},
        "id": "call-echo-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-echo-1"
    assert "result" in resp
    assert resp["result"]["content"] == [{"type": "text", "text": "echo: micropython"}]
    assert resp["result"]["isError"] is False
    print("test_process_mcp_tools_call_echo PASSED")


async def test_process_mcp_tools_call_add_dict_args():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 10, "b": 20}},
        "id": "call-add-dict-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-add-dict-1"
    assert "result" in resp
    assert resp["result"]["content"] == [{"type": "text", "text": "30.0"}]
    assert resp["result"]["isError"] is False
    print("test_process_mcp_tools_call_add_dict_args PASSED")


async def test_process_mcp_tools_call_add_list_args():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "add", "arguments": [15, 25]},
        "id": "call-add-list-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-add-list-1"
    assert "result" in resp
    assert resp["result"]["content"] == [{"type": "text", "text": "40.0"}]
    assert resp["result"]["isError"] is False
    print("test_process_mcp_tools_call_add_list_args PASSED")


async def test_process_mcp_tools_call_info_null_args():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "info", "arguments": None},
        "id": "call-info-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-info-1"
    assert "result" in resp
    assert resp["result"]["content"] == [{"type": "text", "text": "no_params_tool_ran"}]
    assert resp["result"]["isError"] is False
    print("test_process_mcp_tools_call_info_null_args PASSED")


async def test_process_mcp_tools_call_tool_not_found():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "non_existent_tool", "arguments": {}},
        "id": "call-notfound-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-notfound-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32602
    assert resp["error"]["message"] == "Invalid Params"
    assert "data" in resp["error"]
    assert "Tool 'non_existent_tool' not found" in resp["error"]["data"]
    print("test_process_mcp_tools_call_tool_not_found PASSED")


async def test_process_mcp_tools_call_tool_handler_error():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "error_tool", "arguments": {}},
        "id": "call-error-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-error-1"
    assert "result" in resp
    assert resp["result"]["isError"] is True
    assert len(resp["result"]["content"]) == 1
    assert resp["result"]["content"][0]["type"] == "text"
    assert (
        "Error executing tool 'error_tool': This tool intentionally errors."
        in resp["result"]["content"][0]["text"]
    )
    print("test_process_mcp_tools_call_tool_handler_error PASSED")


async def test_process_mcp_tools_call_missing_tool_name():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"arguments": {}},
        "id": "call-missingname-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-missingname-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32602
    assert resp["error"]["message"] == "Invalid Params"
    assert "data" in resp["error"]
    assert (
        "Tool 'name' not provided in parameters for tools/call."
        in resp["error"]["data"]
    )
    print("test_process_mcp_tools_call_missing_tool_name PASSED")


async def test_process_mcp_method_not_found():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "non_existent_mcp_method",
        "id": "method-notfound-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "method-notfound-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32601
    assert resp["error"]["message"] == "Method Not Found"
    assert "data" in resp["error"]
    assert (
        "The method 'non_existent_mcp_method' is not supported by this server."
        in resp["error"]["data"]
    )
    print("test_process_mcp_method_not_found PASSED")


async def run_tool_handler_tests():
    print("\n--- Running MCP Handler Tests (Initialize & Tools) ---")
    await test_process_mcp_initialize()
    await test_initialize_response_includes_protocol_version()
    await test_process_mcp_tools_list()
    await test_process_mcp_tools_call_echo()
    await test_process_mcp_tools_call_add_dict_args()
    await test_process_mcp_tools_call_add_list_args()
    await test_process_mcp_tools_call_info_null_args()
    await test_process_mcp_tools_call_tool_not_found()
    await test_process_mcp_tools_call_tool_handler_error()
    await test_process_mcp_tools_call_missing_tool_name()
    await test_process_mcp_method_not_found()
    print("--- MCP Handler Tests (Initialize & Tools) Complete ---")


if __name__ == "__main__":
    uasyncio.run(run_tool_handler_tests())
