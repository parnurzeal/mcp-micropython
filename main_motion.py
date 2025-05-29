import asyncio
import dc
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
        name="move_forward",
        description="Move the robot forward by a fixed distance.",
        input_schema={},
        handler_func=dc.forward,
    )
    registry.register_tool(
        name="move_backward",
        description="Move the robot backward by a fixed distance.",
        input_schema={
        },
        handler_func=dc.backward,
    )
    registry.register_tool(
        name="turn_left",
        description="Turn the robot left by a fixed angle.",
        input_schema={},
        handler_func=dc.turn_left,
    )
    registry.register_tool(
        name="turn_right",
        description="Turn the robot right by a fixed angle.",
        input_schema={},
        handler_func=dc.turn_right,
    )
    return registry

def start_motion():
    try:
        asyncio.run(run_loop(tool_registry=setup_registry()))
    except KeyboardInterrupt:
        print("Main application interrupted by user. Exiting.", file=sys.stderr)
    except Exception as e:
        print(
            f"An unexpected error occurred in main: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
