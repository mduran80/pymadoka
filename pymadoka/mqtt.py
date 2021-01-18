import asyncio
from asyncio.exceptions import CancelledError
import logging
import click
import json
import yaml

import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from typing import Any,Dict
from functools import wraps
from pymadoka.connection import Connection, ConnectionStatus, ConnectionException, discover_devices, force_device_disconnect
from pymadoka.controller import Controller
from pymadoka.features.fanspeed import FanSpeedEnum, FanSpeedStatus
from pymadoka.features.setpoint import SetPointStatus
from pymadoka.features.operationmode import OperationModeStatus, OperationModeEnum
from pymadoka.features.power import PowerStateStatus
from pymadoka.features.clean_filter import ResetCleanFilterTimerStatus
from pymadoka import Feature

logger = logging.getLogger(__name__)

# Taken from paho-mqtt examples to integrate with asyncio loop

class AsyncioHelper:
    def __init__(self, loop, client):
        self.loop = loop
        self.client = client
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write

    def on_socket_open(self, client, userdata, sock):
        def cb():
            client.loop_read()

        self.loop.add_reader(sock, cb)
        self.misc = self.loop.create_task(self.misc_loop())

    def on_socket_close(self, client, userdata, sock):
        self.loop.remove_reader(sock)
        self.misc.cancel()

    def on_socket_register_write(self, client, userdata, sock):

        def cb():
            client.loop_write()

        self.loop.add_writer(sock, cb)

    def on_socket_unregister_write(self, client, userdata, sock):
        self.loop.remove_writer(sock)

    async def misc_loop(self):
        while self.client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break


async def set_operation_mode(controller:Controller,payload:str):
    """
    Callback used to set the operation mode. It will issue a turn on/off command 
    depending on the value of the mode (OFF if 'OFF', ON otherwise)
    Args:
        controller (`Controller`): Device controller
        payload (str): The payload will be converted to the values accepted by the controller
    """
    try:
        value = payload.decode("utf-8").upper()
        if value != "OFF":
            status = OperationModeStatus(OperationModeEnum[value])
            await controller.operation_mode.update(status)
        await controller.power_state.update(PowerStateStatus(value != "OFF"))
    except CancelledError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionException as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionAbortedError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except Exception as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    
async def set_fan_speed(controller:Controller,payload:str):
    """
    Callback used to set the fan speed
    Args:
        controller (`Controller`): Device controller
        payload (str): The payload will be converted to the values accepted by the controller
    """

    try:

        value = payload.decode("utf-8").upper()
        new_cooling_fan_speed = controller.fan_speed.status.cooling_fan_speed
        new_heating_fan_speed = controller.fan_speed.status.heating_fan_speed
        if (controller.operation_mode.status.operation_mode == OperationModeEnum.AUTO or
           controller.operation_mode.status.operation_mode == OperationModeEnum.DRY or
           controller.operation_mode.status.operation_mode == OperationModeEnum.FAN):
            new_cooling_fan_speed = value
            new_heating_fan_speed = value
        elif controller.operation_mode.status.operation_mode == OperationModeEnum.HEAT:
            new_heating_fan_speed = value
        elif controller.operation_mode.status.operation_mode == OperationModeEnum.COOL:
            new_cooling_fan_speed = value

        status = FanSpeedStatus(FanSpeedEnum[new_cooling_fan_speed],
                                FanSpeedEnum[new_heating_fan_speed])
        await controller.fan_speed.update(status)
    except CancelledError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionException as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionAbortedError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except Exception as e:
        logging.error(f"Could not update operation mode: {str(e)}")

async def set_power_state(controller:Controller,payload:str):
    """
    Callback used to set the power state
    Args:
        controller (`Controller`): Device controller
        payload (str): The payload will be converted to the values accepted by the controller
    """
    try:
        status = PowerStateStatus(payload=="on")
        await controller.power_state.update(status)
    except CancelledError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionException as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionAbortedError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except Exception as e:
        logging.error(f"Could not update operation mode: {str(e)}")

async def set_set_point_state(controller:Controller,payload:str):
    """
    Callback used to set the set point (target temperature)
    Args:
        controller (`Controller`): Device controller
        payload (str): The payload will be converted to the values accepted by the controller
    """
    try:
        value = int(payload)
        new_cooling_set_point = controller.set_point.status.cooling_set_point
        new_heating_set_point = controller.set_point.status.heating_set_point

        if (controller.operation_mode.status.operation_mode == OperationModeEnum.AUTO or
           controller.operation_mode.status.operation_mode == OperationModeEnum.DRY or
           controller.operation_mode.status.operation_mode == OperationModeEnum.FAN):
            new_cooling_set_point = value
            new_heating_set_point = value 
        elif controller.operation_mode.status.operation_mode == OperationModeEnum.HEAT:
            new_heating_set_point = value
        elif controller.operation_mode.status.operation_mode == OperationModeEnum.COOL:
            new_cooling_set_point = value
        await controller.set_point.update(SetPointStatus(new_cooling_set_point,new_heating_set_point))
    except CancelledError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionException as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except ConnectionAbortedError as e:
        logging.error(f"Could not update operation mode: {str(e)}")
    except Exception as e:
        logging.error(f"Could not update operation mode: {str(e)}")

