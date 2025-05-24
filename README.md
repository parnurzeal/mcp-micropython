# MicroPython Model Context Protocol (MCP) Server SDK

This project provides a lightweight SDK for building Model Context Protocol (MCP) servers in a MicroPython environment. It allows developers to expose custom functionalities (tools) that can be discovered and called by MCP clients, such as AI models or other applications.

The implementation focuses on the core MCP methods for tool handling (`initialize`, `tools/list`, `tools/call`) and uses a `stdio` (standard input/output) transport layer.

## Prerequisites

- A MicroPython environment (e.g., on a microcontroller like ESP32, Raspberry Pi Pico, or the Unix port of MicroPython).
- The `uasyncio` library for asynchronous operations.
- The `ujson` library for JSON parsing and serialization.

These libraries are typically built into standard MicroPython firmware.

## Project Structure

```
.
├── mcp/                    # Core MCP server SDK files
│   ├── __init__.py
│   ├── registry.py         # ToolRegistry class for managing tools
│   ├── stdio_server.py     # Main stdio server logic and MCP method handlers
│   └── types.py            # JSON-RPC response helpers
├── tests/                  # Unit tests
│   └── test_mcp_server.py  # Tests for registry and server logic
├── main.py                 # Example application: defines and runs a server
└── README.md               # This file
```

## Developer Guide

This guide explains how to create your own MCP server with custom tools using this SDK. The primary file you'll modify or use as a template is `main.py`.

### Important Note on Output Streams

**Crucial for MCP Communication:** When developing your MicroPython MCP server, it is essential that all `print()` statements used for logging, debugging, or any other informational output are directed to `sys.stderr`. The standard output stream (`sys.stdout`) is exclusively used for the JSON-RPC 2.0 messages that form the communication channel with the MCP client.

Any extraneous output (e.g., from `print("debug message")`) sent to `sys.stdout` will corrupt the JSON-RPC message stream, leading to parsing errors on the client side and a breakdown in communication.

**How to do it:**

1.  Import the `sys` module: `import sys`
2.  Use the `file=sys.stderr` argument in your print statements: `print("Your debug message", file=sys.stderr)`

This practice ensures that your server's diagnostic messages do not interfere with the protocol. The `mcp/stdio_server.py` and example `main.py` already follow this convention for their internal logging.

### 1. Define Tool Handler Functions

Tool handlers are asynchronous Python functions that implement the logic for your tools.

- Each handler function should be defined with `async def`.
- Parameters passed from the MCP client (in the `arguments` field of a `tools/call` request) will be passed to your handler function as keyword arguments if `arguments` is a JSON object, or as positional arguments if `arguments` is a JSON array and `param_names` were specified during registration.
- If a tool takes no arguments, define the handler with no parameters (e.g., `async def my_tool():`).
- The function should return a JSON-serializable value, which will be the `result` of the `tools/call` operation.
- If an error occurs within the handler, it can raise an exception. This will be caught and translated into a JSON-RPC error response.

**Example Tool Handlers (from `main.py`):**

```python
# In your main application file (e.g., main.py)

async def example_echo_tool(message: str):
    """Echoes back the input message."""
    return f"Echo: {message}"

async def example_add_tool(a, b):
    """Adds two numbers."""
    try:
        num_a = float(a)
        num_b = float(b)
        return num_a + num_b
    except ValueError:
        raise ValueError("Invalid number input for 'add' tool.")

async def example_info_tool():
    """Returns a static piece of information."""
    return "This is a MicroPython MCP server, version 0.1.0."
```

### 2. Create and Populate a `ToolRegistry`

The `ToolRegistry` (from `mcp.registry`) is used to manage your tool definitions and their handlers.

- Import `ToolRegistry`: `from mcp.registry import ToolRegistry`
- Create an instance: `registry = ToolRegistry()`
- Register each tool using `registry.register_tool()`:
  - `name` (str): The unique name of the tool (e.g., "echo", "get_weather").
  - `description` (str): A human-readable description of what the tool does.
  - `input_schema` (dict or None): A dictionary describing the tool's input parameters. This dictionary represents the `properties` field of a JSON Schema object.
    - For each parameter, provide a key (parameter name) and a value (e.g., `{"type": "string", "description": "..."}`).
    - If the tool takes no arguments, pass `None` or an empty dictionary `{}`.
  - `handler_func` (async function): A reference to the asynchronous function that implements this tool.
  - `param_names` (list of str, optional): If the MCP client might send arguments as a JSON array, provide a list of parameter names in the order they appear in the array. These will be mapped to keyword arguments for your handler.

