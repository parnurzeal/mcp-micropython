import asyncio

from bleak import BleakClient, BleakScanner

CHARACTERISTIC_UUID_RX = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
CHARACTERISTIC_UUID_TX = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
# CHARACTERISTIC_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
# CHARACTERISTIC_UUID = '00002A6E-0000-1000-8000-00805f9b34fb'
TARGET_DEVICE_NAME = 'PicoLwBLE'

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
  N = 50
  while counter < N:
    try:
      async with BleakClient(pico_address) as client:
        # print('Services: ')
        # for _, val in client.services.characteristics.items():
        #   print(val.service_uuid)
        while counter < N:
          data = await client.read_gatt_char(CHARACTERISTIC_UUID_TX)
          await client.write_gatt_char(CHARACTERISTIC_UUID_RX, f"HELLO {counter}".encode('utf-8'))
          print(f'Temperature: {int.from_bytes(data, byteorder="little") / 100.0}')
          counter += 1
          await asyncio.sleep(2)
    except Exception as e:
      print(f'Error: {e}')

if __name__ == '__main__':
  asyncio.run(main())
