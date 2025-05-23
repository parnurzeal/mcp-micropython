import uasyncio
import sys
from mcp.stdio_server import stdio_server
from mcp.registry import (
    ToolRegistry,
    ResourceRegistry,
    PromptRegistry,
)  # Import PromptRegistry


# --- Tool Handler Examples ---
async def example_echo_tool(message: str):
    return f"Echo: {message}"


async def example_add_tool(a, b):
    try:
        return float(a) + float(b)
    except ValueError:
        raise ValueError("Invalid number input for 'add' tool.")


async def example_info_tool():
    return "This is a MicroPython MCP server, version 0.1.0."


# --- Registry Setup ---
def setup_my_tools():
    registry = ToolRegistry()
    registry.register_tool(
        name="echo",
        description="Echoes back the provided message.",
        input_schema={
            "message": {"type": "string", "description": "The message to be echoed"}
        },
        handler_func=example_echo_tool,
    )
    registry.register_tool(
        name="add",
        description="Adds two numbers provided as 'a' and 'b'.",
        input_schema={
            "a": {"type": "number", "description": "The first number."},
            "b": {"type": "number", "description": "The second number."},
        },
        handler_func=example_add_tool,
    )
    registry.register_tool(
        name="info",
        description="Provides static information about the server.",
        input_schema={},
        handler_func=example_info_tool,
    )
    return registry


# --- Resource Handler and Registry Setup ---
async def example_read_hardcoded_resource(uri: str):
    if uri == "file:///example.txt":
        return "This is the dynamically registered, hardcoded content for file:///example.txt from main.py!"
    else:
        raise ValueError(
            f"example_read_hardcoded_resource called with unexpected URI: {uri}"
        )


def setup_my_resources():
    resource_registry = ResourceRegistry()
    resource_registry.register_resource(
        uri="file:///example.txt",
        name="Registered Example File",
        description="A sample resource registered dynamically with a hardcoded read handler.",
        mime_type="text/plain",
        read_handler=example_read_hardcoded_resource,
    )
    return resource_registry


# --- Prompt Handler and Registry Setup ---
async def example_get_prompt_handler(name: str, arguments: dict):
    """
    Handles 'prompts/get' for the 'example_prompt'.
    Returns a dict suitable for GetPromptResult.
    """
    if name == "example_prompt":
        topic = arguments.get("topic", "a default topic")
        messages = [
            {
                "role": "user",
                "content": {"type": "text", "text": f"Tell me more about {topic}."},
            }
        ]
        return {
            "description": f"A dynamically generated prompt about {topic}",
            "messages": messages,
        }
    raise ValueError(f"Unknown prompt name: {name}")


def setup_my_prompts():
    """
    Creates a PromptRegistry and registers custom prompts.
    """
    prompt_registry = PromptRegistry()
    prompt_registry.register_prompt(
        name="example_prompt",
        description="A sample prompt that can discuss a topic.",
        arguments_schema=[
            {
                "name": "topic",
                "description": "The topic for the prompt",
                "required": True,
            }
        ],
        get_handler=example_get_prompt_handler,
    )
    return prompt_registry


async def main_server_loop():
    print("Starting MCP MicroPython Stdio Server from main.py...", file=sys.stderr)

    my_tool_registry = setup_my_tools()
    my_resource_registry = setup_my_resources()
    my_prompt_registry = setup_my_prompts()  # Create prompt registry

    await stdio_server(
        tool_registry=my_tool_registry,
        resource_registry=my_resource_registry,
        prompt_registry=my_prompt_registry,  # Pass prompt registry
    )

    print("MCP MicroPython Stdio Server finished in main.py.", file=sys.stderr)


if __name__ == "__main__":
    try:
        uasyncio.run(main_server_loop())
    except KeyboardInterrupt:
        print("Main application interrupted by user. Exiting.", file=sys.stderr)
    except Exception as e:
        print(
            f"An unexpected error occurred in main: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
