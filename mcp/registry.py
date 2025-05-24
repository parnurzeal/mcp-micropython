# mcp/registry.py
import sys


class ToolError(Exception):
    """Custom exception for tool execution errors."""

    pass


class ToolRegistry:
    def __init__(self):
        self._tools = {}  # Stores tool definitions and handlers
        # Example structure for self._tools[tool_name]:
        # {
        #     "definition": {"name": "...", "description": "...", "inputSchema": {...}},
        #     "handler": function_ref,
        #     "param_names": ["param1", "param2"] # For ordered params if not using named
        # }

    def register_tool(
        self, name, description, input_schema, handler_func, param_names=None
    ):
        """
        Registers a tool.
        :param name: The name of the tool (e.g., "add", "echo").
        :param description: A description of what the tool does.
        :param input_schema: A dictionary describing the expected input parameters.
                             For simplicity, this can be a dict like {"param_name": "description"}.
                             A more complex JSON schema can be used if needed.
        :param handler_func: The asynchronous function that implements the tool's logic.
                             It should accept parameters as keyword arguments or a single dict.
        :param param_names: Optional list of parameter names in order, if the handler
                              expects positional arguments from a list of params.
                              If None, handler is expected to take **kwargs or a dict.
        """
        if name in self._tools:
            # Or raise an error, or log a warning
            print(f"Warning: Tool '{name}' is being redefined.", file=sys.stderr)

        # If input_schema is an empty dict or None, store it as None,
        # signifying no parameters / inputSchema should be null.
        stored_input_schema = input_schema if input_schema else None

        self._tools[name] = {
            "definition": {  # This stores the raw parts for the definition
                "name": name,
                "description": description,
                "inputSchema_properties": stored_input_schema,  # Store the properties map or None
            },
            "handler": handler_func,
            "param_names": param_names,
        }
        print(f"Tool '{name}' registered.", file=sys.stderr)

    def get_tool_definition(self, name):
        # This method might not be directly used by the server if list_tool_definitions is comprehensive
        if name in self._tools:
            raw_def_parts = self._tools[name]["definition"]
            properties_map = raw_def_parts["inputSchema_properties"]
            if properties_map:
                final_schema = {"type": "object", "properties": properties_map}
            else:
                final_schema = None
            return {
                "name": raw_def_parts["name"],
                "description": raw_def_parts["description"],
                "inputSchema": final_schema,
            }
        return None

    def list_tool_definitions(self):
        tool_defs = []
        for tool_name in self._tools:
            raw_def_parts = self._tools[tool_name]["definition"]
            properties_map = raw_def_parts["inputSchema_properties"]

            if properties_map:  # If it's a non-empty dict of properties
                final_input_schema = {
                    "type": "object",
                    "properties": properties_map,
                    # "required": [] # Could be added if register_tool collected this
                }
            else:  # If properties_map is None (meaning no params for the tool)
                final_input_schema = {
                    "type": "object",
                    "properties": {},
                }  # Default empty schema

            tool_defs.append(
                {
                    "name": raw_def_parts["name"],
                    "description": raw_def_parts["description"],
                    "inputSchema": final_input_schema,
                    # "annotations": {} # Can be added if supported
                }
            )
        return tool_defs

    async def call_tool(self, name, params):
        """
        Calls a registered tool.
        :param name: Name of the tool.
        :param params: Parameters for the tool. Can be a dictionary (for named params)
                       or a list (for positional params, if param_names was set).
        :return: The result of the tool execution.
        :raises: ValueError if tool not found or if params are incorrect.
        """
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")

        tool_info = self._tools[name]
        handler = tool_info["handler"]
        param_names = tool_info["param_names"]

        try:
            if isinstance(params, dict):
                return await handler(**params)
            elif isinstance(params, list):
                if param_names:
                    if len(params) == len(param_names):
                        kwargs = dict(zip(param_names, params))
                        return await handler(**kwargs)
                    else:
                        # This ValueError is specific to incorrect number of list params
                        raise ValueError(
                            f"Tool '{name}' expects {len(param_names)} positional parameters, got {len(params)}."
                        )
                else:
                    # This ValueError is for when list params are given but not expected
                    raise ValueError(
                        f"Tool '{name}' received list parameters but has no defined positional parameter names."
                    )
            elif params is None:
                # Call handler without arguments if params is None
                # Assumes tools expecting no args are called with params=None
                return await handler()
            else:
                # This ValueError is for when 'params' is not dict, list, or None
                raise ValueError(
                    f"Parameters for tool '{name}' must be a dictionary, a list (if positional), or null (if no arguments)."
                )
        except Exception as e:
            # Catch errors from the tool handler itself (e.g., mock_error_tool raising ValueError)
            # or from the parameter preparation (e.g., wrong number of list args).
            # Wrap them in ToolError to be handled by stdio_server.
            # Check if it's already a ToolError to avoid double wrapping (though ToolError is simple now)
            if isinstance(e, ToolError):
                raise  # Re-raise if it's already a ToolError
            if isinstance(e, ValueError) and (
                "positional parameters" in str(e)
                or "no defined positional parameter names" in str(e)
                or "must be a dictionary" in str(e)
            ):
                # Re-raise ValueErrors related to param structure directly, as they are not tool execution errors
                raise
            # Simpler raise for MicroPython compatibility, removing 'from e'
            raise ToolError(f"Error executing tool '{name}': {str(e)}")


