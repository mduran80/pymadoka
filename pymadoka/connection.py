

import asyncio
from asyncio.futures import Future
import logging                                    

import subprocess
from os import popen
import sys

from bleak import BleakClient,discover
from typing import Callable, Any, Dict

from pymadoka.transport import Transport, TransportDelegate
from pymadoka.consts import SERVICE_UUID, NOTIFY_CHAR_UUID, WRITE_CHAR_UUID, SEND_MAX_TRIES


class ConnectionException(Exception):
    """Exceptions are documented in the same way as classes.

    The __init__ method may be documented in either the class level
    docstring, or as a docstring on the __init__ method itself.

    Either form is acceptable, but the two should not be mixed. Choose one
    convention to document the __init__ method and be consistent with it.

     """
    pass


class Connection(TransportDelegate):
    
    """Bluetooth client"""

    client: BleakClient = None

    """This class implements the bluetooth connection to the device.

    It communicates with the device to send and receive data that is passed to the `Transport` to be rebuilt.
    all the features supported by the device and provides methods to operate globally on all the features.
    However, each feature can be queried/updated independently by accesing the feature attributes.

    Attributes:
        client (BleakClient): Bluetooth device client
        adapter (str): Bluetooth adapter
        transport (`Transport`): Transport used for the protocol
        address (str): MAC address of the device
        current_future (Future): Future of the current command being processed
        connected (bool): True if connected, False otherwise
        force_disconnect (bool): Force a hard disconnect of the device. The device is usually disconnected to ensure a better communication (default True)
        device_discovery_timeout(int): Timeout used for the device discovery (default 5s)
    """

    def __init__(
        self,
        address: str,
        adapter: str,
        force_disconnect: bool = True,
        device_discovery_timeout: int = 5
    ):
        """Inits the connection with the device address.

        Args:
            address (str): MAC address of the device
            adapter (str): Bluetooth adapter
            force_disconnect (bool): Force a hard disconnect of the device. The device is usually disconnected to ensure a better communication, in Linux at least (default True)
            device_discovery_timeout(int): Timeout used for the device discovery (default 5s)
        """
        self.address = address
        self.adapter = adapter
        self.connected = False
        self.last_info = None
        self.transport = Transport(self)
        self.current_future = None
        self.force_disconnect = force_disconnect
        self.device_discovery_timeout = device_discovery_timeout

    def on_disconnect(self, client: BleakClient):
        self.connected = False
        # Put code here to handle what happens on disconnet.
        logging.info(f"Disconnected {self.address}!")

    async def cleanup(self):
        if self.client:
            await self.client.stop_notify(NOTIFY_CHAR_UUID)
            await self.client.disconnect()

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
        logging.info(F"Starting connection manager on {self.address}")
        while not self.connected:
            if self.client:
                await self.connect()
            else:
                await self.select_device()
            await asyncio.sleep(1.0)       

    def hard_disconnect(self):
        """Force a device disconnect so it can be listed during the scan.

        This method relays on the `bluetoothctl` tool to disconnect the device.
        """

        logging.debug("Forcing disconnect...")
        try:
            subprocess.run(["bluetoothctl","disconnect",self.address],check= True,capture_output=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Could not disconnect device: {e.stdout}")

    async def connect(self):
        """Connect to the device.
        
        Once the connection is made, two callbacks are installed:
            - On the RX Bluetooth Characteristic UUID used by the UART service.
            - On the client disconnect event

        """
        if self.connected:
            return
        try:
            await self.client.connect()
            self.connected = await self.client.is_connected()
            if self.connected:
                logging.info(F"Connected to {self.address}")
                self.client.set_disconnected_callback(self.on_disconnect)

                await self.client.start_notify(
                    NOTIFY_CHAR_UUID, self.notification_handler,
                )
            else:
               logging.info(f"Failed to connect to {self.address.name}")
        except Exception as e:
            if not "Software cause connection abort" in str(e):
                logging.error(e)
            logging.info("Reconnecting...")

    async def select_device(self):
        """Scan bluetooth devices searching for the thermostat address so it is registered in the DBUS and available to the client.
        """
        logging.info("Bluetooh LE hardware warming up...")
        #await asyncio.sleep(2.0) # Wait for BLE to initialize.
        # Force disconnect to make it discoverable

        if self.force_disconnect:
            self.hard_disconnect()

        devices = await discover(timeout = self.device_discovery_timeout, adapter = self.adapter)
        for d in devices:
            if d.address == self.address: 
                self.client = BleakClient(d, adapter = self.adapter)
                break
       
    def notification_handler(self, sender: str, data: bytearray):
        """This callback is used to receive the data read from the device (chunks) and attempt to rebuild the message.
        
        Args:
            sender (str) : Client ID
            data (bytearray): Data to be rebuilt
        """
        self.transport.rebuild_chunk(data)
       
    async def send(self,cmd_id:int,data:bytearray)-> Future:

        """This method is used to send data to the device.
        The `transport` is used to split the data into chunks as required by the communication protocol and these chunks are sent in order to the device.
        
        Args:
            cmd_id (str) : Command ID to be sent
            data (bytearray): Data to be sent
        Returns:
            Future: Callers of this methods must await this Future to receive the result of the command execution
        """

       # length, 0x00, cmdid, payload
        payload = bytearray([0x00,0x00]) + cmd_id.to_bytes(2,"big") + data
        payload[0] = len(payload)

        logging.debug(f"Sending cmd payload: {payload}")
       
        chunks = self.transport.split_in_chunks(payload)
        sent = 0
        self.current_cmd_id = cmd_id
        for chunknum,chunk in enumerate(chunks):
            for i in range(0,SEND_MAX_TRIES):
                try:
                    if not self.connected:
                        await self.connect()
                    await self.client.write_gatt_char(WRITE_CHAR_UUID,chunk)
                    logging.debug(F"CMD {cmd_id}. Chunk #{chunknum+1}/{len(chunks)} sent with size {len(chunk)} bytes")
                    sent += 1
                    break
                except Exception as e:
                    logging.warn(F"Send command failed. Retrying ({i}/{SEND_MAX_TRIES}) for chunk #{chunknum} : {str(e)}")
                    await asyncio.sleep(1)    

        if sent != len(chunks):
            raise ConnectionException("Command chunks could not be sent")

        self.cmd_response = asyncio.futures.Future()
       
        return self.cmd_response

    def response_rebuilt(self,data:bytearray):
        """This callback is used to receive messages rebuilt by the transport. 

        The messages are used to resolve the future used when the command was sent.

        See base class `TransportDelegate`."""
        self.cmd_response.set_result(data)

    def response_failed(self):
        """This callback is used to cancel the future used when the command was sent.

        See base class `TransportDelegate`."""
        self.cmd_response.cancel()

    async def read_info(self) -> Dict[str,str]:
        """This method is used to retrieve the information stored in the Bluetooth Services available in the device. 

        This information is related to the Software Version, Hardware Version, Model Number and others.

        Returns:
            Dict[str,str]: Dictionary with all the info values
        """
        try:
            if self.last_info:
                 return self.last_info


            if not self.connected:
                await self.connect()
            
            values = {}

            for service in self.client.services:
                logging.debug("[Service] {0}: {1}".format(service.uuid, service.description))
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
                            logging.debug(
                                "\t[Characteristic] {0}: (Handle: {1}) ({2}) | Name: {3}, Value: {4} ".format(
                                char.uuid,
                                char.handle,
                                ",".join(char.properties),
                                char.description,
                                value,
                            )
                        )
                        except Exception as e:
                            logging.error(e)


            self.last_info = values
            return self.last_info
        except Exception as e:
            logging.error(e)
            raise e
        
if __name__ == "__main__":

    async def main(connection:Connection):
        delay = 30
        while not connection.connected:
            logging.info(F"Device not ready. Waiting {delay}s...")
            await asyncio.sleep(delay)
        await connection.client.write_gatt_char(WRITE_CHAR_UUID,[0x00,0x06,0x00,0x20,0x00,0x00])

    logging.basicConfig(level=logging.NOTSET)
    # Create the event loop.
    loop = asyncio.get_event_loop()
    address = sys.argv[1]
    connection = Connection(address )
    try:
        asyncio.ensure_future(connection.start())
        asyncio.ensure_future(main(connection))
        loop.run_forever()
    except KeyboardInterrupt:
        print()
        print("User stopped program.")
    finally:
        print("Disconnecting...")
        loop.run_until_complete(connection.cleanup())
    
