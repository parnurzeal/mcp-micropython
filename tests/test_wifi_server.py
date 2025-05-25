import sys
import uasyncio  # For MicroPython environment

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")


# --- Mocking Stubs (Minimal) ---
class ManualMock:
    def __init__(self, spec=None, return_value=None, side_effect=None, name=None):
        self._name = name if name else "ManualMock"
        self._return_value = return_value
        self._side_effect = side_effect
        self.call_args_list = []
        self.call_count = 0
        self._spec = spec
        self._children = {}

    def __repr__(self):
        return f"<ManualMock name='{self._name}' id='{id(self)}'>"

    def __str__(self):
        return self.__repr__()

    # Changed to synchronous
    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args_list.append({"args": args, "kwargs": kwargs})
        if self._side_effect:
            # If side_effect is a function, it's called.
            # If it's an async function, the code under test must await its result.
            # If it's an exception, raise it.
            if callable(self._side_effect) and not isinstance(
                self._side_effect, Exception
            ):
                return self._side_effect(*args, **kwargs)
            elif isinstance(self._side_effect, Exception):
                raise self._side_effect
            return self._side_effect  # For other cases, like pre-computed values
        # If _return_value is a coroutine, the code under test must await it.
        return self._return_value

    def __getattr__(self, name):
        if name not in self._children:
            child_mock = ManualMock(name=f"{self._name}.{name}")
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
        ]:
            super().__setattr__(name, value)
        else:
            # For other public attributes, treat them as children if they are ManualMocks
            if isinstance(value, ManualMock):
                self._children[name] = value
            else:
                super().__setattr__(name, value)

    def assert_called_once(self):
        assert (
            self.call_count == 1
        ), f"{self._name} expected to be called once, but was called {self.call_count} times."

    def assert_called_once_with(self, *args, **kwargs):
        self.assert_called_once()
        assert (
            len(self.call_args_list) == 1
        ), f"{self._name} call_args_list has unexpected length."
        called_with = self.call_args_list[0]
        assert (
            called_with["args"] == args
        ), f"{self._name} called with args {called_with['args']}, expected {args}."
        assert (
            called_with["kwargs"] == kwargs
        ), f"{self._name} called with kwargs {called_with['kwargs']}, expected {kwargs}."

    def assert_not_called(self):
        assert (
            self.call_count == 0
        ), f"{self._name} expected not to be called, but was called {self.call_count} times."

    def reset_mock(self):
        self.call_args_list = []
        self.call_count = 0
        self._children = {}
        # self._return_value and self._side_effect are preserved by default


# --- Import necessary modules from mcp early ---
from mcp import (
    types,
)  # types is used by wifi_server, but also potentially by tests directly
from mcp.server_core import ServerCore
from mcp.registry import ToolRegistry, ResourceRegistry, PromptRegistry

# --- Globals for Mocks ---
_mock_uasyncio_module = ManualMock(name="uasyncio_module_mock")
_mock_network_module = ManualMock(name="network_module_mock")
_mock_ujson_module = ManualMock(name="ujson_module_mock")
_mock_microdot_module = ManualMock(name="microdot_module_mock")
_mock_microdot_app_instance = ManualMock(name="microdot_app_instance_mock")
_mock_microdot_response_class = ManualMock(name="microdot_response_class_mock")

mock_wlan_instance_for_tests = ManualMock(name="wlan_instance_for_tests")
mock_server_core_for_tests = ManualMock(name="server_core_for_tests", spec=ServerCore)
mock_server_core_for_tests.process_message_dict = ManualMock(
    name="server_core.process_message_dict"
)

tool_registry_for_tests = ManualMock(name="tool_registry_for_tests", spec=ToolRegistry)
resource_registry_for_tests = ManualMock(
    name="resource_registry_for_tests", spec=ResourceRegistry
)
prompt_registry_for_tests = ManualMock(
    name="prompt_registry_for_tests", spec=PromptRegistry
)