# Global default registry (optional, or server can instantiate its own)
# default_registry = ToolRegistry()


class ResourceError(Exception):
    """Custom exception for resource handling errors."""

    pass


class ResourceRegistry:
    def __init__(self):
        self._resources = {}
        # Example structure for self._resources[uri_str]:
        # {
        #     "definition": {"uri": "...", "name": "...", "description": "...", "mimeType": "..."},
        #     "read_handler": async_function_ref # Takes URI, returns content (str/bytes)
        # }

    def register_resource(
        self,
        uri: str,
        name: str,
        read_handler: callable,
        description: str = None,
        mime_type: str = "text/plain",
    ):
        """
        Registers a resource.
        :param uri: The unique URI of the resource (e.g., "file:///example.txt").
        :param name: A human-readable name for the resource.
        :param read_handler: An async function that takes the URI (str) and returns its content (str or bytes).
        :param description: Optional description of the resource.
        :param mime_type: Optional MIME type of the resource.
        """
        if uri in self._resources:
            print(f"Warning: Resource URI '{uri}' is being redefined.", file=sys.stderr)

        self._resources[uri] = {
            "definition": {
                "uri": uri,
                "name": name,
                "description": description,
                "mimeType": mime_type,
            },
            "read_handler": read_handler,
        }
        print(f"Resource '{name}' with URI '{uri}' registered.", file=sys.stderr)

    def list_resources(self):
        """Returns a list of resource definition objects."""
        return [res_info["definition"] for res_info in self._resources.values()]

    async def read_resource_content(self, uri: str):
        """
        Reads the content of a registered resource using its handler.
        :param uri: The URI of the resource to read.
        :return: The content of the resource (str or bytes).
        :raises: ResourceError if resource not found or handler fails.
        """
        if uri not in self._resources:
            raise ResourceError(f"Resource with URI '{uri}' not found.")

        resource_info = self._resources[uri]
        handler = resource_info["read_handler"]

        try:
            # The handler is expected to be an async function that takes the URI
            content = await handler(uri)
            return content
        except Exception as e:
            # Wrap errors from the handler in ResourceError
            if isinstance(e, ResourceError):
                raise
            raise ResourceError(f"Error reading resource '{uri}': {str(e)}")


class PromptError(Exception):
    """Custom exception for prompt handling errors."""

    pass


class PromptRegistry:
    def __init__(self):
        self._prompts = {}
        # Example structure for self._prompts[prompt_name]:
        # {
        #     "definition": {"name": "...", "description": "...", "arguments": [...]},
        #     "get_handler": async_function_ref
        #     # Handler takes (name: str, arguments: dict)
        #     # and returns dict like {"messages": [...], "description": "..."}
        # }

    def register_prompt(
        self, name: str, description: str, arguments_schema: list, get_handler: callable
    ):
        """
        Registers a prompt template.
        :param name: The unique name of the prompt.
        :param description: A human-readable description.
        :param arguments_schema: A list of argument definition objects
                                 (e.g., [{"name": "topic", "description": "...", "required": True}]).
                                 Can be None or empty list if no arguments.
        :param get_handler: An async function that takes (name: str, arguments: dict)
                            and returns a dict for GetPromptResult (messages, optional description).
        """
        if name in self._prompts:
            print(f"Warning: Prompt '{name}' is being redefined.", file=sys.stderr)

        self._prompts[name] = {
            "definition": {
                "name": name,
                "description": description,
                "arguments": arguments_schema if arguments_schema else [],
            },
            "get_handler": get_handler,
        }
        print(f"Prompt '{name}' registered.", file=sys.stderr)

    def list_prompts(self):
        """Returns a list of prompt definition objects."""
        return [prompt_info["definition"] for prompt_info in self._prompts.values()]

    async def get_prompt_result(self, name: str, arguments: dict = None):
        """
        Gets the resolved prompt messages and description using its handler.
        :param name: The name of the prompt.
        :param arguments: A dictionary of arguments for the prompt.
        :return: A dictionary suitable for GetPromptResult (e.g., {"messages": [...], "description": "..."}).
        :raises: PromptError if prompt not found or handler fails.
        """
        if arguments is None:
            arguments = {}

        if name not in self._prompts:
            raise PromptError(f"Prompt '{name}' not found.")

        prompt_info = self._prompts[name]
        handler = prompt_info["get_handler"]

        try:
            # Handler is expected to be async and take name, arguments
            result_dict = await handler(name, arguments)
            # Ensure 'messages' key is present as per GetPromptResult schema
            if "messages" not in result_dict:
                raise PromptError(
                    f"Prompt handler for '{name}' did not return 'messages'."
                )
            return result_dict
        except Exception as e:
            if isinstance(e, PromptError):
                raise
            raise PromptError(f"Error getting prompt '{name}': {str(e)}")
