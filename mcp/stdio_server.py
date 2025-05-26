# mcp/stdio_server.py
import sys
import asyncio
import json
from . import types
from .server_core import ServerCore  # Import ServerCore

# The individual handle_... methods and process_mcp_message are now in ServerCore.


async def stdio_server(
    tool_registry,
    resource_registry,
    prompt_registry,
    custom_reader=None,
    custom_writer=None,
):
    if not tool_registry or not resource_registry or not prompt_registry:
        print(
            "Fatal Error: stdio_server requires ToolRegistry, ResourceRegistry, and PromptRegistry instances.",
            file=sys.stderr,
        )
        return

    server_core = ServerCore(tool_registry, resource_registry, prompt_registry)

    if custom_reader and custom_writer:
        reader = custom_reader
        writer = custom_writer
    else:
        reader = asyncio.StreamReader(sys.stdin)
        writer = asyncio.StreamWriter(sys.stdout, {})

    if not custom_reader:
        print(
            "MicroPython MCP Stdio Server started. Waiting for messages...",
            file=sys.stderr,
        )

    while True:
        current_req_id = None
        response_dict = None
        try:
            line = await reader.readline()
            if not line:
                if not custom_reader:
                    print("EOF received, server shutting down.", file=sys.stderr)
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            if not custom_reader:
                print(f"Received: {line_str}", file=sys.stderr)

            try:
                message_dict = json.loads(line_str)
            except ValueError:
                response_dict = types.create_error_response(
                    None, -32700, "Parse Error", "Invalid JSON received by server."
                )

            if response_dict is None:  # Only process if parsing was successful
                is_notification = "id" not in message_dict
                current_req_id = message_dict.get("id")

                if "method" not in message_dict or "jsonrpc" not in message_dict:
                    if (
                        not is_notification
                    ):  # Only send error if it's not a notification
                        response_dict = types.create_error_response(
                            current_req_id,
                            -32600,
                            "Invalid Request",
                            "The JSON sent is not a valid Request object.",
                        )
                else:
                    # Call the processing method on the ServerCore instance
                    if is_notification:
                        await server_core.process_message_dict(message_dict)
                        response_dict = None
                    else:
                        response_dict = await server_core.process_message_dict(
                            message_dict
                        )

            if response_dict:
                writer.write(json.dumps(response_dict).encode("utf-8") + b"\n")
                await writer.drain()
                if not custom_writer:
                    print(f"Sent response: {response_dict}", file=sys.stderr)
            elif (
                not custom_writer
                and "id" not in message_dict
                and "method" in message_dict
            ):  # Log processed notifications
                print(
                    f"Processed notification (method: {message_dict.get('method')}), no response sent.",
                    file=sys.stderr,
                )

        except KeyboardInterrupt:
            print(
                "Server interrupted by KeyboardInterrupt. Shutting down.",
                file=sys.stderr,
            )
            break
        except Exception as e:
            print(
                f"Unhandled error in stdio_server loop: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            # Try to send a generic internal server error response if possible
            if current_req_id is not None:  # Only if it was a request with an ID
                try:
                    error_resp_internal = types.create_error_response(
                        current_req_id, -32603, "Internal Server Error", str(e)
                    )
                    writer.write(
                        json.dumps(error_resp_internal).encode("utf-8") + b"\n"
                    )
                    await writer.drain()
                except Exception as e_inner:
                    print(
                        f"Critical: Failed to send internal error response: {e_inner}",
                        file=sys.stderr,
                    )

    if not custom_reader:
        print("MicroPython MCP Stdio Server finished.", file=sys.stderr)
