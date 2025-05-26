# tests/test_stdio_transport.py
import sys
import asyncio
import json

# Ensure the project root is in the path
if "." not in sys.path:
    sys.path.insert(0, ".")

from mcp.stdio_server import stdio_server
from tests.common_test_utils import (
    setup_test_registry,
    setup_common_resource_registry,
    setup_common_prompt_registry,
)

# --- stdio_server main loop Tests (for notifications and basic req/resp flow) ---


class MockStreamReader:
    def __init__(self, lines_to_read):
        self.lines = [line.encode("utf-8") + b"\n" for line in lines_to_read]
        self.pos = 0

    async def readline(self):
        if self.pos < len(self.lines):
            line = self.lines[self.pos]
            self.pos += 1
            return line
        return b""  # Simulate EOF


class MockStreamWriter:
    def __init__(self):
        self.written_data = bytearray()

    def write(self, data):
        self.written_data.extend(data)

    async def drain(self):
        pass  # No-op for mock

    def get_written_str(self):
        return self.written_data.decode("utf-8")


async def test_stdio_server_handles_notification():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    notification_msg_str = json.dumps(
        {"jsonrpc": "2.0", "method": "some/notification", "params": {"data": "test"}}
    )
    reader = MockStreamReader([notification_msg_str, ""])
    writer = MockStreamWriter()

    await stdio_server(
        tool_registry=tool_reg,
        resource_registry=res_reg,
        prompt_registry=prompt_reg,
        custom_reader=reader,
        custom_writer=writer,
    )

    written_output = writer.get_written_str()
    assert (
        written_output == ""
    ), f"Expected no output for notification, but got: {written_output}"
    print("test_stdio_server_handles_notification PASSED")


async def test_stdio_server_sends_response_for_request():
    tool_reg = setup_test_registry()
    res_reg = setup_common_resource_registry()
    prompt_reg = setup_common_prompt_registry()
    request_msg_str = json.dumps(
        {"jsonrpc": "2.0", "method": "initialize", "id": "init-req-1"}
    )
    reader = MockStreamReader([request_msg_str, ""])
    writer = MockStreamWriter()

    await stdio_server(
        tool_registry=tool_reg,
        resource_registry=res_reg,
        prompt_registry=prompt_reg,
        custom_reader=reader,
        custom_writer=writer,
    )

    written_output = writer.get_written_str().strip()
    assert written_output != "", "Expected output for a request, but got none."
    try:
        response_json = json.loads(written_output)
        assert response_json.get("id") == "init-req-1"
        assert "result" in response_json
    except ValueError:
        assert False, f"Output was not valid JSON: {written_output}"
    print("test_stdio_server_sends_response_for_request PASSED")


async def run_stdio_transport_tests():
    print("\n--- Running stdio_server Loop Tests ---")
    await test_stdio_server_handles_notification()
    await test_stdio_server_sends_response_for_request()
    print("--- stdio_server Loop Tests Complete ---")


if __name__ == "__main__":
    asyncio.run(run_stdio_transport_tests())