# --- Setup sys.modules Mocks ---
def setup_module_mocks():
    global _mock_uasyncio_module, _mock_network_module, _mock_ujson_module
    global _mock_microdot_module, _mock_microdot_app_instance, _mock_microdot_response_class
    global mock_wlan_instance_for_tests  # Ensure it's in scope

    # Resetting the main module mocks
    for mock_obj in [
        _mock_uasyncio_module,
        _mock_network_module,
        _mock_ujson_module,
        _mock_microdot_module,
        _mock_microdot_app_instance,
        _mock_microdot_response_class,
    ]:
        mock_obj.reset_mock()

    sys.modules["uasyncio"] = _mock_uasyncio_module
    sys.modules["network"] = _mock_network_module
    sys.modules["ujson"] = _mock_ujson_module
    sys.modules["microdot"] = _mock_microdot_module

    # For async functions/methods mocked by ManualMock, their _return_value should be a coroutine
    # if the code under test `await`s the result of `mocked_async_func()`.
    # The ManualMock.__call__ itself is now sync.
    async def _dummy_coro(*args, **kwargs):
        return None

    _mock_uasyncio_module.sleep = ManualMock(name="uasyncio.sleep")
    _mock_uasyncio_module.sleep._return_value = (
        _dummy_coro()
    )  # So `await uasyncio.sleep()` works

    _mock_uasyncio_module.create_task = ManualMock(
        name="uasyncio.create_task",
        side_effect=lambda coro: coro,  # Returns the coroutine itself
    )
    # Make sure the returned coroutine from create_task also has a cancel if needed by tests
    # For now, this simple side_effect is kept. If tasks need actual cancellation, this mock needs enhancement.
    # Example:
    # def create_task_side_effect(coro):
    #   task = ManualMock(name="mocked_task")
    #   task.coro = coro # store it for inspection if needed
    #   task.cancel = ManualMock(name="task.cancel")
    #   return task
    # _mock_uasyncio_module.create_task.side_effect = create_task_side_effect

    _mock_uasyncio_module.CancelledError = (
        uasyncio.CancelledError  # Use real CancelledError for type checks
    )

    _mock_network_module.STA_IF = "STA_IF_mock_value"
    wlan_factory_mock = _mock_network_module.WLAN  # Get/create child mock
    wlan_factory_mock._name = "network.WLAN_factory"
    wlan_factory_mock.return_value = mock_wlan_instance_for_tests

    _mock_ujson_module.dumps = ManualMock(
        name="ujson.dumps", side_effect=lambda x: str(x)
    )
    _mock_ujson_module.loads = ManualMock(
        name="ujson.loads",
        side_effect=lambda x: eval(x) if isinstance(x, (str, bytes)) else x,
    )

    _mock_microdot_module.Microdot = ManualMock(
        name="MicrodotClass", return_value=_mock_microdot_app_instance
    )
    _mock_microdot_module.Response = _mock_microdot_response_class


# Call setup_module_mocks once at import time
setup_module_mocks()

# --- Import the module to be tested (wifi_server) ---
from mcp import wifi_server  # This will now use the mocked sys.modules


# --- Test Helper Functions ---
def _run_async(coro):
    return uasyncio.get_event_loop().run_until_complete(coro)


def reset_test_specific_mocks():
    global mock_wlan_instance_for_tests, mock_server_core_for_tests
    global _mock_network_module, _mock_microdot_app_instance, _mock_microdot_response_class
    global _mock_uasyncio_module  # Added for _dummy_coro

    async def _dummy_coro(*args, **kwargs):
        return None

    mock_wlan_instance_for_tests.reset_mock()
    mock_wlan_instance_for_tests.ifconfig = ManualMock(
        name="wlan.ifconfig", return_value=("192.168.1.100", "", "", "")
    )
    mock_wlan_instance_for_tests.status = ManualMock(name="wlan.status", return_value=3)
    mock_wlan_instance_for_tests.active = ManualMock(name="wlan.active")
    mock_wlan_instance_for_tests.connect = ManualMock(name="wlan.connect")

    _mock_network_module.WLAN.reset_mock()
    _mock_network_module.WLAN.return_value = mock_wlan_instance_for_tests

    mock_server_core_for_tests.reset_mock()
    mock_server_core_for_tests.process_message_dict = ManualMock(
        name="server_core.process_message_dict"
    )
    # If process_message_dict is awaited, its return_value should be a coroutine
    mock_server_core_for_tests.process_message_dict._return_value = _dummy_coro()

    _mock_microdot_app_instance.reset_mock()
    _mock_microdot_app_instance.route = ManualMock(name="app.route")
    # Make the route decorator mock return the decorated function
    _mock_microdot_app_instance.route.side_effect = lambda path, methods=None: (
        lambda fn_to_decorate: fn_to_decorate
    )
    _mock_microdot_app_instance.start_server = ManualMock(name="app.start_server")
    _mock_microdot_app_instance.start_server._return_value = (
        _dummy_coro()
    )  # For `await app.start_server`
    _mock_microdot_app_instance.shutdown = ManualMock(name="app.shutdown")

    _mock_microdot_response_class.reset_mock()

    # Configure the Response class mock to return a mock instance with body/status_code
    def _response_mock_factory(body_arg, status_code_arg=200, headers_arg=None):
        # This factory creates what a `Response()` call would return.
        # The TestClient will then interact with this returned object.
        # The real microdot.Response object has .body, .status_code, .headers
        mock_resp_instance = ManualMock(name="mocked_response_instance")

        # Microdot's Response class can take (body, status, headers) or (body, headers) or just body
        # It also handles dict/list for body by converting to JSON and setting content-type.
        # Our mock factory needs to be simpler.

        # If body_arg is a dict/list, TestClient expects it to be JSON.
        # The actual microdot.Response would serialize it. Our mock_resp_instance
        # might just store it as is, and TestClient's .json property would work.
        mock_resp_instance.body = body_arg  # Store as is, TestClient might try to decode if bytes or use .json if dict
        mock_resp_instance.status_code = status_code_arg
        mock_resp_instance.headers = headers_arg if headers_arg is not None else {}

        # If body is dict/list, Microdot sets content-type to application/json
        if isinstance(body_arg, (dict, list)):
            mock_resp_instance.headers["Content-Type"] = "application/json"
        elif "Content-Type" not in mock_resp_instance.headers:
            mock_resp_instance.headers["Content-Type"] = "text/plain"  # A default

        return mock_resp_instance

    _mock_microdot_response_class.side_effect = _response_mock_factory

    # Also reset the Microdot factory mock itself
    if hasattr(_mock_microdot_module, "Microdot") and isinstance(
        _mock_microdot_module.Microdot, ManualMock
    ):
        _mock_microdot_module.Microdot.reset_mock()

    # Reset uasyncio sleep return value for awaitability
    _mock_uasyncio_module.sleep._return_value = _dummy_coro()


