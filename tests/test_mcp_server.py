import sys
import uasyncio  # uasyncio should be imported after sys path manipulation if needed
import ujson  # ujson should be imported after sys path manipulation if needed

# Ensure the project root (current working directory when tests are run from root)
# is in the path, so 'mcp' package can be found.
# MicroPython's default sys.path usually includes '' (current dir of script) and '.' (cwd).
# However, being explicit can help in some environments or if script is run differently.
# If '.' is already in sys.path from cwd, this might be redundant but harmless.
if "." not in sys.path:
    sys.path.insert(0, ".")
if (
    "" not in sys.path and sys.path[0] != "."
):  # Python often adds script's dir as '' at pos 0
    # This part is tricky as script_dir behavior varies.
    # For `micropython tests/test_mcp_server.py` run from project root,
    # '.' (cwd) is the key.
    pass


# Now try importing the modules
from mcp.registry import ToolRegistry, ToolError  # Import ToolError
from mcp.types import (
    create_success_response,
    create_error_response,
)
from mcp.stdio_server import process_mcp_message, stdio_server  # Import stdio_server


# --- Mock Tool Handlers ---
async def mock_echo_tool(message: str):
    return f"echo: {message}"


async def mock_add_tool(a, b):
    return float(a) + float(b)


async def mock_no_params_tool():
    return "no_params_tool_ran"


async def mock_error_tool():
    raise ValueError("This tool intentionally errors.")


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
    registry.register_tool(
        "info", "No params", {}, mock_no_params_tool  # Empty dict for schema properties
    )
    registry.register_tool(
        "info_null",
        "No params null schema",
        None,
        mock_no_params_tool,  # None for schema properties
    )

    defs = registry.list_tool_definitions()
    assert len(defs) == 3

    echo_def = next(d for d in defs if d["name"] == "echo")
    assert echo_def["inputSchema"] == {
        "type": "object",
        "properties": {"message": {"type": "string"}},
    }

    info_def = next(d for d in defs if d["name"] == "info")
    assert info_def["inputSchema"] is None  # Expect null for empty properties

    info_null_def = next(d for d in defs if d["name"] == "info_null")
    assert info_null_def["inputSchema"] is None  # Expect null for None properties

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
    result = await registry.call_tool("info", None)  # Call with None for no arguments
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
    except ToolError as e:  # Expect ToolError now
        # The ToolError message is "Error executing tool 'error_tool': This tool intentionally errors."
        assert "Error executing tool 'error_tool'" in str(e)
        assert "This tool intentionally errors" in str(e)
    print("test_tool_registry_call_tool_handler_error PASSED")


# --- process_mcp_message Tests ---


# Helper to create a registry with common mock tools for these tests
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


async def test_process_mcp_initialize():
    registry = setup_test_registry()
    req = {"jsonrpc": "2.0", "method": "initialize", "id": "init-1"}
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "init-1"
    assert "result" in resp
    assert "serverName" in resp["result"]
    assert resp["result"]["serverName"] == "MicroPython MCP Server"
    assert "capabilities" in resp["result"]
    assert "tools" in resp["result"]["capabilities"]
    assert resp["result"]["capabilities"]["tools"] == {"listChanged": False}
    assert (
        resp["result"]["specificationVersion"] == "2025-03-26"
    )  # Check for spec version
    print("test_process_mcp_initialize PASSED")


# This test is identical to test_process_mcp_initialize but kept for clarity if one wants to separate them
async def test_initialize_response_includes_spec_version():
    registry = setup_test_registry()
    req = {"jsonrpc": "2.0", "method": "initialize", "id": "init-spec-1"}
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "init-spec-1"
    assert "result" in resp
    assert "specificationVersion" in resp["result"]
    assert resp["result"]["specificationVersion"] == "2025-03-26"
    print("test_initialize_response_includes_spec_version PASSED")


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
    assert info_tool_def["inputSchema"] is None
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
    assert resp.get("result") == "echo: micropython"
    print("test_process_mcp_tools_call_echo PASSED")


async def test_process_mcp_tools_call_add_dict_args():
    registry = setup_test_registry()
    # Tool 'add' was registered with param_names=["a", "b"], so ToolRegistry.call_tool
    # will convert list args to kwargs. If dict args are passed, they should also work.
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 10, "b": 20}},
        "id": "call-add-dict-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-add-dict-1"
    assert resp.get("result") == 30.0
    print("test_process_mcp_tools_call_add_dict_args PASSED")


async def test_process_mcp_tools_call_add_list_args():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "add", "arguments": [15, 25]},  # Using list for add tool
        "id": "call-add-list-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-add-list-1"
    assert resp.get("result") == 40.0
    print("test_process_mcp_tools_call_add_list_args PASSED")


async def test_process_mcp_tools_call_info_null_args():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "info",
            "arguments": None,
        },  # arguments: null for no-param tools
        "id": "call-info-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-info-1"
    assert resp.get("result") == "no_params_tool_ran"
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
    assert resp["error"]["code"] == -32602  # Invalid Params (ValueError from registry)
    assert (
        resp["error"]["message"] == "Invalid Params"
    )  # The message set by handle_tools_call
    assert (
        "data" in resp["error"]
    )  # The specific error from registry.call_tool goes into data
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
    assert "error" in resp
    assert resp["error"]["code"] == -32000  # Tool Execution Error
    assert "This tool intentionally errors" in resp["error"]["data"]
    print("test_process_mcp_tools_call_tool_handler_error PASSED")


