import asyncio
import sys
import logging
import json
from pymadoka.controller import Controller

logger = logging.getLogger(__name__)

async def main(madoka):
    await madoka.start()
    await madoka.update()
    madoka.refresh_status()
    logger.info(f"Device status:\n{json.dumps(vars(madoka.status))}")
   

logger.basicConfig(level=logger.DEBUG)
address = sys.argv[1]
madoka = Controller(address)
loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(main(madoka))
    loop.run_forever()
except KeyboardInterrupt:
    logger.info("User stopped program.")
finally:
    logger.info("Disconnecting...")
    loop.run_until_complete(madoka.stop())
