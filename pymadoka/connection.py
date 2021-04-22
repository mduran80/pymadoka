

import asyncio
from asyncio.exceptions import CancelledError
from asyncio.futures import Future
import logging                                    
 
import subprocess
import sys
from enum import Enum

from bleak import BleakClient,BleakScanner,discover
from typing import Dict

from pymadoka.transport import Transport, TransportDelegate
from pymadoka.consts import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID, SEND_MAX_TRIES

logger = logging.getLogger(__name__)

class ConnectionException(Exception):
    """Exceptions are documented in the same way as classes.

    The __init__ method may be documented in either the class level
    docstring, or as a docstring on the __init__ method itself.

    Either form is acceptable, but the two should not be mixed. Choose one
    convention to document the __init__ method and be consistent with it.

     """
    pass


class ConnectionStatus(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    ABORTED = 3

DISCOVERED_DEVICES_CACHE = []

async def discover_devices(timeout=5,adapter="hci0", force_disconnect = True):
    """Trigger a bluetooth devices discovery on the adapter for the timeout interval.
    
    This method must be called before any connection attempt.
    
    Args:
        timeout(int): Timeout used for the device discovery (default 5s)
        adapter (str): Bluetooth adapter
    """
    global DISCOVERED_DEVICES_CACHE

    scanner = BleakScanner(adapter = adapter)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    DISCOVERED_DEVICES_CACHE = await scanner.get_discovered_devices()
    return DISCOVERED_DEVICES_CACHE

async def force_device_disconnect(address):

    """Force a device disconnect so it can be listed during the scan.

    This method relays on the `bluetoothctl` tool to disconnect the device.
    """

    logger.debug("Forcing disconnect...")
    process = await asyncio.create_subprocess_exec(
        "bluetoothctl","disconnect",address, 
        stdout=asyncio.subprocess.PIPE, 
        stderr=asyncio.subprocess.PIPE
        )
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()
    # Progress
    if process.returncode != 0:
        logger.debug(f"Disconnect failed: {stderr.decode().strip()}")

class Connection(TransportDelegate):
    
    """Bluetooth client"""

    client: BleakClient = None

    """This class implements the bluetooth connection to the device.

    It communicates with the device to send and receive data that is passed to the `Transport` to be rebuilt.
    all the features supported by the device and provides methods to operate globally on all the features.
    However, each feature can be queried/updated independently by accesing the feature attributes.

    Attributes:
        client (BleakClient): Bluetooth device client
        transport (`Transport`): Transport used for the protocol
        address (str): MAC address of the device
        name (str): Name of the device when available
        current_future (Future): Future of the current command being processed
        connected (ConnectionStatus): Status of the connection
        adapter (str): Bluetooth adapter used for the client
        
    """

    def __init__(
        self,
        address: str,
        adapter: str
    ):
        """Inits the connection with the device address.

        Args:
            address (str): MAC address of the device
            adapter(str): Bluetooth adapter for the client
        """
        self.adapter = adapter
        self.address = address
        self.name = self.address
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.last_info = None
        self.transport = Transport(self)
        self.current_future = None
        self.requests = {}
        
    def on_disconnect(self, client: BleakClient):
        self.connection_status = ConnectionStatus.DISCONNECTED
        # Put code here to handle what happens on disconnet.
        logger.info(f"Disconnected {self.address}!")
        asyncio.create_task(self.start())
        
    async def cleanup(self):
        if self.client:
            await self.client.stop_notify(NOTIFY_CHAR_UUID)
            await self.client.disconnect()
        self.connection_status = ConnectionStatus.DISCONNECTED

    async def start(self):
        """Starts the connection.
        
        Firstly, the device has to be registered in the Bluez Service so it becomes available via DBUS, so a device scan has to be performed.
        Once the devices are found, the client is registered and connected to the device that matches the device address.

        However, if the device is already connected, it requires to be disconnected so it can be found during the scan, as the device is not listed otherwise.

        Args:
            address (str): MAC address of the device
            force_disconnect (bool): Force a hard disconnect of the device. The device is usually disconnected to ensure a better communication (default True)
            device_discovery_timeout(int): Timeout used for the device discovery (default 5s)
        """
        logger.debug(F"Starting connection manager on {self.address}")
        self.connection_status = ConnectionStatus.CONNECTING
        while (not self.connection_status == ConnectionStatus.CONNECTED and 
               not self.connection_status == ConnectionStatus.ABORTED):
            try:
                if self.client:
                    await self._connect()
                else:
                    await self._select_device()
                await asyncio.sleep(2.0)       
            except ConnectionAbortedError as e:
                 raise e  
            except CancelledError as e:
                 logger.error(str(e))  
    async def _connect(self):
        try:
            await self.client.connect()
            connected = await self.client.is_connected()
            if connected:
                logger.info(F"Connected to {self.address}")
                self.client.set_disconnected_callback(self.on_disconnect)
                self.connection_status = ConnectionStatus.CONNECTED
                await self.client.start_notify(
                    NOTIFY_CHAR_UUID, self.notification_handler,
                )
        
            else:
               logger.info(f"Failed to connect to {self.address.name}")
        except Exception as e:
            if not "Software caused connection abort" in str(e):
                logger.error(e)
            logger.debug("Reconnecting...")

    async def _select_device(self):
        """Scan bluetooth devices searching for the thermostat address so it is registered in the DBUS and available to the client.
        """
        logger.debug("Bluetooh LE hardware warming up...")
    
        for d in DISCOVERED_DEVICES_CACHE:
            if d.address.upper() == self.address.upper(): 
                self.client = BleakClient(d, adapter = self.adapter)
                self.name = d.name
                break
        if self.client == None:
            self.connection_status = ConnectionStatus.ABORTED
            raise ConnectionAbortedError(f"Could not find bluetooth device for the address {self.address}. Please follow the instructions on device pairing.")

    def notification_handler(self, sender: str, data: bytearray):
        """This callback is used to receive the data read from the device (chunks) and attempt to rebuild the message.
        
        Args:
            sender (str) : Client ID
            data (bytearray): Data to be rebuilt
        """
        self.transport.rebuild_chunk(data)
       
    def cmd_id_to_bytes(self,cmd_id:int):
        return bytearray([0x00]) + cmd_id.to_bytes(2,"big")
    def bytes_to_cmd_id(self,data:bytes):
        return int.from_bytes(data[2:4],"big")

    async def send(self,cmd_id:int,data:bytearray):

        """This method is used to send data to the device.
        The `transport` is used to split the data into chunks as required by the communication protocol and these chunks are sent in order to the device.
        
        Args:
            cmd_id (str) : Command ID to be sent
            data (bytearray): Data to be sent
        Returns:
            Future: Callers of this methods must await this Future to receive the result of the command execution
        """

        cmd_response = asyncio.get_event_loop().create_future()
        if not cmd_id in self.requests:
            self.requests[cmd_id] = []

        self.requests[cmd_id].append(cmd_response)

        if self.connection_status is not ConnectionStatus.CONNECTED:
            cmd_response.cancel()
            return cmd_response
    
        # length, 0x00, cmdid, payload
        payload = bytearray([0x00]) + self.cmd_id_to_bytes(cmd_id) + data

        payload[0] = len(payload)

        logger.debug(f"Sending cmd payload: {payload}")
       
        chunks = self.transport.split_in_chunks(payload)
        sent = 0
        
        self.current_cmd_id = cmd_id
        for chunknum,chunk in enumerate(chunks):
            for i in range(0,SEND_MAX_TRIES):
                try:
                    if self.connection_status is not ConnectionStatus.CONNECTED:
                        cmd_response.cancel()
                        return cmd_response
                   
                    await self.client.write_gatt_char(WRITE_CHAR_UUID,chunk)
                    logger.debug(F"CMD {cmd_id}. Chunk #{chunknum+1}/{len(chunks)} sent with size {len(chunk)} bytes")
                    sent += 1
                    break
                except CancelledError as e:
                    logger.debug(F"Send command failed. Retrying ({i}/{SEND_MAX_TRIES}) for chunk #{chunknum} : {str(e)}", exc_info = e)
                    await asyncio.sleep(1)      
                except Exception as e:
                    logger.debug(F"Send command failed. Retrying ({i}/{SEND_MAX_TRIES}) for chunk #{chunknum} : {str(e)}")
                    await asyncio.sleep(1)    

        if sent != len(chunks) and self.connection_status == ConnectionStatus.CONNECTED:
            raise ConnectionException("Command chunks could not be sent")

        return cmd_response

    def response_rebuilt(self,data:bytearray):
        """This callback is used to receive messages rebuilt by the transport. 

        The messages are used to resolve the future used when the command was sent.

        See base class `TransportDelegate`."""

        if len(data)<=4:
            return

        cmd_id = self.bytes_to_cmd_id(data)

        if not cmd_id in self.requests:
            return
        if len(self.requests[cmd_id])>0:
            req = self.requests[cmd_id].pop(0)
            if req.done():
                return
            req.set_result(data)

    def response_failed(self,data:bytearray):
        """This callback is used to cancel the future used when the command was sent.

        See base class `TransportDelegate`."""
        
        if len(data)<=4:
            return

        cmd_id = self.bytes_to_cmd_id(data)

        if not cmd_id in self.requests:
            return

        if len(self.requests[cmd_id])>0:
            req = self.requests[cmd_id].pop(0)
            if req.done():
                return
            req.cancel()
     
    async def read_info(self) -> Dict[str,str]:
        """This method is used to retrieve the information stored in the Bluetooth Services available in the device. 

        This information is related to the Software Version, Hardware Version, Model Number and others.

        Returns:
            Dict[str,str]: Dictionary with all the info values
        """
        try:
            if self.last_info:
                 return self.last_info
            
            if self.connection_status is not  ConnectionStatus.CONNECTED:
                return {}

            values = {}

            for service in self.client.services:
                logger.debug("[Service] {0}: {1}".format(service.uuid, service.description))
                for char in service.characteristics:
                    if "read" in char.properties:
                        try:
                            raw = await self.client.read_gatt_char(char.uuid)
                            value = None
                            
                            try:
                                if char.description.endswith(" ID"): 
                                    value = raw.hex().replace("fe","-").replace("ff","")
                                else:
                                    value = raw.decode()
                            except:
                                value = str(raw)
                            values[char.description] = value
                            logger.debug(
                                "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                                char.uuid,
                                char.handle,
                                ",".join(char.properties),
                                char.description,
                                value,
                            )
                        )
                        except Exception as e:
                            logger.error(e)


            self.last_info = values
            return self.last_info
        except Exception as e:
            logger.error(e)
            raise e
        
if __name__ == "__main__":

    async def main(connection:Connection):
        try:
            await discover_devices()
            start_task = await asyncio.create_task(connection.start())
            connection_status = await asyncio.gather(start_task)
            if connection_status.result() == ConnectionStatus.CONNECTED:
                await connection.client.write_gatt_char(WRITE_CHAR_UUID,[0x00,0x06,0x00,0x20,0x00,0x00])
        except Exception as e:
           logging.error(str(e))
           asyncio.get_event_loop().stop()
        
    logging.basicConfig(level=logging.NOTSET)
    # Create the event loop.
    loop = asyncio.get_event_loop()
    address = sys.argv[1]
    connection = Connection(address )
    try:
        asyncio.ensure_future(main(connection))
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info()
        logging.info("User stopped program.")
   
    finally:
        
        logging.info("Disconnecting...")
        loop.run_until_complete(connection.cleanup())
    
