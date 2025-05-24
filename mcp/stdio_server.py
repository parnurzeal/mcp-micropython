import sys
import uasyncio
import ujson
from . import types  # Assuming types.py is in the same mcp package
from .registry import (
    ResourceError,
    ToolError,
    PromptRegistry,
    PromptError,
)  # Import PromptRegistry and PromptError


# MCP Method Handlers
async def handle_initialize(
    req_id, params, tool_registry, resource_registry, prompt_registry
):  # Added prompt_registry
    capabilities = {
        "tools": (
            {"listChanged": False}
            if tool_registry and hasattr(tool_registry, "list_tool_definitions")
            else None
        ),
        "resources": (
            {"subscribe": False, "listChanged": False}
            if resource_registry and hasattr(resource_registry, "list_resources")
            else None
        ),
        "prompts": (
            {"listChanged": False}
            if prompt_registry and hasattr(prompt_registry, "list_prompts")
            else None
        ),
    }
    active_capabilities = {k: v for k, v in capabilities.items() if v is not None}
    capabilities_response = {
        "serverInfo": {
            "name": "MicroPython MCP Server",
            "version": "0.1.0",
        },
        "protocolVersion": "2025-03-26",
        "capabilities": active_capabilities,
    }
    return types.create_success_response(req_id, capabilities_response)


async def handle_prompts_list(
    req_id, params, prompt_registry
):  # Changed _ to prompt_registry
    if not prompt_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Prompt registry not available.",
        )
    prompts = prompt_registry.list_prompts()
    return types.create_success_response(req_id, {"prompts": prompts})


async def handle_prompts_get(
    req_id, params, prompt_registry
):  # Changed _ to prompt_registry
    prompt_name = params.get("name")
    prompt_arguments = params.get("arguments", {})

    if not prompt_name:
        return types.create_error_response(
            req_id, -32602, "Invalid Params", "Missing 'name' parameter for prompt."
        )

    if not prompt_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Prompt registry not available.",
        )

    try:
        prompt_result_dict = await prompt_registry.get_prompt_result(
            prompt_name, prompt_arguments
        )
        return types.create_success_response(req_id, prompt_result_dict)
    except PromptError as pe:
        error_code = -32001 if "not found" in str(pe).lower() else -32000
        return types.create_error_response(req_id, error_code, "Prompt Error", str(pe))
    except Exception as e:
        print(
            f"Unexpected error during prompt get for '{prompt_name}': {e}",
            file=sys.stderr,
        )
        return types.create_error_response(
            req_id,
            -32000,
            "Internal Server Error",
            f"Unexpected error getting prompt: {prompt_name}",
        )


async def handle_resources_list(req_id, params, resource_registry):
    # ... (existing implementation) ...
    if not resource_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Resource registry not available.",
        )
    resources = resource_registry.list_resources()
    return types.create_success_response(req_id, {"resources": resources})


async def handle_resources_read(req_id, params, resource_registry):
    # ... (existing implementation) ...
    uri_to_read = params.get("uri")
    if not uri_to_read:
        return types.create_error_response(
            req_id, -32602, "Invalid Params", "Missing 'uri' parameter."
        )
    if not resource_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Resource registry not available.",
        )
    try:
        content = await resource_registry.read_resource_content(uri_to_read)
        resource_content_obj = {}
        if isinstance(content, str):
            resource_content_obj = {
                "uri": uri_to_read,
                "mimeType": "text/plain",
                "text": content,
            }
        elif isinstance(content, bytes):
            import ubinascii

            resource_content_obj = {
                "uri": uri_to_read,
                "mimeType": "application/octet-stream",
                "blob": ubinascii.b2a_base64(content).decode("utf-8").strip(),
            }
        else:
            raise ResourceError(
                f"Resource handler for '{uri_to_read}' returned unexpected type: {type(content)}"
            )
        return types.create_success_response(
            req_id, {"contents": [resource_content_obj]}
        )
    except ResourceError as re:
        error_code = -32001 if "not found" in str(re).lower() else -32000
        return types.create_error_response(
            req_id, error_code, "Resource Error", str(re)
        )
    except Exception as e:
        print(
            f"Unexpected error during resource read for '{uri_to_read}': {e}",
            file=sys.stderr,
        )
        return types.create_error_response(
            req_id,
            -32000,
            "Internal Server Error",
            f"Unexpected error reading resource: {uri_to_read}",
        )


async def handle_tools_list(req_id, params, tool_registry):
    # ... (existing implementation) ...
    if not tool_registry:
        return types.create_error_response(
            req_id, -32000, "Server Configuration Error", "Tool registry not available."
        )
    tool_definitions = tool_registry.list_tool_definitions()
    return types.create_success_response(req_id, {"tools": tool_definitions})


