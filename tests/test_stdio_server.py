import unittest
import asyncio
import uio
import json
import sys

sys.path.insert(0, ".")

from mcp import stdio_server as mcp_stdio_server
from mcp import types as mcp_types


# --- Mock Reader/Writer inspired by tinymqtt tests ---
class MockStdioReader:
    def __init__(self, data_bytes):
        self.data = data_bytes
        self.pos = 0

    async def readline(self):  # Kept async as it was in the working version
        if self.pos >= len(self.data):
            return b""  # EOF
        try:
            newline_idx = self.data.index(b"\n", self.pos)
            line = self.data[self.pos : newline_idx + 1]
            self.pos = newline_idx + 1
        except ValueError:  # No newline found
            line = self.data[self.pos :]
            self.pos = len(self.data)
        return line

    async def readexactly(self, n):
        if self.pos >= len(self.data):
            if n == 0:
                return b""
            raise EOFError()
        end_pos = min(self.pos + n, len(self.data))
        chunk = self.data[self.pos : end_pos]
        self.pos = end_pos
        if len(chunk) < n:
            raise EOFError()
        return chunk

    async def read(self, n):
        if self.pos >= len(self.data):
            return b""
        end_pos = min(self.pos + n, len(self.data))
        chunk = self.data[self.pos : end_pos]
        self.pos = end_pos
        return chunk

    def close(self):
        pass


class MockStdioWriter:
    CLASS_WRITTEN_CHUNKS = []

    def __init__(self):
        MockStdioWriter.CLASS_WRITTEN_CHUNKS.clear()

    def write(self, buf):  # Synchronous
        MockStdioWriter.CLASS_WRITTEN_CHUNKS.append(buf)
        return len(buf)

    async def drain(self):  # Asynchronous
        pass

    def close(self):
        pass

    def get_written_data_bytes(self):
        return b"".join(MockStdioWriter.CLASS_WRITTEN_CHUNKS)


# --- End Mock Reader/Writer ---


class TestStdioServer(unittest.TestCase):

    def run_server_with_input(self, input_str):
        mock_reader = MockStdioReader(input_str.encode("utf-8"))
        mock_writer = MockStdioWriter()

        async def _run_server_task():
            await mcp_stdio_server(custom_reader=mock_reader, custom_writer=mock_writer)
            return mock_writer.get_written_data_bytes(), list(
                MockStdioWriter.CLASS_WRITTEN_CHUNKS
            )

        output_data_bytes = b""
        raw_chunks = []
        try:
            MockStdioWriter.CLASS_WRITTEN_CHUNKS.clear()
            output_data_bytes, raw_chunks = asyncio.run(_run_server_task())
        except Exception as e:
            print(f"Exception during server run: {e}", file=sys.stderr)

        output_lines_str = output_data_bytes.decode("utf-8").strip().split("\n")
        output_lines_str = [line for line in output_lines_str if line]

        parsed_responses = []
        for line in output_lines_str:
            try:
                parsed_responses.append(json.loads(line))
            except ValueError:
                # Optionally, keep this print if you want to know about parse failures
                # print(f"DEBUG: Failed to parse JSON line: {line!r}", file=sys.stderr)
                pass  # Or raise an error, or return an empty list to fail the test
        return parsed_responses

    def test_echo_method(self):
        params = {"text": "hello world"}
        request_id = 1
        request_json_str = (
            json.dumps(
                {"jsonrpc": "2.0", "method": "echo", "params": params, "id": request_id}
            )
            + "\n"
        )
        responses = self.run_server_with_input(request_json_str)
        self.assertEqual(len(responses), 1)
        expected_response = mcp_types.create_success_response(request_id, params)
        self.assertEqual(responses[0], expected_response)

    def test_add_method_success(self):
        params = [10, 5]
        request_id = 2
        request_json_str = (
            json.dumps(
                {"jsonrpc": "2.0", "method": "add", "params": params, "id": request_id}
            )
            + "\n"
        )
        responses = self.run_server_with_input(request_json_str)
        self.assertEqual(len(responses), 1)
        expected_response = mcp_types.create_success_response(request_id, 15)
        self.assertEqual(responses[0], expected_response)

    def test_add_method_invalid_params_type(self):
        params = ["a", 5]
        request_id = 3
        request_json_str = (
            json.dumps(
                {"jsonrpc": "2.0", "method": "add", "params": params, "id": request_id}
            )
            + "\n"
        )
        responses = self.run_server_with_input(request_json_str)
        self.assertEqual(len(responses), 1)
        expected_response = mcp_types.create_error_response(
            request_id, -32602, "Invalid params", "Parameters must be numbers"
        )
        self.assertEqual(responses[0], expected_response)

    def test_method_not_found(self):
        request_id = 4
        method_name = "nonexistent_method"
        request_json_str = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": method_name,
                    "params": {},
                    "id": request_id,
                }
            )
            + "\n"
        )
        responses = self.run_server_with_input(request_json_str)
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["id"], request_id)
        self.assertEqual(responses[0]["error"]["code"], -32601)
        self.assertEqual(responses[0]["error"]["message"], "Method not found")
        self.assertTrue(
            f"Method '{method_name}' not implemented" in responses[0]["error"]["data"]
        )

    def test_invalid_json_input(self):
        request_json_str = "this is not json\n"
        responses = self.run_server_with_input(request_json_str)
        self.assertEqual(len(responses), 1)
        expected_response = mcp_types.create_error_response(
            None, -32700, "Parse error", "Invalid JSON received"
        )
        self.assertEqual(responses[0], expected_response)


if __name__ == "__main__":
    unittest.main()
