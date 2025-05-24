import sys
import uasyncio
import ujson
from . import types  # Assuming types.py is in the same mcp package

# from .registry import ToolRegistry # ToolRegistry will be passed as an argument


# MCP Method Handlers
async def handle_initialize(req_id, params, registry):
    # Server capabilities - can be customized by the developer if they modify this or pass in config
    # For now, using fixed values.
    # `params` from the client might include client capabilities, which we are ignoring here.
    capabilities_response = {
        "serverInfo": {
            "name": "MicroPython MCP Server",
            "version": "0.1.0",  # TODO: Make this configurable
        },
        "protocolVersion": "2025-03-26",
        "capabilities": {
            "tools": {
                "listChanged": False
            },  # True if server can notify client of tool changes
            "resources": {
                "subscribe": False,
                "listChanged": False,
            },  # Added resource capabilities
            "prompts": {"listChanged": False},  # Added prompt capabilities
        },
    }
    return types.create_success_response(req_id, capabilities_response)


async def handle_prompts_list(req_id, params, registry):
    # For now, return a hardcoded list of prompts.
    # `params` could be used for pagination (cursor), ignored for now.
    sample_prompts = [
        {
            "name": "example_prompt",
            "description": "An example prompt template.",
            "arguments": [
                {
                    "name": "topic",
                    "description": "The topic to discuss",
                    "required": True,
                }
            ],
        }
    ]
    return types.create_success_response(req_id, {"prompts": sample_prompts})


async def handle_prompts_get(req_id, params, registry):
    prompt_name = params.get("name")
    prompt_arguments = params.get("arguments", {})  # Default to empty dict

    if not prompt_name:
        return types.create_error_response(
            req_id, -32602, "Invalid Params", "Missing 'name' parameter for prompt."
        )

    if prompt_name == "example_prompt":
        topic = prompt_arguments.get("topic", "a default topic")
        # Construct a simple message list based on the prompt
        messages = [
            {
                "role": "user",
                "content": {"type": "text", "text": f"Tell me about {topic}."},
            }
        ]
        # The GetPromptResult schema expects a "messages" key.
        # It can also have a "description" key for the resolved prompt.
        prompt_result = {"description": f"A prompt about {topic}", "messages": messages}
        return types.create_success_response(req_id, prompt_result)
    else:
        return types.create_error_response(
            req_id, -32001, "Prompt Not Found", f"Prompt '{prompt_name}' not found."
        )


async def handle_resources_list(req_id, params, registry):
    # For now, return a hardcoded list of resources.
    # A real implementation would manage resources dynamically.
    # `params` could be used for pagination (cursor), ignored for now.
    sample_resources = [
        {
            "uri": "file:///example.txt",
            "name": "Example Text File",
            "description": "A sample text file resource.",
            "mimeType": "text/plain",
        }
    ]
    return types.create_success_response(req_id, {"resources": sample_resources})


async def handle_resources_read(req_id, params, registry):
    uri_to_read = params.get("uri")
    if not uri_to_read:
        return types.create_error_response(
            req_id, -32602, "Invalid Params", "Missing 'uri' parameter."
        )

    # For "file:///example.txt", return hardcoded content for simple testing.
    if uri_to_read == "file:///example.txt":
        hardcoded_content = "This is the hardcoded content for file:///example.txt."
        resource_content_obj = {
            "uri": uri_to_read,
            "mimeType": "text/plain",
            "text": hardcoded_content,
        }
        return types.create_success_response(
            req_id, {"contents": [resource_content_obj]}
        )
    # Keep existing file reading logic for other file URIs if needed,
    # but for now, let's make it specific to example.txt for simplicity.
    # Or, more simply, only support example.txt for now.
    elif uri_to_read.startswith("file:///"):
        # For any other file URI that is not the special "example.txt",
        # treat it as if the file is not found or not supported by this simple server.
        actual_path_requested = uri_to_read[7:]  # Get the path part for the message
        return types.create_error_response(
            req_id,
            -32001,  # Resource Not Found
            "Resource Not Found",
            f"File not found: {actual_path_requested}",  # More generic message
        )
    else:
        return types.create_error_response(
            req_id,
            -32002,
            "Unsupported URI Scheme",
            f"URI scheme for '{uri_to_read}' not supported.",
        )


