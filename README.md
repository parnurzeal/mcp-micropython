# MicroPython Model Context Protocol (MCP) Server SDK

This project provides a lightweight SDK for building Model Context Protocol (MCP) servers in a MicroPython environment. It allows developers to expose custom functionalities (tools), share data (resources), and define prompt templates that can be discovered and utilized by MCP clients, such as AI models or other applications.

The implementation focuses on core MCP methods for handling tools (`initialize`, `tools/list`, `tools/call`), resources (`resources/list`, `resources/read`), and prompts (`prompts/list`, `prompts/get`), using a `stdio` (standard input/output) transport layer.

## Prerequisites

- A MicroPython environment (e.g., on a microcontroller like ESP32, Raspberry Pi Pico, or the Unix port of MicroPython).
- The `uasyncio` library for asynchronous operations.
- The `ujson` library for JSON parsing and serialization.
- The `ubinascii` library for base64 encoding (used for binary resources).

These libraries are typically built into standard MicroPython firmware.

## Project Structure

```
.
├── mcp/                    # Core MCP server SDK files
│   ├── __init__.py
│   ├── registry.py         # ToolRegistry, ResourceRegistry, PromptRegistry classes
│   ├── stdio_server.py     # Main stdio server logic and MCP method handlers
│   └── types.py            # JSON-RPC response helpers
├── tests/                  # Unit tests
│   ├── common_test_utils.py
│   ├── test_tool_registry.py
│   ├── test_tool_handlers.py
│   ├── test_resource_handlers.py
│   ├── test_prompt_handlers.py
│   └── test_stdio_transport.py
├── main.py                 # Example application: defines and runs a server
├── run_all_tests.py        # Script to execute all unit tests
└── README.md               # This file
```

## Developer Guide

This guide explains how to create your own MCP server with custom tools, resources, and prompts using this SDK. The primary file you'll modify or use as a template is `main.py`.

### Important Note on Output Streams

**Crucial for MCP Communication:** All `print()` statements used for logging or debugging must be directed to `sys.stderr`. The standard output stream (`sys.stdout`) is exclusively used for JSON-RPC 2.0 messages.
Example: `import sys; print("Debug message", file=sys.stderr)`

### 1. Define Handlers

Handlers are asynchronous Python functions that implement the logic for your tools, resources, and prompts.

#### Tool Handlers

- Define with `async def`.
- Parameters from `tools/call` requests are passed as keyword or positional arguments.
- Return a JSON-serializable value.
- Raise exceptions for errors.

**Example Tool Handlers (from `main.py`):**

```python
async def example_echo_tool(message: str):
    return f"Echo: {message}"

async def example_add_tool(a, b):
    return float(a) + float(b)
```

#### Resource Read Handlers

- Define with `async def your_resource_read_handler(uri: str):`.
- The `uri` argument is the URI of the resource being requested.
- Should return the content of the resource, either as a `str` (for text-based resources) or `bytes` (for binary resources).
- Raise `ResourceError` (from `mcp.registry`) or other exceptions for errors.

**Example Resource Read Handler (from `main.py`):**

```python
async def example_read_hardcoded_resource(uri: str):
    if uri == "file:///example.txt":
        return "This is the dynamically registered, hardcoded content..."
    raise ValueError(f"Handler called with unexpected URI: {uri}")
```

#### Prompt Get Handlers

- Define with `async def your_prompt_get_handler(name: str, arguments: dict):`.
- `name` is the name of the prompt requested.
- `arguments` is a dictionary of arguments provided by the client.
- Should return a dictionary matching the `GetPromptResult` schema, typically `{"messages": [...], "description": "optional resolved description"}`.
- Raise `PromptError` (from `mcp.registry`) or other exceptions for errors.

**Example Prompt Get Handler (from `main.py`):**

```python
async def example_get_prompt_handler(name: str, arguments: dict):
    if name == "example_prompt":
        topic = arguments.get("topic", "a default topic")
        messages = [{"role": "user", "content": {"type": "text", "text": f"Tell me more about {topic}."}}]
        return {"description": f"A dynamically generated prompt about {topic}", "messages": messages}
    raise ValueError(f"Unknown prompt name: {name}")
```

### 2. Create and Populate Registries

Registries manage your server's capabilities.

- Import `ToolRegistry`, `ResourceRegistry`, `PromptRegistry` from `mcp.registry`.

