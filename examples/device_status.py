import asyncio
import sys
import logging
import json
from pymadoka.controller import Controller


async def main(madoka):
    await madoka.start()
    await madoka.update()
    madoka.refresh_status()
    logging.info(f"Device status:\n{json.dumps(vars(madoka.status))}")
   

logging.basicConfig(level=logging.DEBUG)
address = sys.argv[1]
madoka = Controller(address)
loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(main(madoka))
    loop.run_forever()
except KeyboardInterrupt:
    logging.info("User stopped program.")
finally:
    logging.info("Disconnecting...")
    loop.run_until_complete(madoka.stop())