# Helper to check file existence, as os.path.exists might not be standard
def _file_exists(path):
    try:
        # Try to open for reading, if it fails with ENOENT, file doesn't exist
        # This is a more portable way in MicroPython than os.stat
        with open(path, "r") as f:
            pass
        return True
    except OSError as e:
        if hasattr(e, "args") and len(e.args) > 0 and e.args[0] == 2:  # ENOENT
            return False
        raise  # Re-raise other OSErrors


async def handle_tools_list(req_id, params, registry):
    # `params` could be used for filtering if supported, ignored for now.
    if not registry:
        return types.create_error_response(
            req_id, -32000, "Server Configuration Error", "Tool registry not available."
        )

    tool_definitions = registry.list_tool_definitions()
    # Ensure the response structure is {"tools": [Tool, Tool, ...]}
    return types.create_success_response(req_id, {"tools": tool_definitions})


async def handle_tools_call(req_id, params, registry):  # Renamed to handle_tools_call
    if not registry:
        return types.create_error_response(
            req_id, -32000, "Server Configuration Error", "Tool registry not available."
        )

    # According to MCP spec for tools/call, params should be:
    # { "name": "string", "arguments": object | null }
    tool_name = params.get("name")
    tool_arguments = params.get(
        "arguments"
    )  # This can be null/None if tool takes no args

    if not tool_name:
        return types.create_error_response(
            req_id,
            -32602,
            "Invalid Params",
            "Tool 'name' not provided in parameters for tools/call.",
        )

    try:
        # ToolRegistry.call_tool expects `params` as the arguments for the tool itself.
        result = await registry.call_tool(tool_name, tool_arguments)
        # Wrap successful result according to CallToolResult schema
        # Assuming simple text result for now.
        call_tool_result = {
            "content": [{"type": "text", "text": str(result)}],
            "isError": False,  # Explicitly set isError
            # structuredContent could be added here if tools provide it
        }
        return types.create_success_response(req_id, call_tool_result)
    except (
        ValueError
    ) as ve:  # Errors like tool not found or bad params for call_tool itself
        return types.create_error_response(req_id, -32602, "Invalid Params", str(ve))
    except Exception as e:  # This catches ToolError from registry.call_tool
        # Report tool execution errors within a CallToolResult
        print(f"Error during execution of tool '{tool_name}': {e}", file=sys.stderr)
        error_call_tool_result = {
            "content": [{"type": "text", "text": str(e)}],
            "isError": True,
        }
        return types.create_success_response(req_id, error_call_tool_result)


# Main message processing logic
async def process_mcp_message(message_dict, registry):
    """
    Processes an incoming MCP message dictionary using the tool registry.
    """
    req_id = message_dict.get("id")
    method = message_dict.get("method")
    params = message_dict.get(
        "params"
    )  # These are the params for the MCP method itself

    if method == "initialize":
        return await handle_initialize(req_id, params, registry)
    elif method == "tools/list":
        return await handle_tools_list(req_id, params, registry)
    elif method == "tools/call":
        return await handle_tools_call(req_id, params, registry)
    elif method == "resources/list":
        return await handle_resources_list(req_id, params, registry)
    elif method == "resources/read":
        return await handle_resources_read(req_id, params, registry)
    elif method == "prompts/list":
        return await handle_prompts_list(req_id, params, registry)
    elif method == "prompts/get":
        return await handle_prompts_get(req_id, params, registry)
    else:
        return types.create_error_response(
            req_id,
            -32601,
            "Method Not Found",
            f"The method '{method}' is not supported by this server.",
        )


