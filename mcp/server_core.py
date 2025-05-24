# mcp/server_core.py
import sys
from . import types
from .registry import ResourceError, ToolError, PromptError

# These were previously global functions in stdio_server.py
# Now, they will be methods of ServerCore or helper functions called by its methods.


async def _handle_initialize(
    req_id, params, tool_registry, resource_registry, prompt_registry
):
    capabilities = {
        "tools": (
            {"listChanged": False}
            if tool_registry and hasattr(tool_registry, "list_tool_definitions")
            else None
        ),
        "resources": (
            {
                "subscribe": False,
                "listChanged": False,
            }  # Set to False as notifications not implemented
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
            "name": "MicroPython MCP Server",  # Consider making this configurable
            "version": "0.1.0",
        },
        "protocolVersion": "2025-03-26",
        "capabilities": active_capabilities,
    }
    return types.create_success_response(req_id, capabilities_response)


async def _handle_prompts_list(req_id, params, prompt_registry):
    if not prompt_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Prompt registry not available.",
        )
    prompts = prompt_registry.list_prompts()
    return types.create_success_response(req_id, {"prompts": prompts})


async def _handle_prompts_get(req_id, params, prompt_registry):
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


async def _handle_resources_list(req_id, params, resource_registry):
    if not resource_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Resource registry not available.",
        )
    resources = resource_registry.list_resources()
    return types.create_success_response(req_id, {"resources": resources})


async def _handle_resources_read(req_id, params, resource_registry):
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


async def _handle_tools_list(req_id, params, tool_registry):
    if not tool_registry:
        return types.create_error_response(
            req_id, -32000, "Server Configuration Error", "Tool registry not available."
        )
    tool_definitions = tool_registry.list_tool_definitions()
    return types.create_success_response(req_id, {"tools": tool_definitions})


async def _handle_tools_call(req_id, params, tool_registry):
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


async def _handle_resources_subscribe(req_id, params, resource_registry):
    uri_to_subscribe = params.get("uri")
    if not uri_to_subscribe or not isinstance(uri_to_subscribe, str):
        return types.create_error_response(
            req_id,
            -32602,
            "Invalid Params",
            "Missing or invalid 'uri' parameter (must be a string).",
        )

    if not resource_registry:
        return types.create_error_response(
            req_id,
            -32000,
            "Server Configuration Error",
            "Resource registry not available.",
        )

    all_known_uris = [res_def["uri"] for res_def in resource_registry.list_resources()]

    if uri_to_subscribe in all_known_uris:
        # TODO: Actually store this subscription state per client/session if transport supports it.
        # For now, this just acknowledges and logs. No resources/updated notifications are sent.
        # server_core_instance.active_subscriptions.add(uri_to_subscribe) # If we were storing it
        print(
            f"ServerCore: Client 'subscribed' to resource URI: {uri_to_subscribe} (acknowledged, no notifications yet)",
            file=sys.stderr,
        )
        return types.create_success_response(req_id, {})  # Empty result on success
    else:
        return types.create_error_response(
            req_id,
            -32001,  # Using a more specific error code like "Resource not found"
            "Subscription Error",
            f"Resource URI '{uri_to_subscribe}' not found in registry.",
        )


async def _handle_resources_unsubscribe(req_id, params, resource_registry):
    uri_to_unsubscribe = params.get("uri")
    if not uri_to_unsubscribe or not isinstance(uri_to_unsubscribe, str):
        return types.create_error_response(
            req_id,
            -32602,
            "Invalid Params",
            "Missing or invalid 'uri' parameter (must be a string).",
        )

    # TODO: Actually remove this from stored subscription state per client/session.
    # For now, this just acknowledges and logs.
    # server_core_instance.active_subscriptions.discard(uri_to_unsubscribe) # If we were storing it
    print(
        f"ServerCore: Client 'unsubscribed' from resource URI: {uri_to_unsubscribe} (acknowledged)",
        file=sys.stderr,
    )

    return types.create_success_response(req_id, {})  # Empty result on success


class ServerCore:
    def __init__(self, tool_registry, resource_registry, prompt_registry):
        self.tool_registry = tool_registry
        self.resource_registry = resource_registry
        self.prompt_registry = prompt_registry
        # self.active_subscriptions = set() # TODO: Implement stateful subscription tracking if transport supports sessions/notifications

    async def process_message_dict(self, message_dict: dict):
        req_id = message_dict.get("id")
        method = message_dict.get("method")
        params = message_dict.get("params")

        if method == "initialize":
            return await _handle_initialize(
                req_id,
                params,
                self.tool_registry,
                self.resource_registry,
                self.prompt_registry,
            )
        elif method == "tools/list":
            return await _handle_tools_list(req_id, params, self.tool_registry)
        elif method == "tools/call":
            return await _handle_tools_call(req_id, params, self.tool_registry)
        elif method == "resources/list":
            return await _handle_resources_list(req_id, params, self.resource_registry)
        elif method == "resources/read":
            return await _handle_resources_read(req_id, params, self.resource_registry)
        elif method == "prompts/list":
            return await _handle_prompts_list(req_id, params, self.prompt_registry)
        elif method == "prompts/get":
            return await _handle_prompts_get(req_id, params, self.prompt_registry)
        elif method == "resources/subscribe":
            return await _handle_resources_subscribe(
                req_id, params, self.resource_registry
            )
        elif method == "resources/unsubscribe":
            return await _handle_resources_unsubscribe(
                req_id, params, self.resource_registry
            )
        else:
            return types.create_error_response(
                req_id,
                -32601,
                "Method Not Found",
                f"The method '{method}' is not supported by this server.",
            )
