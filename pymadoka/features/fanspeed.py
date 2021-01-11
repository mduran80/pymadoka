"""This module contains the classes used to control the Fan Speed feature
"""

from enum import Enum
from typing import Dict
from pymadoka.feature import Feature, FeatureStatus
from pymadoka.connection import Connection

class FanSpeedEnum(Enum):
    HIGH = 5
    MID = 3
    LOW = 1
    AUTO = 0
    def __str__(self):
        return self.name

class FanSpeedStatus(FeatureStatus):

    """
    This class is used to store the Fan Speed status.
    
    Attributes:
        cooling_fan_speed (FanSpeedEnum): Cooling fan speed
        heating_fan_speed (FanSpeedEnum): Heating fan speed
       
    """

    COOLING_IDX = 0x20
    HEATING_IDX = 0x21

    def __init__(self,cooling_fan_speed:FanSpeedEnum, heating_fan_speed:FanSpeedEnum):
        """Inits with the cooling and heating fan speeds.

        Args:
            cooling_fan_speed (FanSpeedEnum): Cooling fan speed
            cooling_fan_speed (FanSpeedEnum): Heating fan speed
        """
        self.cooling_fan_speed = cooling_fan_speed
        self.heating_fan_speed = heating_fan_speed
   
    def set_values(self, values:Dict[str,bytearray]):
        """See base class."""
        cooling_value = int.from_bytes(values[self.COOLING_IDX],"big")
        heating_value = int.from_bytes(values[self.HEATING_IDX],"big")

        if cooling_value>=2 and cooling_value<=4:
            self.cooling_fan_speed = FanSpeedEnum.MID
        else:
            self.cooling_fan_speed = FanSpeedEnum(cooling_value)

        if heating_value>=2 and heating_value<=4:
            self.heating_fan_speed = FanSpeedEnum.MID
        else:
            self.heating_fan_speed = FanSpeedEnum(heating_value)
        
    def get_values(self) -> Dict[str,bytearray]:
        """See base class."""
        values = {}
        values[self.COOLING_IDX] = self.cooling_fan_speed.value.to_bytes(1,"big")
        values[self.HEATING_IDX] = self.heating_fan_speed.value.to_bytes(1,"big")
        return values

class FanSpeed(Feature):
    """
    This class is used to control the Fan Speed.

    Attributes:
        status (FanSpeedStatus): Current status
    """
    def __init__(self, connection: Connection):
        """See base class."""
        self.status = None
        super().__init__(connection)

    def query_cmd_id(self) -> int:
        """See base class."""
        return 80
    
    def update_cmd_id(self) -> int:
        """See base class."""
        return 16464

    def new_status(self) -> FeatureStatus:
        """See base class."""
        return FanSpeedStatus(FanSpeedEnum.AUTO,FanSpeedEnum.AUTO)
