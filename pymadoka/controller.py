"""This module contains the device controller.
"""
import asyncio
import logging

from typing import Union, Dict
from enum import Enum
from pymadoka.feature import Feature, NotImplementedException
from pymadoka.connection import Connection, ConnectionException, ConnectionStatus
from pymadoka.features.fanspeed import FanSpeed
from pymadoka.features.operationmode import OperationMode
from pymadoka.features.power import PowerState
from pymadoka.features.setpoint import SetPoint
from pymadoka.features.temperatures import Temperatures
from pymadoka.features.clean_filter import CleanFilterIndicator,ResetCleanFilterTimer

logger = logging.getLogger(__name__)


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
    def __init__(self, address: str, adapter: str = "hci0"):
        """Inits the controller with the device address.

        Args:
            address (str): MAC address of the device  
            adapter (str): Bluetooth adapter for the connection
        """


        if adapter is None:
            adapter = "hci0"
        
        self.status = {}
        self.connection = Connection(address,adapter = adapter)
        
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
                    # Small delay to avoid DBUS errors produced when calls are too quick
                    await asyncio.sleep(0.3)
                    await var.query()
                except NotImplementedException as e:
                    pass
                except ConnectionAbortedError:
                    break
                except ConnectionException as e:
                    logger.debug(f"Connection error: {str(e)}")
                    pass
                except Exception as e:
                    logger.error(f"Failed to update {var.__class__.__name__}: {str(e)}")


    
    def refresh_status(self) -> Dict[str,Union[int,str,bool,dict,Enum]]:
        """Collect the status from all the features into a single status dictionary with basic types.

        Returns:
            dict[str,Union[int,str,bool,dict,Enum]]: Dictionary with the status of each feature represented with basic types
        """
        for k,v in vars(self).items():
            if isinstance(v,Feature): 
                if v.status is not None:
                    self.status[k] = vars(v.status)
            
        return self.status

    
    async def read_info(self) -> Dict[str,str]:
        """Reads the device info (Hardware revision, Software revision, Model, Manufacturer, etc)
        Returns:
            Dict[str,str]: Dictionary with the device info
        """
        
        return await self.connection.read_info()
       



    