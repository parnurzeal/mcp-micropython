# MicroPython Model Context Protocol (MCP) Server SDK

This project provides a lightweight SDK for building Model Context Protocol (MCP) servers in a MicroPython environment. It allows developers to expose custom functionalities (tools), share data (resources), and define prompt templates that can be discovered and utilized by MCP clients, such as AI models or other applications.

The implementation focuses on core MCP methods for handling tools (`initialize`, `tools/list`, `tools/call`), resources (`resources/list`, `resources/read`), and prompts (`prompts/list`, `prompts/get`), using a `stdio` (standard input/output) transport layer.

## Prerequisites

- A MicroPython environment (e.g., on a microcontroller like ESP32, Raspberry Pi Pico, or the Unix port of MicroPython).
- An asyncio library (typically `uasyncio`, often available as `asyncio`).
- A JSON library (typically `ujson`, available by importing `json`).
- The `ubinascii` library for base64 encoding (used for binary resources).

These libraries are typically built into standard MicroPython firmware.

For Bluetooth functionality (using `mcp/bluetooth_server.py` and its tests):

- The **`bluetooth` module** must be available in your MicroPython firmware/build. This is a core C module and usually cannot be installed via `mip`. If your `micropython` host executable (e.g., Unix port) reports `ImportError: no module named 'bluetooth'`, it means that specific build of MicroPython does not include Bluetooth support. You would need to use a MicroPython build that has it (e.g., firmware for a BLE-capable board like Pico W, or a Unix port compiled with Bluetooth support).
- The **`aioble` library** is required. This library depends on the `bluetooth` module.
  - **For IoT Devices (e.g., Pico W, ESP32):** Connect to your device and run `mpremote mip install aioble` in your computer's terminal.
  - **For Host `micropython` (e.g., Unix port):** If `aioble` is not found after ensuring `bluetooth` is present, you may need to install it. This typically involves ensuring `aioble` is in MicroPython's search path (e.g., `~/.micropython/lib` for the Unix port, or a path in `MICROPYPATH`). If `mip` is available in your host `micropython` (it might need to be installed separately for the Unix port, e.g., `micropython -m upip install micropython-mip`), you can then try `import mip; mip.install("aioble")` from the MicroPython REPL or by running `micropython -m mip install aioble`.

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

  Alternatively, download the `microdot` library (specifically the `microdot` folder from its `src` directory on GitHub: [https://github.com/miguelgrinberg/microdot/tree/main/src/microdot](https://github.com/miguelgrinberg/microdot/tree/main/src/microdot)). You would then copy this downloaded `microdot` folder to your device.

### Deploying to a Microcontroller

To use this MCP SDK on a MicroPython microcontroller:

1.  **Core MCP SDK (`mcp/` directory)**: This is the `mcp` folder from this project.
2.  **Microdot Library**: If using the Wi-Fi server (`mcp/wifi_server.py`), ensure the `microdot` library is on your device. You can install it via `mip` (see above) or by manually copying it.
3.  **Your Main Application File**: This is your primary script that initializes and runs the MCP server (e.g., `main.py` if it's configured to start the Wi-Fi server, or a script like `main-pico.py`).

**Recommended Placement on Device:**

- Copy the `mcp/` SDK directory and (if using the Wi-Fi server and not installing `microdot` via `mip`) the `microdot/` library directory directly to the root (`/`) of your MicroPython device's filesystem.
- Place your main application script (e.g., `main.py`) also in the root directory (`/`).

MicroPython's `sys.path` includes the root directory, so modules placed here will be importable. While using a `/lib` folder is also common, placing directly in root can be simpler for smaller projects or direct deployments.

**Example File Transfer using `mpremote`:**

`mpremote` is a versatile command-line tool for interacting with MicroPython devices.

```bash
# 0. List connected devices to find your port (optional, if not using default)
# mpremote connect list

# 1. Copy the mcp SDK (the 'mcp' folder from this project) to /mcp on the device
#    Run this command from the root of this SDK project directory.
mpremote fs cp -r mcp :mcp

# 2. Install Microdot (if using the Wi-Fi server and not using mip):
#    a. Download the Microdot library. Extract it. You should have a 'microdot' folder
#       (this folder is inside Microdot's 'src' directory on GitHub).
#    b. Navigate your computer's terminal to the directory *containing* your downloaded 'microdot' folder.
#    c. Copy the 'microdot' folder to the root of the device:
mpremote fs cp -r microdot :microdot
#       (This creates /microdot on the device and copies contents into it.)

# 3. Copy your main application script to the device's root.
#    If your script that starts the wifi_mcp_server is named, for example, 'my_wifi_app.py':
mpremote cp my_wifi_app.py :main.py
#    (Renaming to main.py makes it run on boot for many boards. Or use its original name.)
```

(The `:` in `mpremote ... :<path>` indicates the remote device path. Adjust device connection specifics if needed, e.g., `mpremote connect /dev/ttyUSB0 <command>`)

- **Using Thonny IDE:** You can use Thonny's file browser to upload the `mcp` folder (from this project) and the `microdot` folder (which you would have downloaded separately) directly to the root of your MicroPython device's filesystem. Then upload your main application script to the root.

### Example: Running the Wi-Fi Server

Your main application script (e.g., `main.py` or `main-pico.py` if adapted) will need to:

1. Import `wifi_mcp_server` from `mcp.wifi_server`.
2. Import and set up your tool, resource, and prompt registries.
3. Call `uasyncio.run(wifi_mcp_server(...))` with your Wi-Fi credentials and registries.
   Refer to the example structure in `main-pico.py` (though it might need slight adaptation based on your final setup). You'll need to provide your Wi-Fi SSID and password.

## Using the Bluetooth LE Server (with NUS)

This SDK also includes a Bluetooth Low Energy (BLE) based MCP server (`mcp/bluetooth_server.py`) that uses the Nordic UART Service (NUS) for communication. This is suitable for devices with BLE capabilities (e.g., ESP32, Pico W).

### Dependencies for Bluetooth LE Server

- All prerequisites for the stdio server (MicroPython, `uasyncio`, `ujson`, `ubinascii`).
- The **`ubluetooth` module**, which is a standard part of MicroPython firmware on devices that support Bluetooth. No external libraries are typically needed for basic BLE NUS functionality.

### Deploying to a Microcontroller (for BLE Server)

To use the Bluetooth MCP server on a MicroPython microcontroller:

1.  **Core MCP SDK (`mcp/` directory)**: This is the `mcp` folder from this project.
2.  **Your Main Application File**: This is your primary script that initializes and runs the MCP server using the Bluetooth transport (e.g., `main_ble.py`).

**Recommended Placement on Device:**

- Copy the `mcp/` SDK directory directly to the root (`/`) of your MicroPython device's filesystem.
- Place your main application script (e.g., `main_ble.py`) also in the root directory (`/`).

**Example File Transfer using `mpremote`:**

```bash
# 1. Copy the mcp SDK (the 'mcp' folder from this project) to /mcp on the device
#    Run this command from the root of this SDK project directory.
mpremote fs cp -r mcp :mcp

# 2. Copy your main BLE application script to the device's root.
#    If your script is named 'main_ble.py':
mpremote cp main_ble.py :main.py
#    (Renaming to main.py makes it run on boot for many boards. Or use its original name.)
```

- **Using Thonny IDE:** You can use Thonny's file browser to upload the `mcp` folder (from this project) and your `main_ble.py` script directly to the root of your MicroPython device's filesystem.

### Example: Running the Bluetooth LE Server

Your main application script (e.g., `main_ble.py`) will need to:

1. Import `bluetooth_mcp_server` from `mcp.bluetooth_server`.
2. Import and set up your tool, resource, and prompt registries.
3. Call `uasyncio.run(bluetooth_mcp_server(...))` with your `ServerCore` instance and an optional device name for advertising.
   Refer to the example structure in `main_ble.py`.

## Running Unit Tests

The project includes a test suite in the `tests/` directory. The `run_all_tests.py` script is designed to be executed **exclusively** with a `micropython` interpreter (e.g., `micropython run_all_tests.py`).

**Test Environment Notes:**

- **Execution:** The script uses MicroPython's native `uasyncio` (as `asyncio`). All tests run in the native MicroPython environment.
- **Bluetooth Tests (`tests/test_bluetooth_server.py`):**
  - These tests require a MicroPython environment with functional `bluetooth` and `aioble` modules.
  - `run_all_tests.py` will automatically skip these tests if `bluetooth` or `aioble` cannot be imported, printing an informational message. This is common if the `micropython` host executable (e.g., Unix port) was not built with Bluetooth support.
  - To run these tests, ensure your MicroPython environment (device firmware or host build) includes the `bluetooth` module, and that `aioble` is installed (e.g., via `mpremote mip install aioble` for devices, or available in the `MICROPYPATH` for host builds).
- **Wi-Fi Tests (`tests/test_wifi_server.py`):**
  - These tests also require a MicroPython environment with a functional `network` module and the `microdot` library installed.
  - `run_all_tests.py` will automatically skip these tests if `network` or `microdot` cannot be imported.
  - The Wi-Fi connection specific tests within `test_wifi_server.py` (e.g., `test_wifi_connection_success_and_server_start_attempt`) will attempt real network operations. For these to pass, the MicroPython environment must have Wi-Fi hardware and the placeholder `TEST_SSID` and `TEST_PASSWORD` in `tests/test_wifi_server.py` should be updated to valid local Wi-Fi credentials. Otherwise, these specific connection tests will likely fail.
  - The HTTP request handling parts of the Wi-Fi tests (using `TestClient`) should run against a local Microdot instance and should pass if `microdot` is installed, even if a real Wi-Fi connection isn't established by the connection tests.

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