**Example Registry Setup (from `main.py`):**

```python
# In your main application file

from mcp.registry import ToolRegistry
# ... (import your tool handlers) ...

def setup_my_tools():
    registry = ToolRegistry()

    registry.register_tool(
        name="echo",
        description="Echoes back the provided message.",
        input_schema={"message": {"type": "string", "description": "The message to be echoed"}},
        handler_func=example_echo_tool
    )

    registry.register_tool(
        name="add",
        description="Adds two numbers provided as 'a' and 'b'.",
        input_schema={
            "a": {"type": "number", "description": "The first number."},
            "b": {"type": "number", "description": "The second number."}
        },
        handler_func=example_add_tool,
        param_names=["a", "b"] # If arguments might come as a list [val_a, val_b]
    )

    registry.register_tool(
        name="info",
        description="Provides static information about the server.",
        input_schema=None, # No arguments
        handler_func=example_info_tool
    )
    return registry
```

### 3. Start the MCP Server

- Import the `stdio_server` function: `from mcp.stdio_server import stdio_server`
- Import `uasyncio`.
- In an `async def main_server_loop():` function (or similar):
  1. Call your function to set up the `ToolRegistry` (e.g., `my_registry = setup_my_tools()`).
  2. `await stdio_server(tool_registry=my_registry)` to start the server.
- Use `uasyncio.run(main_server_loop())` to run the event loop.

**Example Server Start (from `main.py`):**

```python
# In your main application file

import uasyncio
from mcp.stdio_server import stdio_server
# ... (import ToolRegistry and setup_my_tools) ...

async def main_server_loop():
    print("Starting MCP MicroPython Stdio Server...")
    my_registry = setup_my_tools()
    await stdio_server(tool_registry=my_registry)
    print("MCP MicroPython Stdio Server finished.")

if __name__ == "__main__":
    try:
        uasyncio.run(main_server_loop())
    except KeyboardInterrupt:
        print("Main application interrupted by user. Exiting.")
    # ... (other exception handling) ...
```

### 4. Running Your Server

- Ensure all files (`mcp/` directory, your `main.py`) are on your MicroPython device or accessible to your MicroPython Unix port.
- Run your main application file: `micropython main.py`
- The server will start and wait for JSON-RPC 2.0 messages on stdin. Responses will be sent to stdout.

## Running Unit Tests

The project includes a test suite in `tests/test_mcp_server.py`.
To run the tests:

1. Ensure the `mcp/` directory and `tests/` directory are structured correctly.
2. From the project root directory, run: `micropython tests/test_mcp_server.py`
3. The tests will print "PASSED" for each successful test case or a traceback for failures.

## MCP Compliance Notes

- **JSON-RPC 2.0:** The server aims for JSON-RPC 2.0 compliance for request/response structure and error objects. Notifications (requests without an `id`) are processed but do not elicit a response.
- **`initialize` Method:** Responds with `serverName`, `serverVersion`, `specificationVersion` ("2025-03-26"), and basic `capabilities` for tools.
- **`tools/list` Method:**
  - Returns a list of tool definitions.
  - Each tool's `inputSchema` will be `null` if it takes no arguments.
  - If it has arguments, `inputSchema` will be a basic JSON Schema object: `{"type": "object", "properties": <your_schema_props_dict>}`.
  - Full JSON Schema features (like `required` fields) are not automatically generated from the simplified `input_schema` provided during registration but could be manually constructed by the developer if needed for the `properties` dictionary.
- **`tools/call` Method:**
  - Expects `params` to contain `name` (string) and `arguments` (object, list, or null).
  - Argument validation against the `inputSchema` is **not** automatically performed by the SDK before calling the tool handler. **Tool handler functions are responsible for their own argument validation.** This is a simplification for the MicroPython environment.
- **Error Codes:** Standard JSON-RPC error codes are used where applicable (e.g., -32700 Parse Error, -32600 Invalid Request, -32601 Method Not Found, -32602 Invalid Params). A server-specific code (-32000) is used for tool execution errors.

This SDK provides a foundational layer for building MCP-compliant servers on MicroPython, with deliberate simplifications to suit resource-constrained environments.
