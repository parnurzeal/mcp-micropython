# mcp/wifi_server.py
import sys
import asyncio
import json
import network

from . import types
from .server_core import ServerCore

try:
    from microdot import Microdot, Response
except ImportError:
    print(
        "Microdot library not found. Please install it (e.g., into /lib/microdot on device).",
        file=sys.stderr,
    )
    Microdot = None
    Response = None

WIFI_CONNECT_TIMEOUT_S = 15
DEFAULT_MCP_PORT = 8080


async def wifi_mcp_server(
    tool_registry,
    resource_registry,
    prompt_registry,
    wifi_ssid: str,
    wifi_password: str,
    mcp_port: int = DEFAULT_MCP_PORT,
    server_name: str = "MicroPython MCP Wi-Fi Server",
    server_version: str = "0.1.0",
):
    if Microdot is None or Response is None:
        print(
            "Microdot library not loaded correctly. Cannot start Wi-Fi server.",
            file=sys.stderr,
        )
        return

    if not all(
        [tool_registry, resource_registry, prompt_registry, wifi_ssid, wifi_password]
    ):
        print(
            "Fatal Error: wifi_mcp_server requires registries, Wi-Fi SSID, and password.",
            file=sys.stderr,
        )
        return

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(f"Attempting to connect to Wi-Fi SSID: {wifi_ssid}", file=sys.stderr)
    wlan.connect(wifi_ssid, wifi_password)

    max_wait = WIFI_CONNECT_TIMEOUT_S
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:  # STAT_GOT_IP is 3
            break
        max_wait -= 1
        print("Waiting for Wi-Fi connection...", file=sys.stderr)
        await asyncio.sleep(1)

    if wlan.status() != 3:  # network.STAT_GOT_IP
        print(f"Wi-Fi connection failed. Status: {wlan.status()}", file=sys.stderr)
        return

    pico_ip_address = wlan.ifconfig()[0]
    print(f"Connected to Wi-Fi. Pico IP: {pico_ip_address}", file=sys.stderr)

    server_core_instance = ServerCore(tool_registry, resource_registry, prompt_registry)
    app = create_mcp_microdot_app(server_core_instance)

    print(
        f"Starting MCP Wi-Fi Server (Microdot) on {pico_ip_address}:{mcp_port}",
        file=sys.stderr,
    )
    try:
        await app.start_server(host="0.0.0.0", port=mcp_port, debug=False)
    except KeyboardInterrupt:
        print("MCP Wi-Fi Server interrupted. Shutting down.", file=sys.stderr)
        if hasattr(app, "shutdown") and callable(app.shutdown):
            app.shutdown()
    except asyncio.CancelledError:
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
        print("MCP Wi-Fi Server (Microdot) stopped.", file=sys.stderr)


def create_mcp_microdot_app(server_core_instance: ServerCore):
    if Microdot is None or Response is None:
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
        print(
            f"--- MCP Wi-Fi: Request received from {client_ip} to {request.path} ---",
            file=sys.stderr,
        )
        print(
            f"MCP Wi-Fi: Method: {request.method}, Content-Type: {request.content_type}",
            file=sys.stderr,
        )

        message_dict = None
        current_req_id = None
        response_data = None
        http_status_code = 200

        try:
            if (
                request.content_type
                and "application/json" in request.content_type.lower()
            ):
                print(f"MCP Wi-Fi: Attempting to parse JSON body...", file=sys.stderr)
                try:
                    message_dict = request.json
                except ValueError:
                    message_dict = None
                if message_dict is None:
                    print(
                        f"MCP Wi-Fi: JSON parsing failed or empty body.",
                        file=sys.stderr,
                    )
                    response_data = types.create_error_response(
                        None,
                        -32700,
                        "Parse Error",
                        "Invalid or empty JSON received by server.",
                    )
                    http_status_code = 400
                else:
                    print(f"MCP Wi-Fi: Parsed JSON: {message_dict}", file=sys.stderr)
            else:
                print(
                    f"MCP Wi-Fi: Invalid Content-Type: {request.content_type}",
                    file=sys.stderr,
                )
                response_data = types.create_error_response(
                    None,
                    -32600,
                    "Invalid Request",
                    "Content-Type must be application/json.",
                )
                http_status_code = 415

            if http_status_code != 200:
                print(
                    f"MCP Wi-Fi: Handler returning early (HTTP Error): {response_data}, {http_status_code}",
                    file=sys.stderr,
                )
                return Response(response_data, status_code=http_status_code)

            is_notification = "id" not in message_dict
            current_req_id = message_dict.get("id")

            if "method" not in message_dict or "jsonrpc" not in message_dict:
                print(f"MCP Wi-Fi: Invalid JSON-RPC structure.", file=sys.stderr)
                if not is_notification:
                    response_data = types.create_error_response(
                        current_req_id,
                        -32600,
                        "Invalid Request",
                        "The JSON sent is not a valid Request object.",
                    )
                else:
                    print(
                        f"MCP Wi-Fi: Malformed notification, returning 204.",
                        file=sys.stderr,
                    )
                    return Response(status_code=204)
            else:
                print(
                    f"MCP Wi-Fi: Calling ServerCore for method: {message_dict.get('method')}",
                    file=sys.stderr,
                )
                if is_notification:
                    await server_core_instance.process_message_dict(message_dict)
                    print(
                        f"MCP Wi-Fi: Processed notification. Returning 204.",
                        file=sys.stderr,
                    )
                    return Response(status_code=204)
                else:
                    response_data = await server_core_instance.process_message_dict(
                        message_dict
                    )
                    print(
                        f"MCP Wi-Fi: ServerCore returned: {response_data}",
                        file=sys.stderr,
                    )
                    if response_data is None:
                        print(
                            f"MCP Wi-Fi: Error: ServerCore returned None for non-notification.",
                            file=sys.stderr,
                        )
                        response_data = types.create_error_response(
                            current_req_id,
                            -32603,
                            "Internal Server Error",
                            "ServerCore returned no response.",
                        )

            if response_data:
                print(
                    f"MCP Wi-Fi: Handler returning (Success/RPC Error in body): {response_data}",
                    file=sys.stderr,
                )
                return Response(response_data)
            elif is_notification:
                print(
                    f"MCP Wi-Fi: Reached end for notification (should not happen). Ensuring 204.",
                    file=sys.stderr,
                )
                return Response(status_code=204)
            else:
                print(
                    f"MCP Wi-Fi: Unhandled case. Sending generic internal error.",
                    file=sys.stderr,
                )
                response_data = types.create_error_response(
                    current_req_id,
                    -32603,
                    "Internal Server Error",
                    "Unhandled server state.",
                )
                return Response(response_data, status_code=500)

        except Exception as e:
            print(
                f"MCP Wi-Fi: Exception in handle_mcp_request: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            if hasattr(sys, "print_exception"):
                sys.print_exception(e, sys.stderr)
            error_response_payload = types.create_error_response(
                current_req_id,
                -32603,
                "Internal Server Error",
                f"Server error: {type(e).__name__} - {str(e)}",
            )
            print(
                f"MCP Wi-Fi: Handler returning (Exception): {error_response_payload}, 500",
                file=sys.stderr,
            )
            return Response(error_response_payload, status_code=500)

    return app
