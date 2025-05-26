# tests/test_resource_handlers.py
import sys
import asyncio
import json
import os

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.server_core import ServerCore
from tests.common_test_utils import (
    setup_common_resource_registry,
    ResourceError,
    setup_test_registry,
    setup_common_prompt_registry,
)

# --- Resource Handler Tests (now using ServerCore.process_message_dict) ---


async def test_process_mcp_resources_list():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    req = {"jsonrpc": "2.0", "method": "resources/list", "id": "res-list-1"}
    resp = await server_core.process_message_dict(req)

    assert resp["id"] == "res-list-1"
    assert "result" in resp
    assert "resources" in resp["result"]
    resources = resp["result"]["resources"]
    assert len(resources) == 2  # From common_test_utils
    # ... (rest of list assertions)
    example_txt_res = next(
        (r for r in resources if r["uri"] == "file:///example.txt"), None
    )
    assert example_txt_res is not None
    bytes_bin_res = next(
        (r for r in resources if r["uri"] == "bytes:///test.bin"), None
    )
    assert bytes_bin_res is not None
    print("test_process_mcp_resources_list PASSED")


async def test_process_mcp_resources_read_text_success():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    uri_to_test = "file:///example.txt"
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": uri_to_test},
        "id": "res-read-text-1",
    }
    resp = await server_core.process_message_dict(req)
    # ... (rest of read text assertions)
    assert resp["id"] == "res-read-text-1"
    assert "result" in resp, f"Response was: {resp}"
    assert "contents" in resp["result"]
    assert len(resp["result"]["contents"]) == 1
    content_resp = resp["result"]["contents"][0]
    assert content_resp["uri"] == uri_to_test
    assert content_resp["text"] == "Common test content for file:///example.txt"
    assert content_resp["mimeType"] == "text/plain"
    print("test_process_mcp_resources_read_text_success PASSED")


async def test_process_mcp_resources_read_binary_success():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    uri_to_test = "bytes:///test.bin"
    import ubinascii

    expected_base64_blob = ubinascii.b2a_base64(b"binary_data").decode("utf-8").strip()
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": uri_to_test},
        "id": "res-read-bin-1",
    }
    resp = await server_core.process_message_dict(req)
    # ... (rest of read binary assertions)
    assert resp["id"] == "res-read-bin-1"
    assert "result" in resp, f"Response was: {resp}"
    assert "contents" in resp["result"]
    assert len(resp["result"]["contents"]) == 1
    content_resp = resp["result"]["contents"][0]
    assert content_resp["uri"] == uri_to_test
    assert content_resp["blob"] == expected_base64_blob
    assert content_resp["mimeType"] == "application/octet-stream"
    print("test_process_mcp_resources_read_binary_success PASSED")


async def test_process_mcp_resources_read_missing_uri():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {},
        "id": "res-read-err-1",
    }
    resp = await server_core.process_message_dict(req)
    # ... (rest of missing URI assertions)
    assert resp["id"] == "res-read-err-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32602
    assert "Missing 'uri' parameter" in resp["error"]["data"]
    print("test_process_mcp_resources_read_missing_uri PASSED")


async def test_process_mcp_resources_read_uri_not_found_in_registry():  # Renamed for clarity
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "file:///non_existent.txt"},
        "id": "res-read-err-2",
    }
    resp = await server_core.process_message_dict(req)
    # ... (rest of URI not found assertions)
    assert resp["id"] == "res-read-err-2"
    assert "error" in resp
    assert resp["error"]["code"] == -32001
    assert (
        "Resource with URI 'file:///non_existent.txt' not found"
        in resp["error"]["data"]
    )
    print("test_process_mcp_resources_read_uri_not_found_in_registry PASSED")


# --- New/Refactored Subscription Tests (Spec Compliant) ---
async def test_resources_subscribe_success_known_uri():
    tool_reg, res_reg, prompt_reg = (
        setup_test_registry(),
        setup_common_resource_registry(),
        setup_common_prompt_registry(),
    )
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/subscribe",
        "params": {"uri": "file:///example.txt"},
        "id": "sub-known-1",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "sub-known-1", "ID mismatch"
    assert "result" in resp, f"Expected success, got error: {resp.get('error')}"
    assert resp["result"] == {}, "Expected empty result object for successful subscribe"
    print("test_resources_subscribe_success_known_uri PASSED")


