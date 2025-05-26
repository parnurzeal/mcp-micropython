# mcp/bluetooth_server.py

import asyncio
import bluetooth  # Still needed for UUID
import json
import time  # For logging/debugging (though aioble might reduce need for manual time)
import aioble  # Import aioble
from micropython import const  # Import const

from .server_core import ServerCore

# from .types import create_json_rpc_response # Will be needed for crafting responses

# Nordic UART Service (NUS) UUIDs - These remain the same
_NUS_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_NUS_RX_CHAR_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_NUS_TX_CHAR_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")

# Advertising interval
_ADV_INTERVAL_US = const(250000)  # From aioble example, can be adjusted


class BluetoothMCPServer:
    def __init__(self, server_core: ServerCore, device_name="PicoMCP-BLE"):
        self._server_core = server_core
        self._name = device_name

        # Create NUS service and characteristics using aioble
        self._nus_service = aioble.Service(_NUS_SERVICE_UUID)
        self._tx_char = aioble.Characteristic(
            self._nus_service, _NUS_TX_CHAR_UUID, read=True, notify=True
        )
        self._rx_char = aioble.Characteristic(
            self._nus_service,
            _NUS_RX_CHAR_UUID,
            write=True,
            capture=True,  # capture=True for written() to return data
        )
        # Register the service
        aioble.register_services(self._nus_service)

        self._connections = (
            {}
        )  # Store connection objects, keyed by conn_handle if needed, or just a set
        self._rx_buffer = (
            bytearray()
        )  # May still be useful for accumulating partial messages

        # _rx_event_placeholder and its associated debug prints are removed as it's no longer needed.
        # Data arrival is handled by awaiting self._rx_char.written() in _handle_connection.

        self._is_running = False
        self._advertising_task = None
        self._connection_handler_tasks = set()

        print(
            f"BluetoothMCPServer: Initialized using aioble. Advertising as '{self._name}'"
        )

    # _advertise method is removed, advertising is handled in the start/connection loop

    # _irq method is removed, replaced by aioble's async event handling

    async def _handle_connection(self, connection):
        print(f"BluetoothMCPServer: Central connected: {connection.device}")
        self._connections[connection.device] = (
            connection  # Or use connection object directly as key/value
        )
        try:
            # Handle disconnect
            disconnected_task = asyncio.create_task(
                connection.disconnected(timeout_ms=None)
            )  # Wait indefinitely

            while connection.is_connected():
                # Wait for data on RX characteristic
                try:
                    # Using characteristic.written() which is an awaitable
                    # The `capture=True` on RX characteristic makes `written()` return the data
                    _, data = await self._rx_char.written(
                        timeout_ms=1000
                    )  # Timeout to allow checking connection state
                    if data:
                        self._rx_buffer.extend(data)
                        print(f"BluetoothMCPServer: Received data: {data}")
                        # Process buffer immediately or signal another task
                        await self._process_buffered_data(connection)

                except asyncio.TimeoutError:
                    # No data received, loop and check connection status
                    pass
                except aioble.DeviceDisconnectedError:
                    print(
                        f"BluetoothMCPServer: Device disconnected during write wait: {connection.device}"
                    )
                    break  # Exit while loop

                if disconnected_task.done():
                    print(
                        f"BluetoothMCPServer: Disconnected task done for {connection.device}"
                    )
                    break

        except Exception as e:
            print(
                f"BluetoothMCPServer: Error in connection handler for {connection.device}: {e}"
            )
        finally:
            print(f"BluetoothMCPServer: Cleaning up connection for {connection.device}")
            if connection.device in self._connections:
                del self._connections[connection.device]
            if not disconnected_task.done():
                disconnected_task.cancel()

    async def _process_buffered_data(self, connection):
        # This method processes data from self._rx_buffer for a specific connection
        # and sends responses via that connection.
        # It's called after new data is received and added to self._rx_buffer.

        response_bytes = (
            None  # Initialize to avoid UnboundLocalError if no message processed
        )
        while b"\n" in self._rx_buffer:
            message_bytes, self._rx_buffer = self._rx_buffer.split(b"\n", 1)
            message_str = message_bytes.decode("utf-8").strip()
            if not message_str:
                continue

            print(f"BluetoothMCPServer: Processing message: {message_str}")
            try:
                message_dict = json.loads(message_str)
                response_dict = await self._server_core.process_message_dict(
                    message_dict
                )
                if response_dict:
                    response_str = json.dumps(response_dict)
                    # Ensure response also ends with a newline for the client
                    response_bytes = (response_str + "\n").encode("utf-8")
                else:
                    print("BluetoothMCPServer: No response from server_core")
                    response_bytes = None  # Explicitly set to None
                    continue
            except ValueError:
                print(f"BluetoothMCPServer: Invalid JSON received: {message_str}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None,
                }
                response_str = json.dumps(error_response)
                response_bytes = (response_str + "\n").encode("utf-8")
            except Exception as e:
                print(f"BluetoothMCPServer: Error processing message: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                    "id": None,  # Or try to extract ID from message_dict if available
                }
                response_str = json.dumps(error_response)
                response_bytes = (response_str + "\n").encode("utf-8")

            if response_bytes:
                print(
                    f"BluetoothMCPServer: Sending response via TX characteristic: {response_bytes[:100]}"
                )  # Log snippet
                try:
                    # Use aioble's characteristic notify
                    self._tx_char.notify(connection, response_bytes)
                except Exception as e_notify:
                    print(f"BluetoothMCPServer: Error sending notification: {e_notify}")
                response_bytes = None  # Reset for next message in buffer

        # No sleep here, this is called synchronously within _handle_connection's loop

    async def start(self):
        self._is_running = True
        print(f"BluetoothMCPServer: Starting. Will advertise as '{self._name}'.")

        # Main advertising and connection acceptance loop
        async def advertising_loop():
            while self._is_running:
                print("BluetoothMCPServer: Starting advertising...")
                try:
                    # Advertise and wait for a connection
                    # services=[_NUS_SERVICE_UUID] is important for NUS clients to find the device
                    async with await aioble.advertise(
                        _ADV_INTERVAL_US,
                        name=self._name,
                        services=[_NUS_SERVICE_UUID],
                        timeout_ms=None,  # Advertise indefinitely until connection or stop
                    ) as connection:
                        print(
                            f"BluetoothMCPServer: Connection from {connection.device}"
                        )
                        # Create a task to handle this connection
                        handler_task = asyncio.create_task(
                            self._handle_connection(connection)
                        )
                        self._connection_handler_tasks.add(handler_task)
                        # Optional: remove task from set when done (e.g. via callback)
                        # For now, _handle_connection removes from self._connections dict
                except asyncio.CancelledError:
                    print("BluetoothMCPServer: Advertising loop cancelled.")
                    break
                except Exception as e:
                    print(f"BluetoothMCPServer: Error in advertising loop: {e}")
                    # Potentially add a small delay before retrying advertising
                    await asyncio.sleep(
                        5
                    )  # Wait 5 seconds before trying to advertise again
            print("BluetoothMCPServer: Advertising loop finished.")

        self._advertising_task = asyncio.create_task(advertising_loop())

        # Keep server running by waiting for the advertising task
        # (or another mechanism if advertising_loop can exit under normal operation without stopping server)
        if self._advertising_task:
            try:
                await self._advertising_task
            except asyncio.CancelledError:
                print(
                    "BluetoothMCPServer: Main advertising task was cancelled during start."
                )

    async def stop(self):
        self._is_running = False
        print("BluetoothMCPServer: Stopping...")

        if self._advertising_task:
            print("BluetoothMCPServer: Cancelling advertising task...")
            self._advertising_task.cancel()
            try:
                await self._advertising_task  # Allow cancellation to complete
            except asyncio.CancelledError:
                print("BluetoothMCPServer: Advertising task successfully cancelled.")
            except Exception as e:
                print(
                    f"BluetoothMCPServer: Exception while awaiting cancelled advertising task: {e}"
                )

        active_connections = list(self._connections.values())
        for conn in active_connections:
            try:
                print(f"BluetoothMCPServer: Disconnecting {conn.device}...")
                await conn.disconnect(timeout_ms=1000)
            except Exception as e:
                print(f"BluetoothMCPServer: Error disconnecting {conn.device}: {e}")

        for task in list(self._connection_handler_tasks):
            if not task.done():
                print(
                    f"BluetoothMCPServer: Cancelling connection handler task {task}..."
                )
                task.cancel()
                try:
                    await task  # Allow cancellation to complete
                except asyncio.CancelledError:
                    print(
                        f"BluetoothMCPServer: Connection handler task {task} successfully cancelled."
                    )
                except Exception as e:
                    print(
                        f"BluetoothMCPServer: Exception while awaiting cancelled handler task {task}: {e}"
                    )
        self._connection_handler_tasks.clear()
        self._connections.clear()

        # aioble.stop() will be called in the main server function's finally block.
        print("BluetoothMCPServer: Class-level stop actions complete.")


