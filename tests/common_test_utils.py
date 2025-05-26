# tests/common_test_utils.py
import sys

# Ensure the project root is in the path if this file is run directly for some reason,
# or if other test files import from it and their own path setup isn't sufficient.
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.registry import (
    ToolRegistry,
    ResourceRegistry,
    ResourceError,
)  # Moved ResourceRegistry and ResourceError import here


# --- Mock Tool Handlers ---
async def mock_echo_tool(message: str):
    return f"echo: {message}"


async def mock_add_tool(a, b):
    return float(a) + float(b)


async def mock_no_params_tool():
    return "no_params_tool_ran"


async def mock_error_tool():
    raise ValueError("This tool intentionally errors.")


# Helper to create a registry with common mock tools for tests
def setup_test_registry():
    registry = ToolRegistry()
    registry.register_tool(
        "echo", "Echoes", {"message": {"type": "string"}}, mock_echo_tool
    )
    registry.register_tool(
        "add",
        "Adds",
        {"a": {"type": "number"}, "b": {"type": "number"}},
        mock_add_tool,
        param_names=["a", "b"],
    )
    registry.register_tool("info", "No params", None, mock_no_params_tool)
    registry.register_tool("error_tool", "Errors", {}, mock_error_tool)
    return registry


# --- Common Resource Registry Setup ---
# (This is minimal for now as resource handlers are simple in stdio_server.py)
# If main.py registers specific resource handlers, this might need to mirror that.
# ResourceRegistry and ResourceError are already imported at the top.


async def example_common_read_handler(uri: str):
    # A generic handler for tests, can be more specific if needed
    if uri == "file:///example.txt":
        return "Common test content for file:///example.txt"
    elif uri == "bytes:///test.bin":
        return b"binary_data"
    raise ResourceError(f"Common test handler does not support URI: {uri}")


def setup_common_resource_registry():
    res_registry = ResourceRegistry()
    res_registry.register_resource(
        uri="file:///example.txt",
        name="Common Test Example File",
        description="A common resource for testing.",
        mime_type="text/plain",
        read_handler=example_common_read_handler,
    )
    res_registry.register_resource(
        uri="bytes:///test.bin",
        name="Common Test Binary File",
        description="A common binary resource for testing.",
        mime_type="application/octet-stream",
        read_handler=example_common_read_handler,
    )
    return res_registry


# --- Common Prompt Registry Setup ---
from mcp.registry import (
    PromptRegistry,
    PromptError,
)  # Already imported PromptError if ResourceError was


async def example_common_get_prompt_handler(name: str, arguments: dict):
    if name == "common_example_prompt":
        topic = arguments.get("topic", "default test topic")
        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Common test prompt about {topic}",
                },
            }
        ]
        return {"description": f"Common test prompt: {topic}", "messages": messages}
    raise PromptError(f"Common test prompt handler does not support prompt: {name}")


def setup_common_prompt_registry():
    prompt_reg = PromptRegistry()
    prompt_reg.register_prompt(
        name="common_example_prompt",
        description="A common prompt for testing.",
        arguments_schema=[
            {"name": "topic", "description": "Test topic", "required": False}
        ],
        get_handler=example_common_get_prompt_handler,
    )
    return prompt_reg


# --- ManualMock Class (copied from tests/test_wifi_server.py) ---
class ManualMock:
    def __init__(
        self,
        spec=None,
        return_value=None,
        side_effect=None,
        name=None,
        track_calls=True,
    ):
        self._name = str(name) if name is not None else "ManualMock"
        self._return_value = return_value
        self._side_effect = side_effect
        self.call_args_list = []
        self.call_count = 0
        self._spec = spec
        self._children = {}
        self._track_calls = track_calls

    def __repr__(self):
        try:
            return f"<ManualMock name='{str(self._name)}' id='{id(self)}'>"
        except Exception:
            return "<ManualMock instance (repr error)>"

    def __str__(self):
        try:
            return f"<ManualMock name='{str(self._name)}' (str)>"
        except Exception:
            return "<ManualMock instance (str error)>"

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        if self._track_calls:
            self.call_args_list.append({"args": args, "kwargs": kwargs})

        # DEBUG PRINT inside ManualMock.__call__
        # Conditionally print to reduce noise, or remove if too verbose for general runs
        # if self._track_calls: # Example: only print if tracking calls
        # print(f"DEBUG_MANUAL_MOCK_CALL: Mock '{self._name}' called. ID: {id(self)}")
        # print(
        #     f"DEBUG_MANUAL_MOCK_CALL:   _side_effect: {self._side_effect}, type: {type(self._side_effect)}"
        # )
        # print(
        #     f"DEBUG_MANUAL_MOCK_CALL:   _return_value: {self._return_value}, type: {type(self._return_value)}"
        # )
        # is_side_effect_callable = callable(self._side_effect) and not isinstance(
        #     self._side_effect, Exception
        # )
        # print(
        #     f"DEBUG_MANUAL_MOCK_CALL:   is_side_effect_callable: {is_side_effect_callable}"
        # )
        # End DEBUG PRINT

        if self._side_effect:
            if callable(self._side_effect) and not isinstance(
                self._side_effect, Exception
            ):
                return self._side_effect(*args, **kwargs)
            elif isinstance(self._side_effect, Exception):
                raise self._side_effect
            return self._side_effect
        return self._return_value

    def __getattr__(self, name):
        if name not in self._children:
            # Ensure child mock names are also explicitly strings
            child_name_str = str(name) if name is not None else "child"
            parent_name_str = (
                str(self._name) if self._name is not None else "ManualMock"
            )
            # Propagate track_calls setting to children, or default to True if parent was not specific
            parent_track_calls = getattr(self, "_track_calls", True)
            child_mock = ManualMock(
                name=f"{parent_name_str}.{child_name_str}",
                track_calls=parent_track_calls,
            )
            self._children[name] = child_mock
            return child_mock
        return self._children[name]

    def __setattr__(self, name, value):
        if name == "return_value":
            super().__setattr__("_return_value", value)
        elif name == "side_effect":
            super().__setattr__("_side_effect", value)
        elif name.startswith("_") or name in [
            "call_args_list",
            "call_count",
            "_name",
            "_spec",
            "_children",
            "_track_calls",  # Added _track_calls here
            "__await__",  # Allow setting __await__ directly
        ]:
            super().__setattr__(name, value)
        else:
            # If assigning a ManualMock instance, assume it's a child mock.
            # Otherwise, it's a regular attribute.
            if isinstance(
                value, ManualMock
            ):  # This logic might need review if setting non-mock attributes that are also ManualMocks
                self._children[name] = value
            else:
                super().__setattr__(name, value)

    def assert_called_once(self):
        assert (
            self.call_count == 1
        ), f"{str(self._name)} expected to be called once, but was called {self.call_count} times."

    def assert_called_once_with(self, *args, **kwargs):
        self.assert_called_once()
        assert (
            len(self.call_args_list) == 1
        ), f"{str(self._name)} call_args_list has unexpected length."
        called_with = self.call_args_list[0]
        assert (
            called_with["args"] == args
        ), f"{str(self._name)} called with args {called_with['args']}, expected {args}."
        assert (
            called_with["kwargs"] == kwargs
        ), f"{str(self._name)} called with kwargs {called_with['kwargs']}, expected {kwargs}."

    def assert_not_called(self):
        assert (
            self.call_count == 0
        ), f"{str(self._name)} expected not to be called, but was called {self.call_count} times."

    def reset_mock(self):
        self.call_args_list = []
        self.call_count = 0
        self._children = {}
