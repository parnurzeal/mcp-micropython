# tests/test_prompt_handlers.py
import sys
import uasyncio
import ujson

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.stdio_server import process_mcp_message
from tests.common_test_utils import setup_common_prompt_registry

# --- Prompt Handler Tests (via process_mcp_message) ---


async def test_process_mcp_prompts_list():
    prompt_reg = setup_common_prompt_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/list",
        "id": "p-list-1",
    }  # Define req here
    # process_mcp_message expects (message, tool_registry, resource_registry, prompt_registry)
    resp = await process_mcp_message(req, None, None, prompt_reg)

    assert resp["id"] == "p-list-1"
    assert "result" in resp
    assert "prompts" in resp["result"]
    prompts_list = resp["result"]["prompts"]
    assert len(prompts_list) == 1
    prompt = prompts_list[0]
    assert prompt["name"] == "common_example_prompt"
    assert prompt["description"] == "A common prompt for testing."
    assert len(prompt["arguments"]) == 1
    assert prompt["arguments"][0]["name"] == "topic"
    print("test_process_mcp_prompts_list PASSED")


async def test_process_mcp_prompts_get_success():
    prompt_reg = setup_common_prompt_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {
            "name": "common_example_prompt",
            "arguments": {"topic": "MicroPython Test"},
        },
        "id": "p-get-1",
    }
    resp = await process_mcp_message(req, None, None, prompt_reg)

    assert resp["id"] == "p-get-1"
    assert "result" in resp
    assert resp["result"]["description"] == "Common test prompt: MicroPython Test"
    assert "messages" in resp["result"]
    assert len(resp["result"]["messages"]) == 1
    message = resp["result"]["messages"][0]
    assert message["role"] == "user"
    assert message["content"]["type"] == "text"
    assert message["content"]["text"] == "Common test prompt about MicroPython Test"
    print("test_process_mcp_prompts_get_success PASSED")


async def test_process_mcp_prompts_get_default_topic():
    prompt_reg = setup_common_prompt_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "common_example_prompt"},
        "id": "p-get-2",
    }
    resp = await process_mcp_message(req, None, None, prompt_reg)

    assert resp["id"] == "p-get-2"
    assert "result" in resp
    assert resp["result"]["description"] == "Common test prompt: default test topic"
    assert "messages" in resp["result"]
    assert len(resp["result"]["messages"]) == 1
    message = resp["result"]["messages"][0]
    assert message["content"]["text"] == "Common test prompt about default test topic"
    print("test_process_mcp_prompts_get_default_topic PASSED")


async def test_process_mcp_prompts_get_not_found_in_registry():
    prompt_reg = setup_common_prompt_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {"name": "non_existent_prompt"},
        "id": "p-get-err-1",
    }
    resp = await process_mcp_message(req, None, None, prompt_reg)

    assert resp["id"] == "p-get-err-1"
    assert "error" in resp
    assert resp["error"]["code"] == -32001
    assert "Prompt 'non_existent_prompt' not found" in resp["error"]["data"]
    print("test_process_mcp_prompts_get_not_found_in_registry PASSED")


async def test_process_mcp_prompts_get_missing_name_param():
    prompt_reg = setup_common_prompt_registry()
    req = {
        "jsonrpc": "2.0",
        "method": "prompts/get",
        "params": {},
        "id": "p-get-err-2",
    }
    resp = await process_mcp_message(req, None, None, prompt_reg)
    assert resp["id"] == "p-get-err-2"
    assert "error" in resp
    assert resp["error"]["code"] == -32602
    assert "Missing 'name' parameter for prompt." in resp["error"]["data"]
    print("test_process_mcp_prompts_get_missing_name_param PASSED")


async def run_prompt_handler_tests():
    print("\n--- Running MCP Handler Tests (Prompts) ---")
    await test_process_mcp_prompts_list()
    await test_process_mcp_prompts_get_success()
    await test_process_mcp_prompts_get_default_topic()
    await test_process_mcp_prompts_get_not_found_in_registry()
    await test_process_mcp_prompts_get_missing_name_param()
    print("--- MCP Handler Tests (Prompts) Complete ---")


if __name__ == "__main__":
    uasyncio.run(run_prompt_handler_tests())
