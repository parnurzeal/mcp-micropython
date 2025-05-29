import asyncio
import json

from bleak import BleakClient, BleakScanner

CHARACTERISTIC_UUID_TX = '00002A6E-0000-1000-8000-00805f9b34fb' # '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
CHARACTERISTIC_UUID_RX = 'DEADBEEF-0001-1000-8000-00805F9B34FB' # '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
# CHARACTERISTIC_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
# CHARACTERISTIC_UUID = '00002A6E-0000-1000-8000-00805f9b34fb'
TARGET_DEVICE_NAME = 'PicoMCPDirect'
EOT_BYTE = 'â'

async def scan_for_pico_device():
  target_address = ''
  target_counts = 0

  devices = await BleakScanner.discover()
  for d in devices:
    if TARGET_DEVICE_NAME in d.name:
      target_address = d.address
      target_counts += 1
  
  if target_counts != 1:
    print(f'Unexpected no. of Pico devices: {target_counts}! Returning last scanned.')
  
  return target_address

async def main():
  pico_address = await scan_for_pico_device()
  print(f'Found pico address: {pico_address}')

  if pico_address == '':
    return

  counter = 0
  N = 20
  while counter < N:
    try:
      async with BleakClient(pico_address) as client:
        while counter < N:
          message_to_send_dict = {
            "params": {
              "name": "echo",
              "arguments": {"message": "Hello from the Python client!"},
            },
            "method": "tools/call",
            "id": 1
          }
          message_json_str = json.dumps(message_to_send_dict)
          formatted_message = message_json_str + EOT_BYTE
          for i in range(0, len(formatted_message), 20):
            sent_message = formatted_message[i: min(len(formatted_message), i + 20)]
            print(f'Sending... {sent_message} {len(sent_message)}')
            await client.write_gatt_char(CHARACTERISTIC_UUID_RX, sent_message.encode('utf-8'))
          await client.start_notify(CHARACTERISTIC_UUID_TX, lambda _, d: print(d))
          # TODO: Uncomment for test message
          # await client.write_gatt_char(CHARACTERISTIC_UUID_RX, f"HELLO {counter}".encode('utf-8'))

          # data = await client.read_gatt_char(CHARACTERISTIC_UUID_TX)
          # print(f'Received from Echo: {data.decode("utf-8")}')
          # TODO(pohlinwei): Uncomment for temperature
          # print(f'Temperature: {int.from_bytes(data, byteorder="little") / 100.0}')
          counter += 1
          await asyncio.sleep(2)
    except Exception as e:
      print(f'Error: {e}')

if __name__ == '__main__':
  asyncio.run(main())