class MQTT:

    """This class implements the MQTT bridge.
    
    Attributes:
        controller (Controller): Connection used to communicate with the device
        connected (bool): Feature used to control the fan speed
        client (Client): Feature used to control the fan speed
        mqtt_cfg (Dict[str,Any]): Feature used to control the fan speed
        loop (AsyncioLoop): Feature used to control the fan speed
    """
  
    ROOT_TOPIC = "/madoka"
    OPERATION_MODE_TOPIC = "operation_mode"
    POWER_STATE_TOPIC = "fan_speed"
    FAN_SPEED_TOPIC = "fan_speed"
    SET_POINT_TOPIC = "set_point"
    AVAILABLE_TOPIC = "available"

    
    def __init__(self,loop,controller: Controller,
                 config: Dict[str,Any]):

        """Initialize the MQTT bridge.
    
        Args:
            loop (AsyncioLoop): Asyncio loop to integrate the MQTT loop with
            controller (Controller): Controller used to manage the device
            mqtt_cfg (Dict[str,Any]): MQTT config 
            
        """
        self.controller:Controller = controller
        self.connected:bool = False
        self.client:mqtt.Client = None
        self.mqtt_cfg = config["mqtt"]
        self.loop = loop
        

    def connect(self):
        """ Connect to the MQTT broker. It returns a future to notify when the 
        connection has been finished.
        """

        id = "madoka_mqtt_" + self.controller.connection.name

        if "id" in self.mqtt_cfg:
            id = self.mqtt_cfg["id"]

        self.client:mqtt.Client = mqtt.Client(client_id = id)
        if "username" in self.mqtt_cfg:
            self.client.username_pw_set(username=self.mqtt_cfg["username"],password=self.mqtt_cfg["password"])
       
        if self.mqtt_cfg["ssl"]:
            self.client.tls_set(ca_certs=mqtt.TLS_CERT_PATH, certfile=None,
                                keyfile=None, cert_reqs=mqtt.ssl.CERT_REQUIRED,
                                tls_version=mqtt.ssl.PROTOCOL_TLSv1_2, ciphers=None)
            self.client.tls_insecure_set(False)
        
        try:

            aioh = AsyncioHelper(self.loop, self.client)
         
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            self.client.connect(self.mqtt_cfg["host"], port=self.mqtt_cfg["port"])
            self.connect_future = asyncio.get_event_loop().create_future()
            return self.connect_future

        except MQTTException as e:
            logger.error(f"Error in MQTT: {str(e)}")
    
    def start(self):
        """Start the MQTT bridge. Subscribe to the topics"""
        subscribe_topics = []
        for k,v in vars(self.controller).items():
            if isinstance(v,Feature):
                subscribe_topics.append(("/".join([self.get_device_topic(),k,"set"]),0))

        self.client.subscribe(subscribe_topics)

    def stop(self):
        """ Disconnect from the MQTT broker """
        self.client.disconnect()
       
    
    def on_connect(self,client, userdata, flags, rc):
        """ Connection established callback. See paho-mqtt docs for more details. """
        self.connected = rc == 0
        if self.connect_future:
            self.connect_future.set_result(self.connected)
        if self.connected: 
            logger.debug("Connected to MQTT broker")
            self.start()

    def on_disconnect(self,client, userdata, rc):
        """ Connection established callback. See paho-mqtt docs for more details. """
        logger.debug(f"Disconnected from MQTT broker ({rc})")
        asyncio.create_task(self.reconnect())

    async def reconnect(self):
        is_connected = self.client.is_connected        
        while not is_connected:
            try:
                logger.debug("Reconnecting in 60s...")
                await asyncio.sleep(60)
                c = await self.connect()
                await c
                is_connected = c.result()
               
            except CancelledError:
                pass
        
        self.available(self.controller.connection.connection_status == ConnectionStatus.CONNECTED)

    def get_device_topic(self):
        """ Get the customized device topic using the device name and the root topic. 
        Returns:
            str: The device topic in the form /root_topic/device_name"""
        root_topic = self.ROOT_TOPIC 
        if "root_topic" in self.mqtt_cfg:
            root_topic = self.mqtt_cfg["root_topic"]
        normalized_name = self.controller.connection.name
        normalized_name = normalized_name.replace(" ","_")
        normalized_name = normalized_name.replace(":","_")
        normalized_name = normalized_name.replace("/","_")

        return "/".join([root_topic,normalized_name]) 

    def available(self, status:bool):
        """
        Send the status to the availability topic
        Args:
            status (bool): True if available, False otherwise       
        """
        device_topic = self.get_device_topic()
        topic = "/".join([device_topic, self.AVAILABLE_TOPIC])
        
        self.client.publish(topic,"0" if not status else "1")

    def update(self, status:str):
        """
        Send the status to the status topic (JSON payload)
        Args:
            status (str): New status
        """           
        if not self.client.is_connected:
            logger.debug("MQTT broker is not available. Skipping message...")
            device_topic = self.get_device_topic()
            topic = "/".join([device_topic, "state","get"])
            
            self.client.publish(topic,status)
        

    def on_message(self,client, userdata, msg):
        """ Message received callback. See paho-mqtt docs for more details. """
        if msg.topic == "/".join([self.get_device_topic(), self.OPERATION_MODE_TOPIC,"set"]):
            asyncio.get_event_loop().create_task(set_operation_mode(self.controller,msg.payload))
        
        elif msg.topic == "/".join([self.get_device_topic(), self.FAN_SPEED_TOPIC,"set"]):
            asyncio.get_event_loop().create_task(set_fan_speed(self.controller,msg.payload))
        
        elif msg.topic == "/".join([self.get_device_topic(), self.POWER_STATE_TOPIC,"set"]):
            asyncio.get_event_loop().create_task(set_power_state(self.controller,msg.payload))
        
        elif msg.topic == "/".join([self.get_device_topic(), self.SET_POINT_TOPIC,"set"]):
            asyncio.get_event_loop().create_task(set_set_point_state(self.controller,msg.payload))
        
    
