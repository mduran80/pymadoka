import asyncio
import sys
import logging
import json

from pymadoka.controller import Controller

async def main(madoka):
    await madoka.start()
    device_info = await madoka.read_info()
    logging.info(f"Device info:\n {json.dumps(device_info, default = str)}")
 

logging.basicConfig(level=logging.DEBUG)
address = sys.argv[1]
madoka = Controller(address, force_disconnect=False, device_discovery_timeout=10)
loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(main(madoka))
    loop.run_forever()
except KeyboardInterrupt:
    logging.info("User stopped program.")
finally:
    logging.info("Disconnecting...")
    loop.run_until_complete(madoka.stop())
    