async def test_process_mcp_tools_call_missing_tool_name():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"arguments": {}},  # Missing 'name'
        "id": "call-missingname-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "call-missingname-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32602  # Invalid Params
    assert resp["error"]["message"] == "Invalid Params"  # Check the main message
    assert "data" in resp["error"]  # The detailed message goes into data
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
    assert resp["error"]["code"] == -32601  # Method Not Found
    assert resp["error"]["message"] == "Method Not Found"  # Check the main message
    assert "data" in resp["error"]  # The detailed message goes into data
    assert (
        "The method 'non_existent_mcp_method' is not supported by this server."
        in resp["error"]["data"]
    )
    print("test_process_mcp_method_not_found PASSED")


# This test is more for the stdio_server's main loop, which does initial JSON parsing
# and basic request validation before calling process_mcp_message.
# async def test_process_mcp_invalid_request_structure():
#     registry = setup_test_registry()
#     req = {"jsonrpc": "2.0", "id": "invalid-struct-1"} # Missing 'method'
#     # In stdio_server.py, this kind of malformed request is caught before process_mcp_message
#     # If it somehow reached process_mcp_message, it would likely result in method not found or error.
#     # For now, this specific test is omitted as it's handled by the caller of process_mcp_message.
#     print("test_process_mcp_invalid_request_structure (covered by stdio_server loop) SKIPPED")


async def run_all_tests():
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

    print("\n--- Running process_mcp_message Tests ---")
    await test_process_mcp_initialize()
    await test_process_mcp_tools_list()
    await test_process_mcp_tools_call_echo()
    await test_process_mcp_tools_call_add_dict_args()
    await test_process_mcp_tools_call_add_list_args()
    await test_process_mcp_tools_call_info_null_args()
    await test_process_mcp_tools_call_tool_not_found()
    await test_process_mcp_tools_call_tool_handler_error()
    await test_process_mcp_tools_call_missing_tool_name()
    await test_process_mcp_method_not_found()
    # await test_process_mcp_invalid_request_structure() # Skipped for now
    print("--- process_mcp_message Tests Complete ---")


# --- stdio_server main loop Tests (for notifications) ---


class MockStreamReader:
    def __init__(self, lines_to_read):
        self.lines = [line.encode("utf-8") + b"\n" for line in lines_to_read]
        self.pos = 0

    async def readline(self):
        if self.pos < len(self.lines):
            line = self.lines[self.pos]
            self.pos += 1
            return line
        return b""  # Simulate EOF


class MockStreamWriter:
    def __init__(self):
        self.written_data = bytearray()

    def write(self, data):
        self.written_data.extend(data)

    async def drain(self):
        pass  # No-op for mock

    def get_written_str(self):
        return self.written_data.decode("utf-8")


async def test_stdio_server_handles_notification():
    registry = setup_test_registry()
    # A notification message (no "id" field)
    notification_msg_str = ujson.dumps(
        {"jsonrpc": "2.0", "method": "some/notification", "params": {"data": "test"}}
    )

    reader = MockStreamReader(
        [notification_msg_str, ""]
    )  # Add empty line to trigger EOF after one message
    writer = MockStreamWriter()

    # Run the server with mock streams. It should process one message and then EOF.
    await stdio_server(
        tool_registry=registry, custom_reader=reader, custom_writer=writer
    )

    # Assert that nothing was written to the output stream for a notification
    written_output = writer.get_written_str()
    assert (
        written_output == ""
    ), f"Expected no output for notification, but got: {written_output}"
    print("test_stdio_server_handles_notification PASSED")


async def test_stdio_server_sends_response_for_request():
    registry = setup_test_registry()
    request_msg_str = ujson.dumps(
        {"jsonrpc": "2.0", "method": "initialize", "id": "init-req-1"}
    )

    reader = MockStreamReader([request_msg_str, ""])
    writer = MockStreamWriter()

    await stdio_server(
        tool_registry=registry, custom_reader=reader, custom_writer=writer
    )

    written_output = writer.get_written_str().strip()
    assert written_output != "", "Expected output for a request, but got none."
    try:
        response_json = ujson.loads(written_output)
        assert response_json.get("id") == "init-req-1"
        assert "result" in response_json
    except ValueError:
        assert False, f"Output was not valid JSON: {written_output}"
    print("test_stdio_server_sends_response_for_request PASSED")


if __name__ == "__main__":
    # Update run_all_tests to include the new stdio_server tests
    async def run_all_tests_updated():
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

        print("\n--- Running process_mcp_message Tests ---")
        await test_process_mcp_initialize()
        await test_initialize_response_includes_spec_version()  # New test
        await test_process_mcp_tools_list()
        await test_process_mcp_tools_call_echo()
        await test_process_mcp_tools_call_add_dict_args()
        await test_process_mcp_tools_call_add_list_args()
        await test_process_mcp_tools_call_info_null_args()
        await test_process_mcp_tools_call_tool_not_found()
        await test_process_mcp_tools_call_tool_handler_error()
        await test_process_mcp_tools_call_missing_tool_name()
        await test_process_mcp_method_not_found()
        print("--- process_mcp_message Tests Complete ---")

        print("\n--- Running stdio_server Loop Tests ---")
        await test_stdio_server_handles_notification()  # New test
        await test_stdio_server_sends_response_for_request()  # New test
        print("--- stdio_server Loop Tests Complete ---")

    uasyncio.run(run_all_tests_updated())
