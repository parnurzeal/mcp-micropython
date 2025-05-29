import sys

from config import *
from mcp.server_core import ServerCore
from mcp.stdio_server import stdio_server
from mcp.bluetooth_server import bluetooth_mcp_server
from mcp.wifi_server import wifi_mcp_server
from mcp.registry import (
    ToolRegistry,
    ResourceRegistry,
    PromptRegistry,
)  # Import PromptRegistry

async def run_loop(
    tool_registry: ToolRegistry,
    resource_registry: ResourceRegistry = ResourceRegistry(),
    prompt_registry: PromptRegistry = PromptRegistry(),
):

    if SERVER_TYPE == WIFI:
        print("Starting MCP MicroPython Wi-Fi Server from main.py...", file=sys.stderr)
        if WIFI_SSID == "YOUR_WIFI_SSID" or WIFI_PASSWORD == "YOUR_WIFI_PASSWORD":
            print(
                "ERROR: Please update WIFI_SSID and WIFI_PASSWORD in main.py to run the Wi-Fi server.",
                file=sys.stderr,
            )
            return

        await wifi_mcp_server(
            tool_registry=tool_registry,
            resource_registry=resource_registry,
            prompt_registry=prompt_registry,
            wifi_ssid=WIFI_SSID,
            wifi_password=WIFI_PASSWORD,
            mcp_port=MCP_SERVER_PORT,
            # server_name and server_version can also be passed to wifi_mcp_server
        )
        print("MCP MicroPython Wi-Fi Server finished in main.py.", file=sys.stderr)
    if SERVER_TYPE == STDIO:
        print("Starting MCP MicroPython Stdio Server from main.py...", file=sys.stderr)
        await stdio_server(
            tool_registry=tool_registry,
            resource_registry=resource_registry,
            prompt_registry=prompt_registry,
        )
        print("MCP MicroPython Stdio Server finished in main.py.", file=sys.stderr)
    if SERVER_TYPE == BULETOOTH:
        server_core = ServerCore(
            tool_registry=tool_registry,
            resource_registry=resource_registry,
            prompt_registry=prompt_registry,
        )
        await bluetooth_mcp_server(server_core=server_core, device_name=BLUETOOTH_NAME)