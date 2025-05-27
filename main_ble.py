# main_ble.py
# Example script to run the Bluetooth MCP Server

import asyncio
from mcp.server_core import ServerCore
from mcp.bluetooth_server import bluetooth_mcp_server
from mcp.registry import ToolRegistry, ResourceRegistry, PromptRegistry

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


async def main():
    print("Initializing Bluetooth MCP Server...")

    # 1. Initialize Registries
    tool_registry = ToolRegistry()
    resource_registry = ResourceRegistry()
    prompt_registry = PromptRegistry()

    # 2. Register Tools, Resources, Prompts
    tool_registry.register_tool(
        name=echo_tool_def["name"],
        description=echo_tool_def["description"],
        input_schema=echo_tool_def["input_schema"][
            "properties"
        ],  # Pass the properties dict
        handler_func=echo_tool,
    )
    print(f"Registered tool: {echo_tool_def['name']}")

    resource_registry.register_resource(
        uri=device_info_def["uri"],
        name=device_info_def[
            "uri"
        ],  # Using URI as name for simplicity, or add a 'name' field to def
        read_handler=device_info_def["handler"],
        description=device_info_def["description"],
        # mime_type can be added if defined in device_info_def
    )
    print(f"Registered resource: {device_info_def['uri']}")

    # For prompt arguments_schema, it expects a list of argument definitions.
    # Let's construct it from the input_schema's properties.
    prompt_args_list = []
    if "properties" in confirm_action_prompt_def["input_schema"]:
        for arg_name, arg_def in confirm_action_prompt_def["input_schema"][
            "properties"
        ].items():
            prompt_args_list.append(
                {
                    "name": arg_name,
                    "description": arg_def.get("description", ""),
                    "type": arg_def.get(
                        "type", "string"
                    ),  # Default to string if not specified
                    "required": arg_name
                    in confirm_action_prompt_def["input_schema"].get("required", []),
                }
            )

    prompt_registry.register_prompt(
        name=confirm_action_prompt_def["name"],
        description=confirm_action_prompt_def["description"],
        arguments_schema=prompt_args_list,
        get_handler=confirm_action_prompt_def["handler"],
    )
    print(f"Registered prompt: {confirm_action_prompt_def['name']}")

    # 3. Create ServerCore
    server_core = ServerCore(
        tool_registry=tool_registry,
        resource_registry=resource_registry,
        prompt_registry=prompt_registry,
    )

    # 4. Start the Bluetooth MCP Server
    device_name = "PicoMCP-NUS"
    print(f"Starting Bluetooth server, advertising as '{device_name}'...")
    try:
        await bluetooth_mcp_server(server_core, device_name=device_name)
    except KeyboardInterrupt:
        print("Bluetooth server stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Bluetooth MCP Server shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Main program interrupted.")
    except Exception as e:
        print(f"Unhandled exception in main: {e}")
        # Consider adding sys.print_exception(e) if on MicroPython for more details
