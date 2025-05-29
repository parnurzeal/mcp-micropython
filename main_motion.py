import asyncio
import sys
from main_server_loop import run_loop

# Import both server types
from mcp.registry import ToolRegistry


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
def setup_registry():
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

if __name__ == "__main__":
    try:
        asyncio.run(run_loop(tool_registry=setup_registry()))
    except KeyboardInterrupt:
        print("Main application interrupted by user. Exiting.", file=sys.stderr)
    except Exception as e:
        print(
            f"An unexpected error occurred in main: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