async def test_resources_subscribe_fail_unknown_uri():
    tool_reg, res_reg, prompt_reg = (
        setup_test_registry(),
        setup_common_resource_registry(),
        setup_common_prompt_registry(),
    )
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/subscribe",
        "params": {"uri": "file:///unknown.txt"},
        "id": "sub-unknown-1",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "sub-unknown-1", "ID mismatch"
    assert "error" in resp, "Expected error for unknown URI subscribe"
    assert (
        resp["error"]["code"] == -32001
    ), "Error code mismatch for unknown URI"  # Resource not found
    assert "not found in registry" in resp["error"]["data"], "Error data mismatch"
    print("test_resources_subscribe_fail_unknown_uri PASSED")


async def test_resources_subscribe_missing_uri_param():
    tool_reg, res_reg, prompt_reg = (
        setup_test_registry(),
        setup_common_resource_registry(),
        setup_common_prompt_registry(),
    )
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/subscribe",
        "params": {},
        "id": "sub-no-uri-1",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "sub-no-uri-1", "ID mismatch"
    assert "error" in resp, "Expected error for missing URI"
    assert resp["error"]["code"] == -32602, "Error code for invalid params"
    assert "Missing or invalid 'uri' parameter" in resp["error"]["data"]
    print("test_resources_subscribe_missing_uri_param PASSED")


async def test_resources_subscribe_invalid_uri_type():
    tool_reg, res_reg, prompt_reg = (
        setup_test_registry(),
        setup_common_resource_registry(),
        setup_common_prompt_registry(),
    )
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/subscribe",
        "params": {"uri": 123},
        "id": "sub-badtype-uri-1",
    }  # URI is not a string
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "sub-badtype-uri-1", "ID mismatch"
    assert "error" in resp, "Expected error for invalid URI type"
    assert resp["error"]["code"] == -32602, "Error code for invalid params"
    assert "Missing or invalid 'uri' parameter" in resp["error"]["data"]
    print("test_resources_subscribe_invalid_uri_type PASSED")


async def test_resources_unsubscribe_success():  # Unsubscribe always succeeds by acknowledgment
    tool_reg, res_reg, prompt_reg = (
        setup_test_registry(),
        setup_common_resource_registry(),
        setup_common_prompt_registry(),
    )
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/unsubscribe",
        "params": {"uri": "file:///example.txt"},
        "id": "unsub-any-1",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "unsub-any-1", "ID mismatch"
    assert "result" in resp, f"Expected success, got error: {resp.get('error')}"
    assert (
        resp["result"] == {}
    ), "Expected empty result object for successful unsubscribe"
    print("test_resources_unsubscribe_success PASSED")


async def test_resources_unsubscribe_missing_uri_param():
    tool_reg, res_reg, prompt_reg = (
        setup_test_registry(),
        setup_common_resource_registry(),
        setup_common_prompt_registry(),
    )
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)
    req = {
        "jsonrpc": "2.0",
        "method": "resources/unsubscribe",
        "params": {},
        "id": "unsub-no-uri-1",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "unsub-no-uri-1", "ID mismatch"
    assert "error" in resp, "Expected error for missing URI in unsubscribe"
    assert resp["error"]["code"] == -32602, "Error code for invalid params"
    assert "Missing or invalid 'uri' parameter" in resp["error"]["data"]
    print("test_resources_unsubscribe_missing_uri_param PASSED")


# --- End New/Refactored Subscription Tests ---


async def run_resource_handler_tests():
    print("\n--- Running MCP Handler Tests (Resources) ---")
    await test_process_mcp_resources_list()
    await test_process_mcp_resources_read_text_success()
    await test_process_mcp_resources_read_binary_success()
    await test_process_mcp_resources_read_missing_uri()
    await test_process_mcp_resources_read_uri_not_found_in_registry()  # Was ...unsupported_scheme...
    # Add new subscription tests to the runner
    await test_resources_subscribe_success_known_uri()
    await test_resources_subscribe_fail_unknown_uri()
    await test_resources_subscribe_missing_uri_param()
    await test_resources_subscribe_invalid_uri_type()
    await test_resources_unsubscribe_success()
    await test_resources_unsubscribe_missing_uri_param()
    print("--- MCP Handler Tests (Resources) Complete ---")


if __name__ == "__main__":
    asyncio.run(run_resource_handler_tests())
