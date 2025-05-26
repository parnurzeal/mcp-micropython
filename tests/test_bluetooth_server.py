# tests/test_bluetooth_server.py

import sys
import unittest

# Ensure the project root is in the path if this file is run directly
if "." not in sys.path:  # If CWD is tests/
    sys.path.insert(0, "..")
elif "tests" in sys.path[0]:  # If CWD is project root and tests/ is in path
    pass
else:  # If CWD is project root and tests/ not in path
    sys.path.insert(0, "tests")

from common_test_utils import ManualMock  # Used for MockServerCore

# asyncio is typically uasyncio in MicroPython.
# If mock_bootstrap.py is used by the test runner, it might provide a CPython-compatible asyncio.
# For native MicroPython execution, this will be the system's uasyncio.
import asyncio
import json

# This test script is intended to run in a MicroPython environment.
# It will use the native `bluetooth` and `aioble` modules.
import bluetooth  # Native MicroPython bluetooth
import aioble  # Native MicroPython aioble

from mcp.bluetooth_server import (
    BluetoothMCPServer,
    # bluetooth_mcp_server, # Main entry point, not directly tested here, but via class
    _NUS_SERVICE_UUID,
    _NUS_RX_CHAR_UUID,
    _NUS_TX_CHAR_UUID,
)
from mcp.server_core import ServerCore


class MockServerCore(ServerCore):
    def __init__(self):
        self.last_processed_message = None
        self.response_to_send = None
        super().__init__(
            tool_registry=None, resource_registry=None, prompt_registry=None
        )

    async def process_message_dict(self, message_dict):
        self.last_processed_message = message_dict
        response = (
            self.response_to_send
            if self.response_to_send
            else {
                "jsonrpc": "2.0",
                "result": {"received": message_dict},
                "id": message_dict.get("id"),
            }
        )
        return response


