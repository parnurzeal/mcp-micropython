import sys
import uasyncio
import ujson
from . import types  # Assuming types.py is in the same mcp package


# Placeholder for actual MCP message processing logic
async def process_mcp_message(message_dict):
    """
    Processes an incoming MCP message dictionary and returns a response dictionary.
    This is a placeholder and should be replaced with actual MCP logic.
    """
    req_id = message_dict.get("id")
    method = message_dict.get("method")

    if method == "echo":
        return types.create_success_response(req_id, message_dict.get("params"))
    elif method == "add":
        params = message_dict.get("params")
        if isinstance(params, list) and len(params) == 2:
            try:
                result = params[0] + params[1]
                return types.create_success_response(req_id, result)
            except TypeError:
                return types.create_error_response(
                    req_id, -32602, "Invalid params", "Parameters must be numbers"
                )
        else:
            return types.create_error_response(
                req_id,
                -32602,
                "Invalid params",
                "Expected a list of two numbers for 'add' method",
            )
    else:
        return types.create_error_response(
            req_id, -32601, "Method not found", f"Method '{method}' not implemented."
        )


async def stdio_server(custom_reader=None, custom_writer=None):
    """
    MicroPython MCP Server transport for stdio.
    Communicates with an MCP client by reading from stdin and writing to stdout.
    Can accept custom reader/writer for testing.
    """
    if custom_reader and custom_writer:
        reader = custom_reader
        writer = custom_writer
    else:
        reader = uasyncio.StreamReader(sys.stdin)
        writer = uasyncio.StreamWriter(sys.stdout, {})

    # Only print to stderr if not using custom streams (i.e., in real run, not test)
    if not custom_reader and not custom_writer:
        print(
            "MicroPython MCP Stdio Server started. Waiting for messages...",
            file=sys.stderr,
        )

    while True:
        req_id = None  # Initialize req_id at the start of the loop
        try:
            # req_id will be properly assigned after parsing if message is valid
            line = await reader.readline()
            if not line:
                print("EOF received, server shutting down.", file=sys.stderr)
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:  # Skip empty lines
                continue

            print(f"Received: {line_str}", file=sys.stderr)

            try:
                message_dict = ujson.loads(line_str)
            except ValueError:
                # Attempt to create an error response even if ID is not parsable
                # JSON-RPC spec says id can be null. If not even JSON, hard to get ID.
                error_resp = types.create_error_response(
                    None, -32700, "Parse error", "Invalid JSON received"
                )
                writer.write(ujson.dumps(error_resp).encode("utf-8") + b"\n")
                await writer.drain()
                print(f"Sent error (parse): {error_resp}", file=sys.stderr)
                continue

            req_id = message_dict.get("id")  # Get ID for responses

            response_dict = await process_mcp_message(message_dict)

            writer.write(ujson.dumps(response_dict).encode("utf-8") + b"\n")
            await writer.drain()
            print(f"Sent response: {response_dict}", file=sys.stderr)

        except KeyboardInterrupt:
            print("Server interrupted. Shutting down.", file=sys.stderr)
            break
        except Exception as e:
            print(f"Unhandled error: {e}", file=sys.stderr)
            # Try to send a generic error response if possible
            # This might fail if the error is in ujson or writer itself
            try:
                # Ensure req_id from the loop's scope is used if available
                _req_id_for_error = locals().get("req_id", None)
                error_resp = types.create_error_response(
                    _req_id_for_error, -32603, "Internal error", str(e)
                )
                writer.write(ujson.dumps(error_resp).encode("utf-8") + b"\n")
                await writer.drain()
            except Exception as e_inner:
                print(
                    f"Failed to send internal error response: {e_inner}",
                    file=sys.stderr,
                )
            # Depending on severity, might want to break or continue
            # For now, let's continue, but this could indicate a persistent issue
            # break

    # Only print to stderr if not using custom streams
    if not custom_reader and not custom_writer:
        print("MicroPython MCP Stdio Server finished.", file=sys.stderr)


if __name__ == "__main__":
    try:
        # When run directly, use default stdio
        uasyncio.run(stdio_server())
    except KeyboardInterrupt:
        print("Exiting server.")