# Main function to run the server (similar to stdio_server.py and wifi_server.py)
async def bluetooth_mcp_server(server_core: ServerCore, device_name="PicoMCP-BLE"):
    # It's good practice to activate BLE early if aioble doesn't do it.
    # However, aioble.advertise and aioble.scan typically handle activation.
    # If issues arise, uncommenting ble.active(True) here might be needed.
    # ble = bluetooth.BLE()
    # ble.active(True)

    ble_server = BluetoothMCPServer(server_core, device_name)
    try:
        await ble_server.start()
    except KeyboardInterrupt:
        print("BluetoothMCPServer: KeyboardInterrupt, stopping...")
    except Exception as e:
        print(f"BluetoothMCPServer: Main server loop error: {e}")
    finally:
        print("BluetoothMCPServer: Main finally block - calling ble_server.stop()...")
        await ble_server.stop()
        print("BluetoothMCPServer: Main finally block - calling aioble.stop()...")
        aioble.stop()  # Ensure aioble resources are cleaned up.
        print("BluetoothMCPServer: Fully stopped.")


if __name__ == "__main__":
    # Example usage (requires a ServerCore instance and registries)
    # This is just for conceptual testing if run directly.
    # A proper main.py or main_ble.py would set up ServerCore.

    class MockToolRegistry:
        async def handle_tool_call(self, tool_name, params):
            if tool_name == "echo":
                return {"success": True, "message": params.get("message", "")}
            return {"success": False, "error": "Tool not found"}

    class MockResourceRegistry:
        async def handle_resource_request(self, resource_name, params):
            return {"success": False, "error": "Resource not found"}

    class MockPromptRegistry:
        async def handle_prompt_request(self, prompt_name, params):
            return {"success": False, "error": "Prompt not found"}

    async def main():
        print("Starting mock Bluetooth MCP Server...")
        tool_registry = MockToolRegistry()
        resource_registry = MockResourceRegistry()
        prompt_registry = MockPromptRegistry()

        core = ServerCore(tool_registry, resource_registry, prompt_registry)
        await bluetooth_mcp_server(core, device_name="TestPicoBLE")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Main: Interrupted")