# --- Test Functions ---
async def test_wifi_connection_success_and_server_start_attempt():
    print("Running test_wifi_connection_success_and_server_start_attempt...")
    reset_test_specific_mocks()

    original_server_core = wifi_server.ServerCore
    wifi_server.ServerCore = ManualMock(
        name="PatchedServerCore", return_value=mock_server_core_for_tests
    )

    server_coro = wifi_server.wifi_mcp_server(
        tool_registry_for_tests,
        resource_registry_for_tests,
        prompt_registry_for_tests,
        "test_ssid",
        "test_password",
    )
    _run_async(server_coro)

    _mock_network_module.WLAN.assert_called_once_with(_mock_network_module.STA_IF)
    mock_wlan_instance_for_tests.active.assert_called_once_with(True)
    mock_wlan_instance_for_tests.connect.assert_called_once_with(
        "test_ssid", "test_password"
    )

    wifi_server.ServerCore.assert_called_once_with(
        tool_registry_for_tests, resource_registry_for_tests, prompt_registry_for_tests
    )

    _mock_microdot_module.Microdot.assert_called_once()
    _mock_microdot_app_instance.route.assert_called_once_with("/", methods=["POST"])
    _mock_microdot_app_instance.start_server.assert_called_once_with(
        host="0.0.0.0", port=wifi_server.DEFAULT_MCP_PORT, debug=False
    )

    wifi_server.ServerCore = original_server_core
    print("test_wifi_connection_success_and_server_start_attempt PASSED")


async def test_wifi_connection_failure():
    print("Running test_wifi_connection_failure...")
    reset_test_specific_mocks()
    # Access status via its mock object directly
    mock_wlan_instance_for_tests.status._return_value = 1

    original_server_core = wifi_server.ServerCore
    wifi_server.ServerCore = ManualMock(
        name="PatchedServerCoreNeverCalled", return_value=mock_server_core_for_tests
    )

    await wifi_server.wifi_mcp_server(
        tool_registry_for_tests,
        resource_registry_for_tests,
        prompt_registry_for_tests,
        "test_ssid",
        "test_password",
    )

    _mock_network_module.WLAN.assert_called_once()
    mock_wlan_instance_for_tests.connect.assert_called_once()
    wifi_server.ServerCore.assert_not_called()
    _mock_microdot_module.Microdot.assert_not_called()
    _mock_microdot_app_instance.start_server.assert_not_called()

    wifi_server.ServerCore = original_server_core
    print("test_wifi_connection_failure PASSED")


async def test_handle_mcp_request_valid_json_rpc_call():
    print("Running test_handle_mcp_request_valid_json_rpc_call...")
    reset_test_specific_mocks()

    if "microdot.test_client" in sys.modules and isinstance(
        sys.modules["microdot.test_client"], ManualMock
    ):
        del sys.modules["microdot.test_client"]
    from microdot.test_client import TestClient

    app = wifi_server.create_mcp_microdot_app(mock_server_core_for_tests)
    client = TestClient(app)

    request_payload = {
        "jsonrpc": "2.0",
        "method": "test_method",
        "params": {"foo": "bar"},
        "id": 1,
    }
    expected_response_payload = {"jsonrpc": "2.0", "result": "success", "id": 1}

    # process_message_dict is async, so its mock's return_value should be a coroutine
    async def mock_process_message_dict_coro(*args, **kwargs):
        return expected_response_payload

    mock_server_core_for_tests.process_message_dict._return_value = (
        mock_process_message_dict_coro()
    )

    actual_response_from_test_client = await client.post("/", body=request_payload)

    mock_server_core_for_tests.process_message_dict.assert_called_once_with(
        request_payload
    )
    assert actual_response_from_test_client.status_code == 200
    assert actual_response_from_test_client.json == expected_response_payload
    print("test_handle_mcp_request_valid_json_rpc_call PASSED")