async def handle_tools_call(req_id, params, tool_registry):
    # ... (existing implementation) ...
    if not tool_registry:
        return types.create_error_response(
            req_id, -32000, "Server Configuration Error", "Tool registry not available."
        )
    tool_name = params.get("name")
    tool_arguments = params.get("arguments")
    if not tool_name:
        return types.create_error_response(
            req_id,
            -32602,
            "Invalid Params",
            "Tool 'name' not provided in parameters for tools/call.",
        )
    try:
        result = await tool_registry.call_tool(tool_name, tool_arguments)
        call_tool_result = {
            "content": [{"type": "text", "text": str(result)}],
            "isError": False,
        }
        return types.create_success_response(req_id, call_tool_result)
    except ValueError as ve:
        return types.create_error_response(req_id, -32602, "Invalid Params", str(ve))
    except ToolError as te:
        print(f"Error during execution of tool '{tool_name}': {te}", file=sys.stderr)
        error_call_tool_result = {
            "content": [{"type": "text", "text": str(te)}],
            "isError": True,
        }
        return types.create_success_response(req_id, error_call_tool_result)
    except Exception as e:
        print(
            f"Unexpected error during tool call for '{tool_name}': {e}", file=sys.stderr
        )
        return types.create_error_response(
            req_id,
            -32000,
            "Internal Server Error",
            f"Unexpected error calling tool: {tool_name}",
        )


# Main message processing logic
async def process_mcp_message(
    message_dict, tool_registry, resource_registry, prompt_registry
):  # Added prompt_registry
    req_id = message_dict.get("id")
    method = message_dict.get("method")
    params = message_dict.get("params")

    if method == "initialize":
        return await handle_initialize(
            req_id, params, tool_registry, resource_registry, prompt_registry
        )
    elif method == "tools/list":
        return await handle_tools_list(req_id, params, tool_registry)
    elif method == "tools/call":
        return await handle_tools_call(req_id, params, tool_registry)
    elif method == "resources/list":
        return await handle_resources_list(req_id, params, resource_registry)
    elif method == "resources/read":
        return await handle_resources_read(req_id, params, resource_registry)
    elif method == "prompts/list":
        return await handle_prompts_list(req_id, params, prompt_registry)
    elif method == "prompts/get":
        return await handle_prompts_get(req_id, params, prompt_registry)
    else:
        return types.create_error_response(
            req_id,
            -32601,
            "Method Not Found",
            f"The method '{method}' is not supported by this server.",
        )


async def stdio_server(
    tool_registry,
    resource_registry,
    prompt_registry,  # Added prompt_registry
    custom_reader=None,
    custom_writer=None,
):
    if (
        not tool_registry or not resource_registry or not prompt_registry
    ):  # Check all three
        print(
            "Fatal Error: stdio_server requires ToolRegistry, ResourceRegistry, and PromptRegistry instances.",
            file=sys.stderr,
        )
        return

    # ... (rest of stdio_server, ensuring process_mcp_message is called with all three registries) ...
    # Inside the loop:
    # await process_mcp_message(message_dict, tool_registry, resource_registry, prompt_registry)
    # response_dict = await process_mcp_message(message_dict, tool_registry, resource_registry, prompt_registry)

    if custom_reader and custom_writer:
        reader = custom_reader
        writer = custom_writer
    else:
        reader = uasyncio.StreamReader(sys.stdin)
        writer = uasyncio.StreamWriter(sys.stdout, {})

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
                message_dict = ujson.loads(line_str)
            except ValueError:
                response_dict = types.create_error_response(
                    None, -32700, "Parse Error", "Invalid JSON received by server."
                )

            if response_dict is None:
                is_notification = "id" not in message_dict
                current_req_id = message_dict.get("id")

                if "method" not in message_dict or "jsonrpc" not in message_dict:
                    if not is_notification:
                        response_dict = types.create_error_response(
                            current_req_id,
                            -32600,
                            "Invalid Request",
                            "The JSON sent is not a valid Request object.",
                        )
                else:
                    if is_notification:
                        await process_mcp_message(
                            message_dict,
                            tool_registry,
                            resource_registry,
                            prompt_registry,
                        )
                        response_dict = None
                    else:
                        response_dict = await process_mcp_message(
                            message_dict,
                            tool_registry,
                            resource_registry,
                            prompt_registry,
                        )

            if response_dict:
                writer.write(ujson.dumps(response_dict).encode("utf-8") + b"\n")
                await writer.drain()
                if not custom_writer:
                    print(f"Sent response: {response_dict}", file=sys.stderr)
            elif (
                not custom_writer
                and "id" not in message_dict
                and "method" in message_dict
            ):
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
                f"Unhandled error in server loop: {type(e).__name__}: {e}",
                file=sys.stderr,
            )
            try:
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

    if not custom_reader:
        print("MicroPython MCP Stdio Server finished.", file=sys.stderr)
