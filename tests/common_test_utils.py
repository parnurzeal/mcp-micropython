# tests/common_test_utils.py
import sys

# Ensure the project root is in the path if this file is run directly for some reason,
# or if other test files import from it and their own path setup isn't sufficient.
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.registry import (
    ToolRegistry,
    ResourceRegistry,
    ResourceError,
)  # Moved ResourceRegistry and ResourceError import here


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


# --- Common Resource Registry Setup ---
# (This is minimal for now as resource handlers are simple in stdio_server.py)
# If main.py registers specific resource handlers, this might need to mirror that.
# ResourceRegistry and ResourceError are already imported at the top.


async def example_common_read_handler(uri: str):
    # A generic handler for tests, can be more specific if needed
    if uri == "file:///example.txt":
        return "Common test content for file:///example.txt"
    elif uri == "bytes:///test.bin":
        return b"binary_data"
    raise ResourceError(f"Common test handler does not support URI: {uri}")


def setup_common_resource_registry():
    res_registry = ResourceRegistry()
    res_registry.register_resource(
        uri="file:///example.txt",
        name="Common Test Example File",
        description="A common resource for testing.",
        mime_type="text/plain",
        read_handler=example_common_read_handler,
    )
    res_registry.register_resource(
        uri="bytes:///test.bin",
        name="Common Test Binary File",
        description="A common binary resource for testing.",
        mime_type="application/octet-stream",
        read_handler=example_common_read_handler,
    )
    return res_registry


# --- Common Prompt Registry Setup ---
from mcp.registry import (
    PromptRegistry,
    PromptError,
)  # Already imported PromptError if ResourceError was


async def example_common_get_prompt_handler(name: str, arguments: dict):
    if name == "common_example_prompt":
        topic = arguments.get("topic", "default test topic")
        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Common test prompt about {topic}",
                },
            }
        ]
        return {"description": f"Common test prompt: {topic}", "messages": messages}
    raise PromptError(f"Common test prompt handler does not support prompt: {name}")


def setup_common_prompt_registry():
    prompt_reg = PromptRegistry()
    prompt_reg.register_prompt(
        name="common_example_prompt",
        description="A common prompt for testing.",
        arguments_schema=[
            {"name": "topic", "description": "Test topic", "required": False}
        ],
        get_handler=example_common_get_prompt_handler,
    )
    return prompt_reg
