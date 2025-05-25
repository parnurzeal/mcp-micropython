# mcp/wifi_server.py
import sys
import uasyncio
import ujson  # Still useful for creating specific error dicts if needed
import network

# import socket # No longer needed directly for server logic
from . import types
from .server_core import ServerCore

try:
    # Attempt to import directly from the microdot module
    # The microdot.py module itself should handle asyncio if available
    from microdot import Microdot, Response
except ImportError:
    print("Microdot library not found. Please install it.", file=sys.stderr)
    # Fallback or error handling if Microdot is essential
    # For now, we'll let it raise an error if not found at runtime
    # This allows the rest of the file to be parsed.
    Microdot = None
    Response = None


# Default Wi-Fi connection timeout
WIFI_CONNECT_TIMEOUT_S = 15
# Default MCP server port
DEFAULT_MCP_PORT = 8080

# _handle_client_connection is removed as Microdot handles connections.


async def wifi_mcp_server(
    tool_registry,
    resource_registry,
    prompt_registry,
    wifi_ssid: str,
    wifi_password: str,
    mcp_port: int = DEFAULT_MCP_PORT,
    server_name: str = "MicroPython MCP Wi-Fi Server",  # For initialize response
    server_version: str = "0.1.0",  # For initialize response
):
    if Microdot is None or Response is None:
        print("Microdot library not loaded. Cannot start server.", file=sys.stderr)
        return

    if not all(
        [tool_registry, resource_registry, prompt_registry, wifi_ssid, wifi_password]
    ):
        print(
            "Fatal Error: wifi_mcp_server requires registries, Wi-Fi SSID, and password.",
            file=sys.stderr,
        )
        return

    # --- Wi-Fi Connection ---
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(f"Attempting to connect to Wi-Fi SSID: {wifi_ssid}", file=sys.stderr)
    wlan.connect(wifi_ssid, wifi_password)

    max_wait = WIFI_CONNECT_TIMEOUT_S
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:  # Success or permanent failure
            break
        max_wait -= 1
        print("Waiting for Wi-Fi connection...", file=sys.stderr)
        await uasyncio.sleep(1)

    if wlan.status() != 3:  # network.STAT_GOT_IP
        print(f"Wi-Fi connection failed. Status: {wlan.status()}", file=sys.stderr)
        return

    pico_ip_address = wlan.ifconfig()[0]
    print(f"Connected to Wi-Fi. Pico IP: {pico_ip_address}", file=sys.stderr)

    # --- MCP Server Setup ---
    server_core_instance = ServerCore(tool_registry, resource_registry, prompt_registry)
    # Note: server_name and server_version are not used by Microdot directly,
    # but ServerCore might use them if it's adapted for initialize responses.

    app = create_mcp_microdot_app(server_core_instance)

    print(
        f"Starting MCP Wi-Fi Server (Microdot) on {pico_ip_address}:{mcp_port}",
        file=sys.stderr,
    )
    # server_task = None # server_task is not used later with app.start_server() like this
    try:
        # Start the Microdot server.
        # The start_server coroutine completes when the server is shut down.
        await app.start_server(host="0.0.0.0", port=mcp_port, debug=False)
        # No `while True: await uasyncio.sleep(60)` loop is needed.
        # The server runs until KeyboardInterrupt or other exception stops it.
        # So, no `while True: await uasyncio.sleep(60)` loop is needed.
        # The server runs until KeyboardInterrupt or other exception stops it.

    except KeyboardInterrupt:
        print("MCP Wi-Fi Server interrupted. Shutting down.", file=sys.stderr)
        if hasattr(app, "shutdown") and callable(app.shutdown):
            app.shutdown()  # Gracefully shutdown Microdot server
    except uasyncio.CancelledError:
        print("MCP Wi-Fi Server task cancelled.", file=sys.stderr)
        if hasattr(app, "shutdown") and callable(app.shutdown):
            app.shutdown()
    except Exception as e:
        print(
            f"Fatal error in MCP Wi-Fi Server (Microdot): {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        if hasattr(app, "shutdown") and callable(app.shutdown):
            app.shutdown()
    finally:
        # Microdot's start_server cleans up itself on exit/cancellation.
        # If server_task was a uasyncio.Task, we might await/cancel it here.
        # But since start_server is awaited directly, its completion means shutdown.
        print("MCP Wi-Fi Server (Microdot) stopped.", file=sys.stderr)

    # Note on server_name, server_version:
    # These are not directly used by Microdot. If ServerCore's initialize method
    # needs them, ServerCore would need to be initialized or configured with them.
    # For example, server_core_instance = ServerCore(..., server_info={"name": server_name, "version": server_version})
    # And ServerCore._handle_initialize would use this server_info.


def create_mcp_microdot_app(server_core_instance: ServerCore):
    """
    Creates and configures a Microdot application for the MCP server.
    """
    if Microdot is None or Response is None:
        # This case should ideally be handled before calling this function,
        # but as a safeguard:
        raise RuntimeError("Microdot library not loaded.")

    app = Microdot()

    @app.route("/", methods=["POST"])
    async def handle_mcp_request(request):
        client_ip_tuple = request.client_addr
        client_ip = (
            f"{client_ip_tuple[0]}:{client_ip_tuple[1]}"
            if client_ip_tuple
            else "Unknown Client"
        )
        # Limiting verbose logging for tests, can be re-enabled if needed
        # print(f"MCP Request from {client_ip} to {request.path}", file=sys.stderr)

        message_dict = None
        current_req_id = None
        response_data = None

        try:
            if (
                request.content_type
                and "application/json" in request.content_type.lower()
            ):
                message_dict = request.json
                if message_dict is None:
                    response_data = types.create_error_response(
                        None, -32700, "Parse Error", "Invalid or empty JSON received."
                    )
                    # For TestClient, returning a dict directly is often easier.
                    # The actual server needs a Response object.
                    # This creates a slight divergence but simplifies TestClient interaction.
                    # Alternatively, the mock Response factory needs to be perfect.
                    return response_data, 400  # Return tuple (body, status_code)
            else:
                response_data = types.create_error_response(
                    None,
                    -32600,
                    "Invalid Request",
                    "Content-Type must be application/json.",
                )
                return response_data, 415  # Return tuple

            # print(f"Received JSON from {client_ip}: {message_dict}", file=sys.stderr)

            is_notification = "id" not in message_dict
            current_req_id = message_dict.get("id")

            if "method" not in message_dict or "jsonrpc" not in message_dict:
                if not is_notification:
                    response_data = types.create_error_response(
                        current_req_id,
                        -32600,
                        "Invalid Request",
                        "The JSON sent is not a valid Request object.",
                    )
            else:
                if is_notification:
                    await server_core_instance.process_message_dict(message_dict)
                    # print(f"Processed notification from {client_ip} (method: {message_dict.get('method')})", file=sys.stderr)
                    return "", 204  # Return empty body, status 204 for notifications
                else:
                    response_data = await server_core_instance.process_message_dict(
                        message_dict
                    )
                    if response_data is None:
                        # print(f"Error: ServerCore returned None for a non-notification request from {client_ip}.", file=sys.stderr)
                        response_data = types.create_error_response(
                            current_req_id,
                            -32603,
                            "Internal Server Error",
                            "ServerCore returned no response for request.",
                        )

            if response_data:
                # print(f"Sending response to {client_ip}: {response_data}", file=sys.stderr)
                return response_data  # Return dict, TestClient will handle it (status 200 default)
            elif is_notification:  # Should have already returned 204
                return "", 204
            else:  # Should not be reached
                # print(f"Warning: Unhandled case for request from {client_ip}, sending generic error.", file=sys.stderr)
                response_data = types.create_error_response(
                    current_req_id,
                    -32603,
                    "Internal Server Error",
                    "Unhandled server state.",
                )
                return response_data, 500

        except Exception as e:
            # print(f"Error handling request from {client_ip}: {type(e).__name__}: {e}", file=sys.stderr)
            error_response_payload = types.create_error_response(
                current_req_id,
                -32603,
                "Internal Server Error",
                f"Server error: {type(e).__name__} - {e}",
            )
            return error_response_payload, 500

    return app
