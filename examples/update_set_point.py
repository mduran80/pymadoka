import asyncio
import sys
import logging
import json
from pymadoka.controller import Controller
from pymadoka.features.setpoint import SetPointStatus
from pymadoka.connection import discover_devices, force_device_disconnect

logger = logging.getLogger(__name__)


async def main(madoka):
    try:
        await force_device_disconnect(madoka.connection.address)
        await discover_devices()
        await madoka.start()    
        set_point_status = await madoka.set_point.query()
        logger.info(f"Set Point status:\n{json.dumps(vars(set_point_status), default = str)}")
        await madoka.set_point.update(SetPointStatus(20,27))
        set_point_status = await madoka.set_point.query()
        logger.info(f"Updated Set Point status:\n{json.dumps(vars(set_point_status), default=str)}")
    except Exception as e:
        logging.error(str(e))
        asyncio.get_event_loop().stop()
   

logging.basicConfig(level=logging.DEBUG)
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
    
    