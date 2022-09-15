import asyncio
import logging
from pymadoka.connection import discover_devices, force_device_disconnect


import click
import time
import json
import threading  

from functools import wraps
from pymadoka.controller import Controller
from pymadoka.features.fanspeed import FanSpeedEnum, FanSpeedStatus
from pymadoka.features.setpoint import SetPointStatus
from pymadoka.features.operationmode import OperationModeStatus, OperationModeEnum
from pymadoka.features.power import PowerStateStatus
from pymadoka.features.clean_filter import ResetCleanFilterTimerStatus

def format_output(format,status):
    try:
        print(json.dumps(vars(status),default=str))
    except:
        print(json.dumps(status,default=str))

import threading
import time

logger = logging.getLogger(__name__)

class LoadingThread(threading.Thread):
    
    def __init__(self, clean):
        self.clean = clean
        super().__init__()
        self.stopevent = threading.Event()

    def stop(self):
        self.stopevent.set()

    def join(self, *args, **kwargs):
        self.stop()
        super().join(*args, **kwargs)

    def run(self):
        if not self.clean:
            spaces = 0  
            while not self.stopevent.is_set():
                print("\b "*spaces+".", end="", flush=True) 
                spaces = spaces+1                          
                time.sleep(0.2)                            
                if (spaces>5):                              
                    print("\b \b"*spaces, end="")           
                    spaces = 0  
            print("\b"*(spaces+2), end="", flush=True) 
 

def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        async def p(*args,**kwargs):
            
            loading = args[0]["loading"]
            if loading is not None:
                loading.start()

            madoka:Controller = args[0]["madoka"]
            if args[0]["force_disconnect"]:
                await force_device_disconnect(madoka.connection.address)
            await discover_devices(timeout = args[0]["timeout"], adapter = args[0]["adapter"])
            await madoka.start()
            status = await f(*args,**kwargs)
            if loading is not None:
                loading.join()
            format_output(args[0]["format"],status)
            
        try:
            return asyncio.run(p(*args, **kwargs)) 
        except KeyboardInterrupt:
            logger.info("User stopped program.")
        except Exception as e:
            logger.error(str(e))
            if "loading" in args[0]:
                args[0]["loading"].join()
        finally:
            logger.info("Disconnecting...")
   
    return wrapper
@click.group(chain=False)
@click.pass_context
@click.option('-a', '--address', required=True, type=str, help="Bluetooth MAC address of the thermostat")
@click.option('-d', '--adapter', required=False, type=str, default="hci0", show_default=True, help="Name of the Bluetooth adapter to be used for the connection")
@click.option('--force-disconnect/--not-force-disconnect', default="True", show_default=True, help="Should disconnect the device to ensure it is recognized (recommended)")
@click.option('-t', '--device-discovery-timeout', type=int, default=5, show_default=True, help = "Timeout for Bluetooth device scan in seconds")
@click.option('-o', '--log-output', required=False,type=click.Path(), help="Path to the log output file")
@click.option('--debug', is_flag=True, help="Enable debug logging")
@click.option('--verbose', is_flag=True, help="Enable verbose logging")
@click.option('--clean', is_flag=True, help="Enable clean output")
@click.version_option()


def cli(ctx,verbose,clean,adapter,log_output,debug,address,force_disconnect, device_discovery_timeout):
  
    madoka = Controller(address, adapter = adapter)
    
    ctx.obj = {}
    ctx.obj["madoka"] = madoka
    ctx.obj["loop"] = asyncio.get_event_loop()   
    ctx.obj["format"] = format
    ctx.obj["timeout"] = device_discovery_timeout
    ctx.obj["adapter"] = adapter
    ctx.obj["force_disconnect"] = force_disconnect
 
    loading = LoadingThread(clean)
    logging_level = None
    if verbose:
        logging_level = logging.DEBUG if debug else logging.INFO
    else:
        ctx.obj["loading"] = loading
        
    logging_filename = log_output
    logging.basicConfig(level=logging_level,
                        filename = logging_filename)

    
    
       

@cli.command()
@click.pass_obj
@coro
@click.argument('fan-speed',
              type=(click.Choice(['LOW', 'MID', 'HIGH', 'AUTO'], case_sensitive=True),click.Choice(['LOW', 'MID', 'HIGH', 'AUTO'], case_sensitive=True)))
async def set_fan_speed(obj,fan_speed):
   """Set cooling and heating fan speeds."""
   return await obj["madoka"].fan_speed.update(FanSpeedStatus(FanSpeedEnum[fan_speed[0]], FanSpeedEnum[fan_speed[1]]))
  
@cli.command()
@click.pass_obj
@coro
async def get_fan_speed(obj):
    """Get cooling and heating fan speeds."""
    return await obj["madoka"].fan_speed.query()
 

    
@cli.command()
@click.pass_obj
@coro
async def get_operation_mode(obj):
    """Get the operation mode."""
    return await obj["madoka"].operation_mode.query()
  
@cli.command()
@click.pass_obj
@coro
@click.argument('operation-mode',
              type=click.Choice(['FAN', 'DRY', 'AUTO', 'COOL','HEAT','VENTILATION'], case_sensitive=True))
async def set_operation_mode(obj,operation_mode):
    """Set the operation mode."""
    return await obj["madoka"].operation_mode.update(OperationModeStatus(OperationModeEnum[operation_mode]))
    

@cli.command()
@click.pass_obj
@coro
async def get_power_state(obj):
    """Check if the HVAC is turned on."""
    return await obj["madoka"].power_state.query()
  
   
@cli.command()
@click.pass_obj
@coro
@click.argument('power-state',
              type=click.Choice(['ON','OFF'], case_sensitive=True))
async def set_power_state(obj,power_state):
    """Turn ON or OFF the HVAC."""
    return await obj["madoka"].power_state.update(PowerStateStatus(power_state == "ON"))
  
        
@cli.command()
@click.pass_obj
@coro
async def get_temperatures(obj):
    """Get temperatures as read by the thermostat."""
    return await obj["madoka"].temperatures.query()
  

@cli.command()
@click.pass_obj
@coro
async def get_set_point(obj):
    """Get target temperatures in Celsius degrees."""
    return await obj["madoka"].set_point.query()

@cli.command()
@click.pass_obj
@coro
@click.argument('set-point',
              type= (click.IntRange(0, 30, clamp=True),click.IntRange(0, 30, clamp=True)))
async def set_set_point(obj,set_point):
    """Set cooling/heating target temperatures in Celsius degrees."""
    return await obj["madoka"].set_point.update(SetPointStatus(set_point[0],set_point[1]))
    
@cli.command()
@click.pass_obj
@coro
async def get_clean_filter_indicator(obj):
    """Get status of the Clean Filter indicator."""
    return await obj["madoka"].clean_filter_indicator.query()
   
@cli.command()
@click.pass_obj
@coro
async def reset_clean_filter_timer(obj):
    """Reset the Clean Filter indicator timer."""
    return await obj["madoka"].reset_clean_filter_timer.update(ResetCleanFilterTimerStatus())
  
@cli.command()
@click.pass_obj
@coro
async def get_status(obj):
    """Get status of all the thermostat features."""
    await obj["madoka"].update()
    return obj["madoka"].refresh_status()
    

@cli.command()
@click.pass_obj
@coro
async def get_info(obj):
    """Get info of the device."""
    return await obj["madoka"].read_info()
  
    

if __name__ == "__main__":  
    asyncio.get_event_loop().run_until_complete(cli())
   