#### `ToolRegistry`

- `registry.register_tool(name, description, input_schema, handler_func, param_names=None)`

**Example ToolRegistry Setup (from `main.py`):**

```python
def setup_my_tools():
    registry = ToolRegistry()
    registry.register_tool(
        name="echo",
        description="Echoes back the provided message.",
        input_schema={"message": {"type": "string", "description": "The message to be echoed"}},
        handler_func=example_echo_tool
    )
    # ... more tools ...
    return registry
```

#### `ResourceRegistry`

- `registry.register_resource(uri, name, read_handler, description=None, mime_type="text/plain")`

**Example ResourceRegistry Setup (from `main.py`):**

```python
def setup_my_resources():
    resource_registry = ResourceRegistry()
    resource_registry.register_resource(
        uri="file:///example.txt",
        name="Registered Example File",
        description="A sample resource with a hardcoded read handler.",
        mime_type="text/plain",
        read_handler=example_read_hardcoded_resource
    )
    return resource_registry
```

#### `PromptRegistry`

- `registry.register_prompt(name, description, arguments_schema, get_handler)`
  - `arguments_schema`: List of argument definition objects (e.g., `[{"name": "topic", "description": "...", "required": True}]`).

**Example PromptRegistry Setup (from `main.py`):**

```python
def setup_my_prompts():
    prompt_registry = PromptRegistry()
    prompt_registry.register_prompt(
        name="example_prompt",
        description="A sample prompt that can discuss a topic.",
        arguments_schema=[{"name": "topic", "description": "The topic for the prompt", "required": True}],
        get_handler=example_get_prompt_handler
    )
    return prompt_registry
```

### 3. Start the MCP Server

- Import `stdio_server` from `mcp.stdio_server`.
- In an `async def main_server_loop():`
  1. Create and populate all three registries.
  2. `await stdio_server(tool_registry=my_tool_reg, resource_registry=my_res_reg, prompt_registry=my_prompt_reg)`

**Example Server Start (from `main.py`):**

```python
async def main_server_loop():
    print("Starting MCP MicroPython Stdio Server...", file=sys.stderr)
    my_tool_registry = setup_my_tools()
    my_resource_registry = setup_my_resources()
    my_prompt_registry = setup_my_prompts()

    await stdio_server(
        tool_registry=my_tool_registry,
        resource_registry=my_resource_registry,
        prompt_registry=my_prompt_registry
    )
    print("MCP MicroPython Stdio Server finished.", file=sys.stderr)

if __name__ == "__main__":
    uasyncio.run(main_server_loop())
```

### 4. Running Your Server

- Ensure all files are on your MicroPython device or accessible to your MicroPython Unix port.
- Run: `micropython main.py`

## Using the Wi-Fi Server (with Microdot)

This SDK also includes a Wi-Fi based MCP server (`mcp/wifi_server.py`) that uses the Microdot web framework. This is suitable for devices with network capabilities (e.g., ESP32, Pico W).

### Dependencies for Wi-Fi Server

