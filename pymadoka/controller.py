"""This module contains the device controller.
"""
import asyncio
import logging

from typing import Union, Dict
from enum import Enum
from pymadoka.feature import Feature
from pymadoka.connection import Connection
from pymadoka.features.fanspeed import FanSpeed
from pymadoka.features.operationmode import OperationMode
from pymadoka.features.power import PowerState
from pymadoka.features.setpoint import SetPoint
from pymadoka.features.temperatures import Temperatures
from pymadoka.features.clean_filter import CleanFilterIndicator,ResetCleanFilterTimer

class Controller:
    """This class implements the device controller.
    It stores all the features supported by the device and provides methods to operate globally on all the features.
    However, each feature can be queried/updated independently by accesing the feature attributes.

    Attributes:
        status (dict[string,FeatureStatus]): Last status collected from the features
        connection (Connection): Connection used to communicate with the device
        fan_speed (Feature): Feature used to control the fan speed
        operation_mode (Feature): Feature used to control the fan speed
        power_state (Feature): Feature used to control the fan speed
        set_point (Feature): Feature used to control the fan speed
        set_point (Feature): Feature used to control the fan speed
        clean_filter_indicator (Feature): Feature used to control the fan speed
    """
    def __init__(self, address: str, adapter: str, force_disconnect = None, device_discovery_timeout = None):
        """Inits the controller with the device address.

        Args:
            address (str): MAC address of the device
            adapter (str): Bluetooth adapter
            force_disconnect (bool): Force a hard disconnect of the device. The device is usually disconnected to ensure a better communication (default True)
            device_discovery_timeout(int): Timeout used for the device discovery (default 5s)
        """

        if force_disconnect is None:
            force_disconnect = True
        if device_discovery_timeout is None:
            device_discovery_timeout = 5
        
        if adapter is None:
            adapter = "hci0"
        
        self.status = {}
        self.connection = Connection(address,adapter = adapter, force_disconnect = force_disconnect, device_discovery_timeout = device_discovery_timeout)
        
        self.fan_speed = FanSpeed(self.connection)
        self.operation_mode = OperationMode(self.connection)
        self.power_state = PowerState(self.connection)
        self.set_point = SetPoint(self.connection)
        self.temperatures = Temperatures(self.connection)
        self.clean_filter_indicator = CleanFilterIndicator(self.connection)
        self.reset_clean_filter_timer = ResetCleanFilterTimer(self.connection)

    async def start(self):
        """Start the connection to the device.
        """        
        await self.connection.start()
        while not self.connection.connected: 
            logging.info("Awaiting connection (5s)...")
            await asyncio.sleep(5)
    
    async def stop(self):
        """Stop the connection.
        """ 
        await self.connection.cleanup()
    
    async def update(self):
        """Iterate over all the features and query their status.
        """ 
        for var in vars(self).values():
            if isinstance(var,Feature): 
                try:
                    await var.query()
                except NotImplemented as e:
                    pass
                except Exception as e:
                    logging.error(f"Failed to update {var.__class__.__name__}: {str(e)}")


    
    def refresh_status(self) -> Dict[str,Union[int,str,bool,dict,Enum]]:
        """Collect the status from all the features into a single status dictionary with basic types.

        Returns:
            dict[str,Union[int,str,bool,dict,Enum]]: Dictionary with the status of each feature represented with basic types
        """
        for var in vars(self).values():
            if isinstance(var,Feature): 
                try:
                    if var.status is not None:
                        self.status[var.__class__.__name__] = vars(var.status)
                except NotImplemented as e:
                    pass
                except Exception as e:
                    logging.error(f"Failed to update {var.__class__.__name__}: {str(e)}")
        return self.status

    
    async def read_info(self) -> Dict[str,str]:
        """Reads the device info (Hardware revision, Software revision, Model, Manufacturer, etc)
        Returns:
            Dict[str,str]: Dictionary with the device info
        """
        return await self.connection.read_info()



    