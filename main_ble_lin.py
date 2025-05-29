# main_ble.py
# Example script to run the Bluetooth MCP Server

import asyncio
from mcp.server_core import ServerCore
from mcp.bluetooth_server import bluetooth_mcp_server
from mcp.registry import ToolRegistry, ResourceRegistry, PromptRegistry
from config import BLUETOOTH_NAME

# --- Define Example Tools, Resources, Prompts ---


# Example Tool: echo
async def echo_tool(params):
    """Returns the provided message."""
    message = params.get("message", "No message provided.")
    return {"status": "success", "echo": message}


echo_tool_def = {
    "name": "echo",
    "description": "Echoes back the provided message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "The message to echo."}
        },
        "required": ["message"],
    },
    "output_schema": {
        "type": "object",
        "properties": {"status": {"type": "string"}, "echo": {"type": "string"}},
    },
}


# Example Resource: device_info
async def get_device_info_content(params):
    """Returns basic device information."""
    # In a real scenario, this would query actual device info
    return "Device: MockPico\nFirmware: MCP-BLE-v0.1"


device_info_def = {
    "uri": "mcp://device/info",
    "description": "Provides basic information about the device.",
    "methods": ["read"],
    "handler": get_device_info_content,
    "schema": None,  # No specific schema for read params in this example
}


# Example Prompt: confirm_action
async def confirm_action_prompt_handler(params):
    """
    A mock prompt handler. In a real BLE scenario, prompts are tricky
    as there's no direct console. This might log or require a specific
    client interaction pattern not covered by basic NUS.
    For this example, it just returns a canned response.
    """
    action = params.get("action", "do something")
    # Simulating an automatic confirmation for testing
    return {"confirmed": True, "action": action}


confirm_action_prompt_def = {
    "name": "confirm_action",
    "description": "Asks the user to confirm an action (mocked for BLE).",
    "input_schema": {
        "type": "object",
        "properties": {"action": {"type": "string"}},
        "required": ["action"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "confirmed": {"type": "boolean"},
            "action": {"type": "string"},
        },
    },
    "handler": confirm_action_prompt_handler,
}


def main(
    tool_registry: ToolRegistry,
    resource_registry: ResourceRegistry,
    prompt_registry: PromptRegistry,
):
    print("Initializing Bluetooth MCP Server...")
    # 1. Create ServerCore
    server_core = ServerCore(
        tool_registry=tool_registry,
        resource_registry=resource_registry,
        prompt_registry=prompt_registry,
    )

    # 2. Start the Bluetooth MCP Server
    print(f"Starting Bluetooth server, advertising as '{BLUETOOTH_NAME}'...")
    try:
        asyncio.run(bluetooth_mcp_server(server_core, device_name=BLUETOOTH_NAME))
    except KeyboardInterrupt:
        print("Bluetooth server stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Bluetooth MCP Server shutdown complete.")

if __name__ == "__main__":
    print("Starting BluetoothMCP Server directly (for testing)...")

    # Create a mock ServerCore for direct testing
    mock_tool_registry = ToolRegistry()
    mock_resource_registry = ResourceRegistry()
    mock_prompt_registry = PromptRegistry()
    mock_core = ServerCore(
        mock_tool_registry, mock_resource_registry, mock_prompt_registry
    )

    async def mock_echo_tool(message: str):
        return f"Echo: {message}"

    mock_tool_registry.register_tool(
        name="echo",
        description="Echoes a message",
        input_schema={"message": {"type": "string", "description": "Message to echo"}},
        handler_func=mock_echo_tool,
    )

    try:
        asyncio.run(bluetooth_mcp_server(mock_core, device_name="PicoMCPDirect"))
    except KeyboardInterrupt:
        print("MainApp: Interrupted by user.")
    except Exception as e:
        print(f"MainApp: Error - {type(e).__name__}: {e}")
    finally:
        print("MainApp: Finished.")
