# mcp/bluetooth_server.py

import asyncio
import bluetooth
import random
import struct
import aioble
from micropython import const

# --- UUIDs changed to reflect the working example's *intent* (Environmental Sensing) ---
# Even though the numerical values match NUS, the example names them as ENV_SENSE.
_NUS_SERVICE_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_NUS_RX_CHAR_UUID = bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_NUS_TX_CHAR_UUID = bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E") 

# Advertising interval (same as working example)
_ADV_INTERVAL_US = const(250_000)

# Appearance (from working example)
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)


# Helper to encode the temperature characteristic encoding (sint16, hundredths of a degree).
# This is directly from the working example.
def _encode_temperature(temp_deg_c):
    return struct.pack("<h", int(temp_deg_c * 100))


class BluetoothMCPServer:
    # Removed server_core dependency as it's not part of the simple sensor example
    def __init__(self, device_name="PicoLwBLE"):
        self._name = device_name

        # Create Environmental Sensing service and single characteristic
        self._nus_service = aioble.Service(_NUS_SERVICE_UUID)
        self._tx_char = aioble.Characteristic(
            self._nus_service, _NUS_TX_CHAR_UUID, read=True, notify=True
        )
        self._rx_char = aioble.Characteristic(
            self._nus_service, _NUS_RX_CHAR_UUID, write=True, capture=True
        )
        aioble.register_services(self._nus_service)

        self._is_running = False
        self._advertising_task = None
        self._connection_handler_task = None # TODO: revisit --> should this be a set?

        print(
            f"BluetoothMCPServer: Initialized using aioble. Advertising as '{self._name}'"
        )

    async def _handle_connection(self, connection):
        """
        Handles an individual client connection.
        In this simplified example, it just waits for disconnection.
        """
        print(f"BluetoothMCPServer: Central connected: {connection.device}")
        try:
            # Wait indefinitely for the device to disconnect
            await connection.disconnected(timeout_ms=None)
            print(f"BluetoothMCPServer: Central disconnected: {connection.device}")
        except asyncio.CancelledError:
            print(f"BluetoothMCPServer: Connection handler cancelled for {connection.device}")
        except Exception as e:
            print(f"BluetoothMCPServer: Error in connection handler for {connection.device}: {e}")
        finally:
            print(f"BluetoothMCPServer: Cleaning up connection for {connection.device}")


    async def _sensor_data_loop(self):
        """
        Continuously generates and sends mock temperature data via the characteristic.
        Analogous to the 'sensor_task' in the working example.
        """
        current_temp = 24.5
        n = 0
        while self._is_running:
            try:
                _, d = await self._rx_char.written(timeout_ms=1000)
                if d:
                    print(f'[TEST] Whew!! {d.decode("utf-8")}')
            except asyncio.TimeoutError:
                print(f'Timeout {n}')
                n += 1
            except Exception as e:
                print(f'Error: {e}')
            # TODO: Process the value here
            # _, data = await self._rx_char.written()


            # Update the characteristic value and send a notification
            self._tx_char.write(_encode_temperature(current_temp), send_update=True)
            
            print(f"BluetoothMCPServer: Notified temperature: {current_temp:.2f} C")
            current_temp += random.uniform(-0.5, 0.5) # Simulate temperature change
            await asyncio.sleep_ms(1000) # Wait 1 second (1000 ms)


    async def start(self):
        self._is_running = True
        print(f"BluetoothMCPServer: Starting. Will advertise as '{self._name}'.")

        async def advertising_loop():
            """
            Continuously advertises and accepts new connections.
            Analogous to the 'peripheral_task' in the working example.
            """
            while self._is_running:
                print("BluetoothMCPServer: Starting advertising...")
                try:
                    # Advertise and wait for a connection
                    async with await aioble.advertise(
                        _ADV_INTERVAL_US,
                        name=self._name,
                        services=[_NUS_SERVICE_UUID], # Advertise the Environmental Sensing Service
                        appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER, # From working example
                        timeout_ms=None,
                    ) as connection:
                        print(f"BluetoothMCPServer: Connection from {connection.device}")
                        # Handle this connection in a separate task
                        await self._handle_connection(connection)
                        # After _handle_connection returns (i.e., disconnected), loop back to advertise
                        # This simplifies the connection management from the original code.

                except asyncio.CancelledError:
                    print("BluetoothMCPServer: Advertising loop cancelled.")
                    break
                except Exception as e:
                    print(f"BluetoothMCPServer: Error in advertising loop: {e}")
                    await asyncio.sleep(5) # Wait before retrying advertising
            print("BluetoothMCPServer: Advertising loop finished.")


        # Create tasks for both advertising and sensor data generation
        self._advertising_task = asyncio.create_task(advertising_loop())
        self._connection_handler_task = asyncio.create_task(self._sensor_data_loop())

        # Wait for both tasks to complete (which they won't until stop() is called)
        try:
            await asyncio.gather(self._advertising_task, self._connection_handler_task)
        except asyncio.CancelledError:
            print("BluetoothMCPServer: Main server tasks were cancelled during start.")


    async def stop(self):
        self._is_running = False
        print("BluetoothMCPServer: Stopping...")

        # Cancel the advertising task
        if self._advertising_task:
            print("BluetoothMCPServer: Cancelling advertising task...")
            self._advertising_task.cancel()
            try:
                await self._advertising_task
            except asyncio.CancelledError:
                print("BluetoothMCPServer: Advertising task successfully cancelled.")
            except Exception as e:
                print(f"BluetoothMCPServer: Exception while awaiting cancelled advertising task: {e}")

        # Cancel the sensor data task
        if self._connection_handler_task:
            print("BluetoothMCPServer: Cancelling sensor data task...")
            self._connection_handler_task.cancel()
            try:
                await self._connection_handler_task
            except asyncio.CancelledError:
                print("BluetoothMCPServer: Sensor data task successfully cancelled.")
            except Exception as e:
                print(f"BluetoothMCPServer: Exception while awaiting cancelled sensor data task: {e}")

        print("BluetoothMCPServer: Class-level stop actions complete.")


# Main function to run the server, simplified to match the example
async def bluetooth_sensor_server_main(device_name="PicoLwBLE"):
    # It's good practice to activate BLE early if aioble doesn't do it.
    # However, aioble.advertise and aioble.scan typically handle activation.
    # If issues arise, uncommenting ble.active(True) here might be needed.
    # ble = bluetooth.BLE()
    # ble.active(True)

    ble_server = BluetoothMCPServer(device_name)
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
        aioble.stop() # Ensure aioble resources are cleaned up.
        print("BluetoothMCPServer: Fully stopped.")


# The __main__ block now directly uses the simplified main function
if __name__ == "__main__":
    print("Starting simplified Bluetooth sensor server...")
    try:
        asyncio.run(bluetooth_sensor_server_main(device_name="PicoLwBLE"))
    except KeyboardInterrupt:
        print("Main: Interrupted")
    except Exception as e:
        print(f"Main: An error occurred: {e}")
