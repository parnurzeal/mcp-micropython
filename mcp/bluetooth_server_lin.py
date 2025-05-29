# mcp/bluetooth_server.py (Re-integrating MCP logic)

import asyncio
import aioble
import bluetooth
import json
from micropython import const

from .server_core import ServerCore  # Re-import ServerCore
from .registry import ToolRegistry, ResourceRegistry, PromptRegistry  # For ServerCore

# Service UUID (Environmental Sensing - 0x181A)
_MCP_SERVICE_UUID = bluetooth.UUID(0x181A)

# Characteristic UUIDs
# Using 0x2A6E (Temperature) for TX (Server to Client for MCP responses)
_MCP_TX_CHAR_UUID = bluetooth.UUID(0x2A6E)
# Using a custom 128-bit UUID for RX (Client to Server for MCP commands)
_MCP_RX_CHAR_UUID = bluetooth.UUID(
    "DEADBEEF-0001-1000-8000-00805F9B34FB"
)  # Custom RX UUID

_ADV_APPEARANCE_GENERIC_DEVICE = const(0)  # Or a more specific one if desired
_ADV_INTERVAL_MS = 250_000
_MAX_BLUETOOTH_PACKET_BYTES = 20

# Global service and characteristics
mcp_service = aioble.Service(_MCP_SERVICE_UUID)
mcp_tx_characteristic = aioble.Characteristic(
    mcp_service, _MCP_TX_CHAR_UUID, read=True, notify=True, indicate=True
)
mcp_rx_characteristic = aioble.Characteristic(
    mcp_service, _MCP_RX_CHAR_UUID, write=True, capture=True
)

_EOT_BYTE = 'â'

# Buffer for incoming data
_rx_buffer = bytearray()


async def mcp_handler_task(connection, core: ServerCore, rx_char, tx_char):
    global _rx_buffer
    print(f"BluetoothMCP: mcp_handler_task started for {connection.device}")
    try:
        # Write an initial status to TX char
        tx_char.write(
            b'{"status":"mcp_ready"}', send_update=True
        )  # send_update to notify if client subscribed early

        while connection.is_connected():
            try:
                _, data = await rx_char.written(timeout_ms=1000)
                if data:
                    _rx_buffer.extend(data)
                    print(f"BluetoothMCP: Received on RX_CHAR (0x2A6F): {data}")

                    if not _EOT_BYTE in _rx_buffer.decode('utf-8'):
                        # TODO: remove. For testing only.
                        # print('[TEST] Sleeping to test async')
                        # await asyncio.sleep(2)
                        continue

                    # print(f'Final: {_rx_buffer.decode("utf-8")}')
                    # Process buffered data (JSON messages separated by newline)
                    # response_bytes_to_send = None
                    message_str = _rx_buffer.decode("utf-8")[:-1]
                    print(f'Final: {message_str}')
                    if not message_str:
                        continue

                    print(f"BluetoothMCP: Processing MCP message: {message_str}")
                    try:
                        message_dict = json.loads(message_str)
                        
                        response_dict = await core.process_message_dict(
                            message_dict
                        )
                        if response_dict:
                            response_str = json.dumps(response_dict)
                            response_bytes_to_send = (response_str + "\n").encode(
                                "utf-8"
                            )
                        else:
                            print("BluetoothMCP: No response from core")
                            response_bytes_to_send = None
                            continue
                    except ValueError:
                        print(f"BluetoothMCP: Invalid JSON: {message_str}")
                        error_resp = {
                            "jsonrpc": "2.0",
                            "error": {"code": -32700, "message": "Parse error"},
                            "id": None,
                        }
                        response_bytes_to_send = (
                            json.dumps(error_resp) + "\n"
                        ).encode("utf-8")
                    except Exception as e_proc:
                        print(f"BluetoothMCP: Error processing message: {e_proc}")
                        error_resp = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Internal error: {e_proc}",
                            },
                            "id": None,
                        }
                        response_bytes_to_send = (
                            json.dumps(error_resp) + "\n"
                        ).encode("utf-8")
                    finally:
                        _rx_buffer = bytearray()

                    if response_bytes_to_send:
                        print(
                            f"BluetoothMCP: Sending response on TX_CHAR (0x2A6E): {response_bytes_to_send[:100]}"
                        )
                        for i in range(0, len(response_bytes_to_send), _MAX_BLUETOOTH_PACKET_BYTES):
                            tx_char.notify(connection, response_bytes_to_send[i:min(len(response_bytes_to_send), i + _MAX_BLUETOOTH_PACKET_BYTES)])
                        # tx_char.write(response_bytes_to_send, send_update=True) # Alternative if notify isn't enough
                        response_bytes_to_send = None
            except asyncio.TimeoutError:
                pass  # Normal if no data written by client
            except aioble.DeviceDisconnectedError:
                print(
                    f"BluetoothMCP: Device disconnected during mcp_handler_task for {connection.device}"
                )
                break  # Exit while loop
            except Exception as e:
                print(f"BluetoothMCP: Error in mcp_handler_task loop: {e}")
                await asyncio.sleep_ms(100)  # Avoid tight loop on other errors

    except asyncio.CancelledError:
        print(f"BluetoothMCP: mcp_handler_task cancelled for {connection.device}")
    except Exception as e:
        print(f"BluetoothMCP: Unhandled error in mcp_handler_task: {e}")
    finally:
        _rx_buffer = bytearray()  # Clear buffer for this connection
        print(f"BluetoothMCP: mcp_handler_task finished for {connection.device}")