def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return asyncio.run(f(*args, **kwargs))
        except KeyboardInterrupt:
            logger.info("User stopped program.")
        except Exception as e:
            logger.error("",e, stack_info=True)
        
    return wrapper

async def periodic_update(interval:int,controller:Controller,mqtt_service:MQTT):
    """ This routine is used to schedule the periodic update of the controller.
    Args:
        interval (int): Number of seconds to wait between updates
        controller (`Controller`): Device controller to be updated
        mqtt_service (`MQTT`): MQTT service to send updates with
    """
    available = True
    while available:
        try:
            await controller.update()
            status = controller.refresh_status()
            mqtt_service.update(json.dumps(status,default=str))
            await asyncio.sleep(interval)
        except CancelledError as e:
                pass
        except ConnectionAbortedError as e:
             mqtt_service.available(False)
             available = False
        except Exception as e:
            logger.error(f"Exception caught : {str(e)}")

@click.command()
@click.pass_context
@click.option('-a', '--address', required=True, type=str, help="Bluetooth MAC address of the thermostat")
@click.option('-c', '--config', required=True, type=click.Path(), help="MQTT config file")
@click.option('-d', '--adapter', required=False, type=str, default="hci0", show_default=True, help="Name of the Bluetooth adapter to be used for the connection")
@click.option('--force-disconnect/--not-force-disconnect', default="True", show_default=True, help="Should disconnect the device to ensure it is recognized (recommended)")
@click.option('-t', '--device-discovery-timeout', type=int, default=5, show_default=True, help = "Timeout for Bluetooth device scan in seconds")
@click.option('-o', '--log-output', required=False,type=click.Path(), help="Path to the log output file")
@click.option('--debug', is_flag=True, help="Enable debug logging")
@click.option('--verbose', is_flag=True, help="Enable versbose logging")
@click.version_option()
@coro
async def run(ctx,verbose,adapter,log_output,debug,address,force_disconnect, device_discovery_timeout, config):
    
        
    madoka = Controller(address, adapter = adapter)
    
    ctx.obj = {}
    ctx.obj["madoka"] = madoka
    ctx.obj["loop"] = asyncio.get_event_loop()   
    ctx.obj["timeout"] = device_discovery_timeout
    ctx.obj["adapter"] = adapter
    ctx.obj["force_disconnect"] = force_disconnect
    with open(config, 'r') as stream:
        yml_config = yaml.safe_load(stream)
        ctx.obj["config"] = yml_config
    
    logging_level = None
    if verbose:
        logging_level = logging.DEBUG if debug else logging.DEBUG
        
    logging_filename = log_output
    logging.basicConfig(level=logging_level,
                        filename = logging_filename)

    
    if force_disconnect:
        await force_device_disconnect(madoka.connection.address)
    discovered_devices = await discover_devices(timeout = ctx.obj["timeout"], adapter = ctx.obj["adapter"])
    mqtt_service = MQTT(asyncio.get_event_loop(),madoka,yml_config)
    update_task = None
    try:
        
        await madoka.start()       
        connect = mqtt_service.connect() 
        
        await connect
        if not connect.result():
              return
        
        mqtt_service.available(True)
        
        update_task = asyncio.create_task(periodic_update(yml_config["daemon"]["update_interval"], madoka, mqtt_service))
    
        asyncio.gather(update_task)
    except CancelledError as e:
        logger.error(e)
    except ConnectionAbortedError as e:
        if mqtt_service.connected:
            mqtt_service.available(False)
        if update_task is not None:
            await update_task.stop()
        mqtt_service.stop()
        await madoka.stop()
        logger.error(e)
    except ConnectionRefusedError as e:
        logger.error("Could not connect to MQTT broker")
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":  
      

    asyncio.run(run())        
    asyncio.get_event_loop().run_forever()

    
   