async def stdio_server(tool_registry, custom_reader=None, custom_writer=None):
    """
    MicroPython MCP Server transport for stdio.
    Communicates with an MCP client by reading from stdin and writing to stdout.
    Requires a ToolRegistry instance.
    Can accept custom reader/writer for testing.
    """
    if not tool_registry:
        # This is a programming error, should not happen if used correctly.
        print(
            "Fatal Error: stdio_server requires a ToolRegistry instance.",
            file=sys.stderr,
        )
        return

    if custom_reader and custom_writer:
        reader = custom_reader
        writer = custom_writer
    else:
        reader = uasyncio.StreamReader(sys.stdin)
        writer = uasyncio.StreamWriter(sys.stdout, {})

    if not custom_reader:  # Only print startup message in actual runs
        print(
            "MicroPython MCP Stdio Server started. Waiting for messages...",
            file=sys.stderr,
        )

    while True:
        current_req_id = None  # To hold the ID of the message being processed
        response_dict = None  # Define response_dict here to ensure it's always available for writing
        try:
            line = await reader.readline()
            if not line:
                if not custom_reader:  # Avoid printing EOF for test streams
                    print("EOF received, server shutting down.", file=sys.stderr)
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            if not custom_reader:  # Avoid printing received line for test streams
                print(f"Received: {line_str}", file=sys.stderr)

            try:
                message_dict = ujson.loads(line_str)
            except ValueError:  # Invalid JSON
                # JSON-RPC spec: If there is an error in parsing the JSON text,
                # the server MUST reply with an error object with id set to null.
                response_dict = types.create_error_response(
                    None, -32700, "Parse Error", "Invalid JSON received by server."
                )
                # No continue here, let it flow to writer

            if response_dict is None:  # If no parse error, proceed to process message
                # Check if it's a notification (no 'id' field)
                is_notification = "id" not in message_dict

                current_req_id = message_dict.get(
                    "id"
                )  # Will be None for notifications

                if "method" not in message_dict or "jsonrpc" not in message_dict:
                    # This is an invalid request structure.
                    # If it has an ID, an error response should be sent.
                    # If it's a notification (no ID), technically no response, but it's malformed.
                    # JSON-RPC spec is a bit vague on malformed notifications.
                    # For simplicity, we'll send an error if an ID is present.
                    if not is_notification:
                        response_dict = types.create_error_response(
                            current_req_id,
                            -32600,
                            "Invalid Request",
                            "The JSON sent is not a valid Request object.",
                        )
                    # If it's a notification and malformed, we just ignore it.
                else:
                    # Valid request structure (or notification)
                    if is_notification:
                        # It's a notification, process it but don't prepare a response dict
                        # (as no response should be sent)
                        await process_mcp_message(message_dict, tool_registry)
                        response_dict = None  # Ensure no response is sent
                    else:
                        # It's a regular request with an ID, process and get response
                        response_dict = await process_mcp_message(
                            message_dict, tool_registry
                        )

            # Only write a response if response_dict is not None
            # (i.e., it was not a notification, or it was an error during parsing a non-notification)
            if response_dict:
                writer.write(ujson.dumps(response_dict).encode("utf-8") + b"\n")
                await writer.drain()
                if not custom_writer:
                    print(f"Sent response: {response_dict}", file=sys.stderr)
            elif (
                not custom_writer
                and "id" not in message_dict
                and "method" in message_dict
            ):  # Log if it was a valid notification
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
            # Catch-all for unexpected errors within the server loop
            print(
                f"Unhandled error in server loop: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            # Attempt to send a JSON-RPC error response if possible
            try:
                # Use current_req_id if available from the message being processed
                error_resp_internal = types.create_error_response(
                    current_req_id, -32603, "Internal Server Error", str(e)
                )
                writer.write(ujson.dumps(error_resp_internal).encode("utf-8") + b"\n")
                await writer.drain()
            except Exception as e_inner:
                print(
                    f"Critical: Failed to send internal error response: {e_inner}",
                    file=sys.stderr,
                )
            # Depending on severity, might want to break or continue.
            # For now, continue, but frequent errors here would be problematic.

    if not custom_reader:  # Only print shutdown message in actual runs
        print("MicroPython MCP Stdio Server finished.", file=sys.stderr)


# Note: The if __name__ == "__main__": block for running example tools
# will be moved to main.py to keep stdio_server.py as a library module.
