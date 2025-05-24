# tests/test_resource_handlers.py
import sys
import uasyncio
import ujson
import os

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.server_core import ServerCore  # Import ServerCore
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
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)  # Instantiate ServerCore

    req = {"jsonrpc": "2.0", "method": "resources/list", "id": "res-list-1"}
    resp = await server_core.process_message_dict(req)  # Call method on instance

    assert resp["id"] == "res-list-1"
    assert "result" in resp
    assert "resources" in resp["result"]
    resources = resp["result"]["resources"]
    assert len(resources) == 2

    example_txt_res = next(
        (r for r in resources if r["uri"] == "file:///example.txt"), None
    )
    assert example_txt_res is not None
    assert example_txt_res["name"] == "Common Test Example File"
    bytes_bin_res = next(
        (r for r in resources if r["uri"] == "bytes:///test.bin"), None
    )
    assert bytes_bin_res is not None
    assert bytes_bin_res["name"] == "Common Test Binary File"
    print("test_process_mcp_resources_list PASSED")


async def test_process_mcp_resources_read_text_success():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    uri_to_test = "file:///example.txt"
    expected_content_text = "Common test content for file:///example.txt"
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": uri_to_test},
        "id": "res-read-text-1",
    }
    resp = await server_core.process_message_dict(req)

    assert resp["id"] == "res-read-text-1"
    assert "result" in resp, f"Response was: {resp}"
    assert "contents" in resp["result"]
    assert len(resp["result"]["contents"]) == 1
    content_resp = resp["result"]["contents"][0]
    assert content_resp["uri"] == uri_to_test
    assert content_resp["text"] == expected_content_text
    assert content_resp["mimeType"] == "text/plain"
    print("test_process_mcp_resources_read_text_success PASSED")


async def test_process_mcp_resources_read_binary_success():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    uri_to_test = "bytes:///test.bin"
    expected_blob_content = b"binary_data"
    import ubinascii

    expected_base64_blob = (
        ubinascii.b2a_base64(expected_blob_content).decode("utf-8").strip()
    )
    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": uri_to_test},
        "id": "res-read-bin-1",
    }
    resp = await server_core.process_message_dict(req)

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
    assert resp["id"] == "res-read-err-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32602
    assert "Missing 'uri' parameter" in resp["error"]["data"]
    print("test_process_mcp_resources_read_missing_uri PASSED")


async def test_process_mcp_resources_read_unsupported_scheme_if_not_registered():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "http://example.com/unsupported.txt"},
        "id": "res-read-err-2",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "res-read-err-2"
    assert "error" in resp
    assert resp["error"]["code"] == -32001
    assert (
        "Resource with URI 'http://example.com/unsupported.txt' not found"
        in resp["error"]["data"]
    )
    print("test_process_mcp_resources_read_unsupported_scheme_if_not_registered PASSED")


async def test_process_mcp_resources_read_uri_not_found_in_registry():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    server_core = ServerCore(tool_reg, res_reg, prompt_reg)

    req = {
        "jsonrpc": "2.0",
        "method": "resources/read",
        "params": {"uri": "file:///non_existent_file_for_sure.txt"},
        "id": "res-read-err-3",
    }
    resp = await server_core.process_message_dict(req)
    assert resp["id"] == "res-read-err-3"
    assert "error" in resp
    assert resp["error"]["code"] == -32001
    assert (
        "Resource with URI 'file:///non_existent_file_for_sure.txt' not found"
        in resp["error"]["data"]
    )
    print("test_process_mcp_resources_read_uri_not_found_in_registry PASSED")


async def run_resource_handler_tests():
    print("\n--- Running MCP Handler Tests (Resources) ---")
    await test_process_mcp_resources_list()
    await test_process_mcp_resources_read_text_success()
    await test_process_mcp_resources_read_binary_success()
    await test_process_mcp_resources_read_missing_uri()
    await test_process_mcp_resources_read_unsupported_scheme_if_not_registered()
    await test_process_mcp_resources_read_uri_not_found_in_registry()
    print("--- MCP Handler Tests (Resources) Complete ---")


if __name__ == "__main__":
    uasyncio.run(run_resource_handler_tests())
