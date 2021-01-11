import asyncio
import sys
import logging
import json
from pymadoka.controller import Controller
from pymadoka.features.setpoint import SetPointStatus

async def main(madoka):
    await madoka.start()
    
    set_point_status = await madoka.set_point.query()
    logging.info(f"Set Point status:\n{json.dumps(vars(set_point_status), default = str)}")
    
    await madoka.set_point.update(SetPointStatus(27,27))
    
    set_point_status = await madoka.set_point.query()
    logging.info(f"Updated Set Point status:\n{json.dumps(vars(set_point_status), default=str)}")
   

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
    
    