- All prerequisites for the stdio server.
- The **`microdot` library**. This is an external dependency that you need to install separately onto your MicroPython device if you intend to use the Wi-Fi server (`mcp/wifi_server.py`).

  **Installing `microdot`:**
  You can install `microdot` using `mip` (MicroPython Package Manager) directly on your device if it has network connectivity, or by downloading it and copying it manually.

  ```bash
  # Example using mip (run in MicroPython REPL)
  import mip
  mip.install("github:miguelgrinberg/microdot/src/microdot")
  # Or, for a specific module if the above doesn't work for the package structure:
  # mip.install("github:miguelgrinberg/microdot/src/microdot/microdot.py")
  # mip.install("github:miguelgrinberg/microdot/src/microdot/request.py")
  # ...and other necessary files from Microdot's src/microdot directory.
  # It's often easier to download the 'microdot' folder from its GitHub 'src'
  # and copy it to your device's /lib directory.
  ```

  Alternatively, download the `microdot` library (specifically the `microdot` folder from its `src` directory on GitHub: [https://github.com/miguelgrinberg/microdot/tree/main/src/microdot](https://github.com/miguelgrinberg/microdot/tree/main/src/microdot)) and copy this `microdot` folder to the `/lib` directory on your MicroPython device. For example, if you downloaded it to `~/Downloads/microdot_src/microdot`:

  ```bash
  # Example for manually downloaded microdot (after navigating to where microdot_src is)
  mpremote cp -r microdot :lib/microdot
  ```

### Deploying to a Microcontroller

To use this MCP SDK on a MicroPython microcontroller:

1.  **Core MCP SDK (`mcp/` directory)**: Copy the entire `mcp/` directory from this project to your device.
2.  **Microdot Library**: If using the Wi-Fi server, ensure `microdot` is installed on your device as described above.
3.  **Your Main Application File**: This will be your script (e.g., like `main.py` or `main-pico.py` from this project) where you define tools, resources, prompts, and start the chosen server.

**Recommended Placement on Device:**

- Place library code (like the `mcp` SDK and the separately installed `microdot` library) into the `/lib` directory on your device.
- Place your main application script (e.g., `main.py`) in the root directory (`/`) of your device.

**Recommended Placement:**

- Place library code (like the `mcp` SDK and `microdot`) into the `/lib` directory on your device.
- Place your main application script (e.g., `main.py`) in the root directory (`/`) of your device.

**Example File Transfer Methods:**

You can use tools like `mpremote` (part of MicroPython) or Thonny IDE.

- **Using `mpremote` (Recommended for `/lib`):**
  Assuming your device is connected and `mpremote` is installed:

  ```bash
  # List connected devices to find your port (e.g., /dev/ttyACM0, /dev/ttyUSB0, COM3)
  # mpremote connect list

  # Create /lib directory on the device if it doesn't exist
  # Replace <device_shortcut> with your device, e.g., mpremote connect /dev/ttyACM0 mkdir /lib
  # Or, if you have a default connection: mpremote mkdir /lib
  mpremote mkdir /lib

  # Copy the mcp SDK to /lib/mcp on the device
  mpremote cp -r mcp :lib/mcp

  # Ensure Microdot is in /lib/microdot (either via mip or manual copy as shown above)

  # Copy your main application file (e.g., main-pico.py) to the device's root,
  # naming it main.py if you want it to run automatically on boot.
  mpremote cp main-pico.py :main.py
  ```

  (The `:` in `mpremote cp` commands indicates the remote device path. Adjust device connection specifics as needed.)

- **Using Thonny IDE:** You can use Thonny's file browser ("This computer" and "MicroPython device" panes) to navigate and transfer the `mcp` folder to your MicroPython device (typically into `/lib`). Ensure `microdot` is also installed, usually into `/lib` as well.

### Example: Running the Wi-Fi Server

Refer to `main-pico.py` for an example of how to set up and run the `wifi_mcp_server`. You'll need to provide your Wi-Fi SSID and password.

## Running Unit Tests

The project includes a test suite in the `tests/` directory. A master script `run_all_tests.py` is provided to execute all tests.

1. Ensure the `mcp/` directory and `tests/` directory are structured correctly.
2. From the project root directory, run: `micropython run_all_tests.py`
3. The tests will print "PASSED" for each successful test case or a traceback for failures.

## MCP Compliance Notes

- **JSON-RPC 2.0:** Adheres to JSON-RPC 2.0 structure.
- **`initialize` Method:** Responds with `serverInfo`, `protocolVersion` ("2025-03-26"), and `capabilities` for tools, resources, and prompts (if their respective registries are provided and populated).
- **`tools/list` Method:** Returns tool definitions. `inputSchema` is `{"type": "object", "properties": {}}` for no-argument tools.
- **`tools/call` Method:** Tool execution errors are reported within a `CallToolResult` object with `isError: true`.
- **`resources/list` Method:** Returns resource definitions.
- **`resources/read` Method:** Returns `ResourceContents`. Binary content is base64 encoded in the `blob` field.
- **`resources/subscribe` & `resources/unsubscribe` Methods:** The server includes handlers for these methods which acknowledge requests as per the MCP specification (single `uri` parameter, empty `result` object on success). However, the server currently advertises `capabilities.resources.subscribe: false` because it does **not** yet implement stateful tracking of subscriptions or send `notifications/resources/updated` messages. The full subscription flow is not yet functional.
- **`prompts/list` Method:** Returns prompt definitions.
- **`prompts/get` Method:** Returns `GetPromptResult` (messages and optional description).
- **Argument Validation:** Tool, resource, and prompt handlers are responsible for their own argument validation.

This SDK provides a foundational layer for building MCP-compliant servers on MicroPython.
