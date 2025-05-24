import uasyncio
import sys  # Import sys for stderr
from mcp.stdio_server import stdio_server  # Import the server function directly
from mcp.registry import ToolRegistry  # Import the ToolRegistry

# --- Tool Handler Examples ---
# These are the functions that will actually do the work for each tool.
# They should be asynchronous.


async def example_echo_tool(message: str):
    """Echoes back the input message."""
    # In a real tool, you might have more complex logic.
    # The 'message' argument comes from the 'arguments' field of the tool/call request.
    return f"Echo: {message}"


async def example_add_tool(a, b):
    """Adds two numbers."""
    try:
        num_a = float(a)
        num_b = float(b)
        return num_a + num_b
    except ValueError:
        # It's often better for tools to raise specific errors or return error structures
        # that can be translated into JSON-RPC errors by the caller if needed.
        # For now, this will be caught by the tool_call handler in stdio_server.
        raise ValueError("Invalid number input for 'add' tool.")


async def example_info_tool():
    """Returns a static piece of information."""
    return "This is a MicroPython MCP server, version 0.1.0."


# --- Registry Setup ---
def setup_my_tools():
    """
    Creates a ToolRegistry and registers custom tools.
    This is where a developer defines their server's capabilities.
    """
    registry = ToolRegistry()

    # Register the 'echo' tool
    registry.register_tool(
        name="echo",
        description="Echoes back the provided message.",
        # inputSchema defines what 'arguments' should look like for tool/call.
        # For simplicity, using a dict where keys are param names and values are descriptions or type info.
        # A full JSON schema is more robust but complex for MicroPython.
        input_schema={
            "message": {"type": "string", "description": "The message to be echoed"}
        },
        handler_func=example_echo_tool,
        # param_names=["message"] # Use if your handler expects positional args from a list
    )

    # Register the 'add' tool
    registry.register_tool(
        name="add",
        description="Adds two numbers provided as 'a' and 'b'.",
        input_schema={
            "a": {"type": "number", "description": "The first number."},
            "b": {"type": "number", "description": "The second number."},
        },
        handler_func=example_add_tool,
        # param_names=["a", "b"] # If handler expects positional args from a list
    )

    # Register a tool with no parameters
    registry.register_tool(
        name="info",
        description="Provides static information about the server.",
        input_schema={},  # Empty schema for no arguments
        handler_func=example_info_tool,
    )

    # Add more tool registrations here
    # registry.register_tool(...)

    return registry


async def main_server_loop():
    # IMPORTANT: All print statements in this server application, especially those
    # that are not part of the MCP JSON-RPC communication itself (e.g., debug logs,
    # status messages), should be directed to sys.stderr.
    # Printing to sys.stdout can interfere with the JSON-RPC messages expected by
    # the client, as stdout is used for the primary communication channel.
    print("Starting MCP MicroPython Stdio Server from main.py...", file=sys.stderr)

    # 1. Create and populate the tool registry
    my_registry = setup_my_tools()

    # 2. Pass the registry to the server
    await stdio_server(tool_registry=my_registry)

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