class TestBluetoothMCPServer(unittest.TestCase):

    def setUp(self):
        self.server_core = MockServerCore()
        self.ble_mcp_server = BluetoothMCPServer(
            self.server_core,
            device_name="TestMCPBLE",  # Ensure this name is unique if running on live BLE
        )
        ble = bluetooth.BLE()
        if ble.active():
            ble.active(False)
        ble.active(True)

    async def tearDown(self):
        if self.ble_mcp_server._is_running:
            print("Teardown: Server was running, stopping it...")
            await self.ble_mcp_server.stop()
        print("Teardown: Calling aioble.stop()...")
        aioble.stop()
        await asyncio.sleep(0.1)  # Short pause after operations

    def test_01_initialization_native(self):
        self.assertIsNotNone(
            self.ble_mcp_server._nus_service, "NUS Service object not created"
        )
        self.assertIsInstance(
            self.ble_mcp_server._nus_service,
            aioble.Service,
            "Nus service is not an aioble.Service",
        )
        self.assertEqual(self.ble_mcp_server._nus_service.uuid, _NUS_SERVICE_UUID)

        self.assertIsNotNone(
            self.ble_mcp_server._tx_char, "TX Characteristic object not created"
        )
        self.assertIsInstance(
            self.ble_mcp_server._tx_char,
            aioble.Characteristic,
            "TX char is not an aioble.Characteristic",
        )
        self.assertEqual(self.ble_mcp_server._tx_char.service.uuid, _NUS_SERVICE_UUID)
        self.assertEqual(self.ble_mcp_server._tx_char.uuid, _NUS_TX_CHAR_UUID)

        self.assertIsNotNone(
            self.ble_mcp_server._rx_char, "RX Characteristic object not created"
        )
        self.assertIsInstance(
            self.ble_mcp_server._rx_char,
            aioble.Characteristic,
            "RX char is not an aioble.Characteristic",
        )
        self.assertEqual(self.ble_mcp_server._rx_char.service.uuid, _NUS_SERVICE_UUID)
        self.assertEqual(self.ble_mcp_server._rx_char.uuid, _NUS_RX_CHAR_UUID)
        print(
            "TestBluetoothMCPServer.test_01_initialization_native PASSED (structure check)"
        )

    async def _run_server_and_client(
        self, client_task_coro, server_instance, server_name="TestMCPBLE"
    ):
        ble = bluetooth.BLE()
        if not ble.active():
            print("Helper: Activating BLE...")
            ble.active(True)
            await asyncio.sleep(0.2)

        server_task = asyncio.create_task(server_instance.start())
        client_task = asyncio.create_task(client_task_coro(server_name))

        try:
            await asyncio.wait_for(client_task, timeout=30)
        except asyncio.TimeoutError:
            self.fail(
                f"Client task timed out after 30s. Server running: {server_instance._is_running}"
            )
        except Exception as e_client:
            self.fail(f"Client task failed: {type(e_client).__name__}: {e_client}")
        finally:
            print("Helper: Client task finished or timed out. Stopping server...")
            if server_instance._is_running:
                await server_instance.stop()

            if not server_task.done():
                print("Helper: Waiting for server task to complete after stop...")
                try:
                    await asyncio.wait_for(server_task, timeout=5)
                except asyncio.TimeoutError:
                    print("Helper: Server task did not complete on stop, cancelling.")
                    server_task.cancel()
                except asyncio.CancelledError:
                    print("Helper: Server task was cancelled by stop().")

            if not client_task.done():
                print("Helper: Cancelling client task (if not already done)...")
                client_task.cancel()
                try:
                    await client_task
                except asyncio.CancelledError:
                    print("Helper: Client task successfully cancelled.")
            print("Helper: _run_server_and_client finished.")

    async def client_task_connect_disconnect(self, server_name):
        print(f"Client: Starting scan for '{server_name}'...")
        device = None
        connection = None
        try:
            async with aioble.scan(
                duration_ms=5000, interval_us=30000, window_us=30000, active=True
            ) as scanner:
                async for result in scanner:
                    if (
                        result.name() == server_name
                        and _NUS_SERVICE_UUID in result.services()
                    ):
                        device = result.device
                        print(
                            f"Client: Found server: {device} Name: '{result.name()}' RSSI: {result.rssi}"
                        )
                        break
            self.assertIsNotNone(
                device, f"Client: Server '{server_name}' not found during scan."
            )
            if not device:
                return

            print(f"Client: Connecting to {device}...")
            connection = await device.connect(timeout_ms=10000)
            self.assertIsNotNone(
                connection, "Client: Failed to connect (connection object is None)."
            )
            if not connection:
                return

            print(f"Client: Connected to {connection.device}. Checking server state...")
            await asyncio.sleep(0.2)
            self.assertTrue(
                len(self.ble_mcp_server._connections) > 0,
                "Server did not register the connection.",
            )

            print("Client: Disconnecting...")
            await connection.disconnect(timeout_ms=5000)
            connection = None
            print("Client: Disconnected by client.")

            await asyncio.sleep(0.5)
            self.assertEqual(
                len(self.ble_mcp_server._connections),
                0,
                "Server did not clear connection after client disconnect.",
            )
        except Exception as e:
            self.fail(f"Client (connect_disconnect) error: {type(e).__name__}: {e}")
        finally:
            if connection and connection.is_connected():
                print("Client (connect_disconnect) finally: Disconnecting...")
                await connection.disconnect(timeout_ms=1000)

    async def test_02_connect_disconnect_native(self):
        await self._run_server_and_client(
            self.client_task_connect_disconnect,
            self.ble_mcp_server,
            server_name="TestMCPBLE",
        )
        print("TestBluetoothMCPServer.test_02_connect_disconnect_native PASSED")

    async def client_task_send_receive(self, server_name):
        print(f"Client: Starting scan for send/receive test for '{server_name}'...")
        device = None
        connection = None
        try:
            async with aioble.scan(
                duration_ms=5000, interval_us=30000, window_us=30000, active=True
            ) as scanner:
                async for result in scanner:
                    if (
                        result.name() == server_name
                        and _NUS_SERVICE_UUID in result.services()
                    ):
                        device = result.device
                        print(f"Client: Found server {result.name()}")
                        break
            self.assertIsNotNone(
                device, f"Client: Server '{server_name}' not found for send/receive."
            )
            if not device:
                return

            connection = await device.connect(timeout_ms=10000)
            self.assertIsNotNone(
                connection, "Client: Failed to connect for send/receive."
            )
            if not connection:
                return

            print("Client: Discovering NUS service...")
            nus_service = await connection.service(_NUS_SERVICE_UUID, timeout_ms=5000)
            self.assertIsNotNone(nus_service, "Client: NUS service not found.")

            rx_char = await nus_service.characteristic(
                _NUS_RX_CHAR_UUID, timeout_ms=5000
            )
            self.assertIsNotNone(rx_char, "Client: NUS RX characteristic not found.")

            tx_char = await nus_service.characteristic(
                _NUS_TX_CHAR_UUID, timeout_ms=5000
            )
            self.assertIsNotNone(tx_char, "Client: NUS TX characteristic not found.")

            print("Client: Subscribing to TX characteristic...")
            await tx_char.subscribe(notify=True)

            test_msg_id = "aioble_native_echo"
            client_message_str = f'{{"jsonrpc": "2.0", "method": "echo_native", "params": {{"data": "echo_this"}}, "id": "{test_msg_id}"}}'
            client_message_bytes = (client_message_str + "\n").encode("utf-8")

            expected_response_payload = {"echo_reply": "echo_this_native_world"}
            self.server_core.response_to_send = {
                "jsonrpc": "2.0",
                "result": expected_response_payload,
                "id": test_msg_id,
            }
            expected_response_json_str = json.dumps(self.server_core.response_to_send)

            print(f"Client: Writing to RX characteristic: {client_message_bytes!r}")
            await rx_char.write(client_message_bytes, response=False)

            print("Client: Waiting for notification on TX characteristic...")
            received_data_bytes = await tx_char.notified(timeout_ms=10000)
            self.assertIsNotNone(
                received_data_bytes, "Client: Did not receive notification."
            )

            if received_data_bytes:
                received_data_str = received_data_bytes.decode("utf-8").strip()
                print(f"Client: Received notification: {received_data_str!r}")
                self.assertEqual(received_data_str, expected_response_json_str)

            self.assertIsNotNone(
                self.server_core.last_processed_message,
                "ServerCore did not process message",
            )
            if self.server_core.last_processed_message:
                self.assertEqual(
                    self.server_core.last_processed_message.get("id"), test_msg_id
                )
                self.assertEqual(
                    self.server_core.last_processed_message.get("method"), "echo_native"
                )
        except Exception as e_test_logic:
            self.fail(
                f"Client (send_receive) error: {type(e_test_logic).__name__}: {e_test_logic}"
            )
        finally:
            if connection and connection.is_connected():
                print("Client (send_receive) finally: Disconnecting...")
                await connection.disconnect(timeout_ms=2000)
            print("Client: Send/receive task finished.")

    async def test_03_send_receive_native(self):
        await self._run_server_and_client(
            self.client_task_send_receive, self.ble_mcp_server, server_name="TestMCPBLE"
        )
        print("TestBluetoothMCPServer.test_03_send_receive_native PASSED")


async def run_bluetooth_server_tests():
    print("\n--- Running Bluetooth Server Tests (Native MicroPython) ---")
    test_suite = TestBluetoothMCPServer()

    # Test 01 (sync)
    test_suite.setUp()
    test_suite.test_01_initialization_native()
    await test_suite.tearDown()

    # Test 02 (async)
    test_suite.setUp()
    await test_suite.test_02_connect_disconnect_native()
    await test_suite.tearDown()

    # Test 03 (async)
    test_suite.setUp()
    await test_suite.test_03_send_receive_native()
    await test_suite.tearDown()

    print("--- Bluetooth Server Tests (Native MicroPython) Complete ---")


if __name__ == "__main__":
    try:
        asyncio.run(run_bluetooth_server_tests())
        print("ALL BLUETOOTH SERVER NATIVE TESTS PASSED (when run directly)")
    except Exception as e:
        print(f"A bluetooth server native test failed: {type(e).__name__}: {e}")
