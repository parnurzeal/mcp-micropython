# tests/test_resource_handlers.py
import sys
import uasyncio
import ujson
import os  # For CWD and file operations in tests

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.stdio_server import process_mcp_message
from tests.common_test_utils import setup_test_registry

# --- Resource Handler Tests (via process_mcp_message) ---


async def test_process_mcp_resources_list():
    registry = setup_test_registry()
    req = {"jsonrpc": "2.0", "method": "resources/list", "id": "res-list-1"}
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "res-list-1"
    assert "result" in resp
    assert "resources" in resp["result"]
    assert len(resp["result"]["resources"]) == 1
    resource = resp["result"]["resources"][0]
    assert resource["uri"] == "file:///example.txt"
    assert resource["name"] == "Example Text File"
    print("test_process_mcp_resources_list PASSED")


async def test_process_mcp_resources_read_success():
    registry = setup_test_registry()
    cwd = os.getcwd()
    print(f"CWD in test_process_mcp_resources_read_success: {cwd}")
    file_name = "test_example_resource.txt"  # Use a unique name to avoid conflicts
    if not cwd.endswith("/"):
        cwd += "/"
    absolute_file_path = cwd + file_name
    file_uri = f"file://{absolute_file_path}"
    test_content = "This is content for resource read success test."

    try:
        with open(absolute_file_path, "w") as f:
            f.write(test_content)
        print(f"Successfully created '{absolute_file_path}' for test.")
    except Exception as e:
        print(f"Failed to create '{absolute_file_path}' for test: {e}")
        raise AssertionError(f"Setup failed: Could not create {absolute_file_path}")

    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": file_uri},
        "id": "res-read-abs-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "res-read-abs-1"
    assert "result" in resp, f"Response was: {resp}"
    assert "contents" in resp["result"]
    assert len(resp["result"]["contents"]) == 1
    content_resp = resp["result"]["contents"][0]
    assert content_resp["uri"] == file_uri
    assert content_resp["text"] == test_content
    assert content_resp["mimeType"] == "text/plain"

    try:
        os.remove(absolute_file_path)
        print(f"Successfully cleaned up '{absolute_file_path}'.")
    except Exception as e:
        print(f"Failed to clean up '{absolute_file_path}': {e}")
    print("test_process_mcp_resources_read_success PASSED")


async def test_process_mcp_resources_read_missing_uri():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {},
        "id": "res-read-err-1",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "res-read-err-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32602
    assert "Missing 'uri' parameter" in resp["error"]["data"]
    print("test_process_mcp_resources_read_missing_uri PASSED")


async def test_process_mcp_resources_read_unsupported_scheme():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "http://example.com/unsupported.txt"},
        "id": "res-read-err-2",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "res-read-err-2"
    assert "error" in resp
    assert resp["error"]["code"] == -32002
    assert "Unsupported URI Scheme" in resp["error"]["message"]
    print("test_process_mcp_resources_read_unsupported_scheme PASSED")


async def test_process_mcp_resources_read_file_not_found():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "file:///non_existent_file_for_sure.txt"},
        "id": "res-read-err-3",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "res-read-err-3"
    assert "error" in resp
    assert resp["error"]["code"] == -32001
    assert "File not found" in resp["error"]["data"]
    print("test_process_mcp_resources_read_file_not_found PASSED")


async def run_resource_handler_tests():
    print("\n--- Running MCP Handler Tests (Resources) ---")
    await test_process_mcp_resources_list()
    await test_process_mcp_resources_read_success()
    await test_process_mcp_resources_read_missing_uri()
    await test_process_mcp_resources_read_unsupported_scheme()
    await test_process_mcp_resources_read_file_not_found()
    print("--- MCP Handler Tests (Resources) Complete ---")


if __name__ == "__main__":
    uasyncio.run(run_resource_handler_tests())
