import uasyncio
import sys  # Import sys for stderr
from mcp.stdio_server import stdio_server  # Import the server function directly
from mcp.registry import ToolRegistry, ResourceRegistry  # Import ResourceRegistry

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


# --- Resource Handler and Registry Setup ---
async def example_read_hardcoded_resource(uri: str):
    """Returns hardcoded content for a specific URI."""
    # This handler is specific to "file:///example.txt" as registered below.
    # A more generic file handler would parse the path from the URI and read the actual file.
    if uri == "file:///example.txt":  # Check for the specific URI it's registered for
        content_to_return = "This is the dynamically registered, hardcoded content for file:///example.txt from main.py!"
        return content_to_return
    else:
        # Should not happen if registry calls correctly, but as a fallback:
        error_message = (
            f"example_read_hardcoded_resource called with unexpected URI: {uri}"
        )
        raise ValueError(error_message)


def setup_my_resources():
    """
    Creates a ResourceRegistry and registers custom resources.
    """
    resource_registry = ResourceRegistry()

    resource_registry.register_resource(
        uri="file:///example.txt",  # The URI the client will request
        name="Registered Example File",
        description="A sample resource registered dynamically with a hardcoded read handler.",
        mime_type="text/plain",
        read_handler=example_read_hardcoded_resource,
    )

    # Example of registering a resource that reads an actual file (if desired later)
    # async def read_actual_file_content(uri: str):
    #     file_path = uri[7:] # Naive stripping of "file:///"
    #     # Add proper path joining and security for real use
    #     # For MicroPython, ensure file exists and handle errors
    #     try:
    #         with open(file_path, "r") as f:
    #             return f.read()
    #     except Exception as e:
    #         print(f"Error reading actual file {file_path}: {e}", file=sys.stderr)
    #         raise # Re-raise to be caught by handle_resources_read
    #
    # resource_registry.register_resource(
    #     uri="file:///actual_test_file.txt",
    #     name="Actual Test File",
    #     description="Reads content from actual_test_file.txt in CWD.",
    #     mime_type="text/plain",
    #     read_handler=read_actual_file_content
    # )

    return resource_registry


async def main_server_loop():
    # IMPORTANT: All print statements in this server application, especially those
    # that are not part of the MCP JSON-RPC communication itself (e.g., debug logs,
    # status messages), should be directed to sys.stderr.
    # Printing to sys.stdout can interfere with the JSON-RPC messages expected by
    # the client, as stdout is used for the primary communication channel.
    print("Starting MCP MicroPython Stdio Server from main.py...", file=sys.stderr)

    # 1. Create and populate the tool registry
    my_tool_registry = setup_my_tools()

    # 2. Create and populate the resource registry
    my_resource_registry = setup_my_resources()

    # 3. Pass both registries to the server
    await stdio_server(
        tool_registry=my_tool_registry, resource_registry=my_resource_registry
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