async def peripheral_mcp_task(device_name_str: str, core: ServerCore):
    print(
        f"BluetoothMCP: peripheral_mcp_task started, advertising as {device_name_str}"
    )
    try:
        aioble.register_services(mcp_service)
        print("BluetoothMCP: MCP services registered.")
    except Exception as e_reg:
        print(f"BluetoothMCP: Error registering MCP services: {e_reg}")
        return

    while True:
        print(f"BluetoothMCP: Starting advertising as '{device_name_str}'...")
        connection = None
        try:
            connection = await aioble.advertise(
                _ADV_INTERVAL_MS,
                name=device_name_str,
                services=[_MCP_SERVICE_UUID],  # Advertise our MCP service (0x181A)
                appearance=_ADV_APPEARANCE_GENERIC_DEVICE,
            )
            print(f"BluetoothMCP: Connection from {connection.device}")

            # Connection established, run the MCP handler for this connection.
            # This will block until the handler finishes (i.e., client disconnects).
            await mcp_handler_task(
                connection, core, mcp_rx_characteristic, mcp_tx_characteristic
            )

            # After mcp_handler_task returns, ensure disconnection is processed.
            print(
                f"BluetoothMCP: mcp_handler_task completed for {connection.device}. Waiting for final disconnect confirmation."
            )
            await connection.disconnected(
                timeout_ms=2000
            )  # Wait a bit for disconnect event
            print(f"BluetoothMCP: Device {connection.device} fully disconnected.")

        except asyncio.CancelledError:
            print("BluetoothMCP: peripheral_mcp_task cancelled.")
            if connection and connection.is_connected():
                await connection.disconnect()
            break
        except Exception as e:
            print(f"BluetoothMCP: Error in peripheral_mcp_task: {e}")
            if connection and connection.is_connected():
                await connection.disconnect()  # Attempt to disconnect on error
            await asyncio.sleep_ms(5000)
    print("BluetoothMCP: peripheral_mcp_task finished.")


# Main entry point called by main_ble.py
async def bluetooth_mcp_server(server_core: ServerCore, device_name="PicoMCP-BLE"):
    print(f"BluetoothMCP: Server starting with device name '{device_name}'")

    ble = bluetooth.BLE()
    if not ble.active():
        ble.active(True)
    print(f"BluetoothMCP: BLE Radio Active: {ble.active()}")

    # Create the main peripheral task
    # This task now takes server_core.
    main_task = asyncio.create_task(peripheral_mcp_task(device_name, server_core))

    try:
        await main_task
    except KeyboardInterrupt:
        print("BluetoothMCP: KeyboardInterrupt received.")
    except Exception as e:
        print(f"BluetoothMCP: Error in main_task execution: {e}")
    finally:
        print("BluetoothMCP: Main server function stopping...")
        if main_task and not main_task.done():
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                print("BluetoothMCP: Main task cancelled successfully.")
        # aioble.stop() should be handled by the script calling this function (e.g. main_ble.py)
        print("BluetoothMCP: Server stopped.")


if __name__ == "__main__":
    print("Starting BluetoothMCP Server directly (for testing)...")

    # Create a mock ServerCore for direct testing
    mock_tool_registry = ToolRegistry()
    mock_resource_registry = ResourceRegistry()
    mock_prompt_registry = PromptRegistry()
    mock_core = ServerCore(
        mock_tool_registry, mock_resource_registry, mock_prompt_registry
    )

    async def mock_echo_tool(message: str):
        return f"Echo: {message}"

    mock_tool_registry.register_tool(
        name="echo",
        description="Echoes a message",
        input_schema={"message": {"type": "string", "description": "Message to echo"}},
        handler_func=mock_echo_tool,
    )

    try:
        asyncio.run(bluetooth_mcp_server(mock_core, device_name="PicoMCPDirect"))
    except KeyboardInterrupt:
        print("MainApp: Interrupted by user.")
    except Exception as e:
        print(f"MainApp: Error - {type(e).__name__}: {e}")
    finally:
        print("MainApp: Cleaning up aioble...")
        aioble.stop()
        print("MainApp: Finished.")
