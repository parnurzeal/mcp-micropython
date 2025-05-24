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