async def test_handle_mcp_request_notification():
    print("Running test_handle_mcp_request_notification...")
    reset_test_specific_mocks()
    if "microdot.test_client" in sys.modules and isinstance(
        sys.modules["microdot.test_client"], ManualMock
    ):
        del sys.modules["microdot.test_client"]
    from microdot.test_client import TestClient

    app = wifi_server.create_mcp_microdot_app(mock_server_core_for_tests)
    client = TestClient(app)
    notification_payload = {
        "jsonrpc": "2.0",
        "method": "notify_event",
        "params": {"data": "event1"},
    }

    # process_message_dict is async, its return_value should be a coroutine
    async def mock_process_message_dict_coro_none(*args, **kwargs):
        return None  # For notifications, it might effectively return/resolve to None

    mock_server_core_for_tests.process_message_dict._return_value = (
        mock_process_message_dict_coro_none()
    )

    actual_response_from_test_client = await client.post("/", body=notification_payload)
    mock_server_core_for_tests.process_message_dict.assert_called_once_with(
        notification_payload
    )
    assert actual_response_from_test_client.status_code == 204
    print("test_handle_mcp_request_notification PASSED")


async def test_handle_mcp_request_invalid_json():
    print("Running test_handle_mcp_request_invalid_json...")
    reset_test_specific_mocks()
    if "microdot.test_client" in sys.modules and isinstance(
        sys.modules["microdot.test_client"], ManualMock
    ):
        del sys.modules["microdot.test_client"]
    from microdot.test_client import TestClient

    app = wifi_server.create_mcp_microdot_app(mock_server_core_for_tests)
    client = TestClient(app)
    invalid_json_body = b'{"jsonrpc": "2.0", "method": "test", "id": 1'
    actual_response_from_test_client = await client.post(
        "/", body=invalid_json_body, headers={"Content-Type": "application/json"}
    )
    mock_server_core_for_tests.process_message_dict.assert_not_called()
    assert actual_response_from_test_client.status_code == 400
    response_json = actual_response_from_test_client.json
    assert response_json is not None
    assert response_json.get("error", {}).get("code") == -32700
    assert "Invalid or empty JSON received" in response_json.get("error", {}).get(
        "message", ""
    )
    print("test_handle_mcp_request_invalid_json PASSED")


async def test_handle_mcp_request_invalid_mcp_request_object():
    print("Running test_handle_mcp_request_invalid_mcp_request_object...")
    reset_test_specific_mocks()
    if "microdot.test_client" in sys.modules and isinstance(
        sys.modules["microdot.test_client"], ManualMock
    ):
        del sys.modules["microdot.test_client"]
    from microdot.test_client import TestClient

    app = wifi_server.create_mcp_microdot_app(mock_server_core_for_tests)
    client = TestClient(app)
    invalid_mcp_payload = {"jsonrpc": "2.0", "id": 1}
    actual_response_from_test_client = await client.post("/", body=invalid_mcp_payload)
    mock_server_core_for_tests.process_message_dict.assert_not_called()
    assert actual_response_from_test_client.status_code == 200
    response_json = actual_response_from_test_client.json
    assert response_json is not None
    assert response_json.get("error", {}).get("code") == -32600
    assert "The JSON sent is not a valid Request object" in response_json.get(
        "error", {}
    ).get("message", "")
    print("test_handle_mcp_request_invalid_mcp_request_object PASSED")


# --- Test Runner ---
async def run_wifi_server_tests():
    """Runs all tests in this module."""
    print(">>> Running Wifi Server Tests <<<")
    await test_wifi_connection_success_and_server_start_attempt()
    await test_wifi_connection_failure()
    await test_handle_mcp_request_valid_json_rpc_call()
    await test_handle_mcp_request_notification()
    await test_handle_mcp_request_invalid_json()
    await test_handle_mcp_request_invalid_mcp_request_object()
    print(">>> Wifi Server Tests Completed <<<")


if __name__ == "__main__":
    try:
        uasyncio.run(run_wifi_server_tests())
        print("ALL WIFI SERVER TESTS PASSED (when run directly)")
    except Exception as e:
        print(f"A test failed when run directly: {type(e).__name__}: {e}")
