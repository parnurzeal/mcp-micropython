# tests/test_prompt_handlers.py
import sys
import uasyncio
import ujson

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.stdio_server import process_mcp_message
from tests.common_test_utils import (
    setup_test_registry,
)  # For consistency, though not used by prompt handlers yet

# --- Prompt Handler Tests (via process_mcp_message) ---


async def test_process_mcp_prompts_list():
    registry = setup_test_registry()  # registry is not used by current prompt handlers
    req = {"jsonrpc": "2.0", "method": "prompts/list", "id": "p-list-1"}
    resp = await process_mcp_message(req, registry)

    assert resp["id"] == "p-list-1"
    assert "result" in resp
    assert "prompts" in resp["result"]
    assert len(resp["result"]["prompts"]) == 1
    prompt = resp["result"]["prompts"][0]
    assert prompt["name"] == "example_prompt"
    assert prompt["description"] == "An example prompt template."
    assert len(prompt["arguments"]) == 1
    assert prompt["arguments"][0]["name"] == "topic"
    print("test_process_mcp_prompts_list PASSED")


async def test_process_mcp_prompts_get_success():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "example_prompt", "arguments": {"topic": "MicroPython"}},
        "id": "p-get-1",
    }
    resp = await process_mcp_message(req, registry)

    assert resp["id"] == "p-get-1"
    assert "result" in resp
    assert resp["result"]["description"] == "A prompt about MicroPython"
    assert "messages" in resp["result"]
    assert len(resp["result"]["messages"]) == 1
    message = resp["result"]["messages"][0]
    assert message["role"] == "user"
    assert message["content"]["type"] == "text"
    assert message["content"]["text"] == "Tell me about MicroPython."
    print("test_process_mcp_prompts_get_success PASSED")


async def test_process_mcp_prompts_get_default_topic():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "example_prompt"},  # No arguments provided
        "id": "p-get-2",
    }
    resp = await process_mcp_message(req, registry)

    assert resp["id"] == "p-get-2"
    assert "result" in resp
    assert resp["result"]["description"] == "A prompt about a default topic"
    assert "messages" in resp["result"]
    assert len(resp["result"]["messages"]) == 1
    message = resp["result"]["messages"][0]
    assert message["content"]["text"] == "Tell me about a default topic."
    print("test_process_mcp_prompts_get_default_topic PASSED")


async def test_process_mcp_prompts_get_not_found():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "non_existent_prompt"},
        "id": "p-get-err-1",
    }
    resp = await process_mcp_message(req, registry)

    assert resp["id"] == "p-get-err-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32001  # Prompt Not Found
    assert "Prompt 'non_existent_prompt' not found" in resp["error"]["data"]
    print("test_process_mcp_prompts_get_not_found PASSED")


async def test_process_mcp_prompts_get_missing_name():
    registry = setup_test_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {},  # Missing name
        "id": "p-get-err-2",
    }
    resp = await process_mcp_message(req, registry)
    assert resp["id"] == "p-get-err-2"
    assert "error" in resp
    assert resp["error"]["code"] == -32602  # Invalid Params
    assert "Missing 'name' parameter for prompt." in resp["error"]["data"]
    print("test_process_mcp_prompts_get_missing_name PASSED")


async def run_prompt_handler_tests():
    print("\n--- Running MCP Handler Tests (Prompts) ---")
    await test_process_mcp_prompts_list()
    await test_process_mcp_prompts_get_success()
    await test_process_mcp_prompts_get_default_topic()
    await test_process_mcp_prompts_get_not_found()
    await test_process_mcp_prompts_get_missing_name()
    print("--- MCP Handler Tests (Prompts) Complete ---")


if __name__ == "__main__":
    uasyncio.run(run_prompt_handler_tests())
