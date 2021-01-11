"""This module contains the classes used to control the Set Point feature (temperatures set by the user)
"""

from typing import Dict
from pymadoka.feature import Feature, FeatureStatus
from pymadoka.connection import Connection

class SetPointStatus(FeatureStatus):
    """
    This class is used to store the Set Point temperatures.
    
    The values must be set as in Celsius degrees and are converted to the device format when read/written.

    No ranges validation is performed.

    Attributes:
        cooling_set_point (int): Cooling set point
        heating_set_point (int): Heating set point
    """

    COOLING_IDX = 0x20
    HEATING_IDX = 0x21

    def __init__(self,cooling_set_point:int, heating_set_point:int):
        """Inits the status with the set points
        
        Args: 
            cooling_set_point (int): Cooling set point
            heating_set_point (int): Heating set point
        """
        self.cooling_set_point = cooling_set_point
        self.heating_set_point = heating_set_point
   
    def set_values(self, values:Dict[str,bytearray]):
        """See base class."""
        self.cooling_set_point = round(int.from_bytes(values[self.COOLING_IDX],"big")/128.0)
        self.heating_set_point = round(int.from_bytes(values[self.HEATING_IDX],"big")/128.0)
        
    def get_values(self) -> Dict[str,bytearray]:
        """See base class."""
        values = {}
        values[self.COOLING_IDX] = (self.cooling_set_point*128).to_bytes(2,"big")
        values[self.HEATING_IDX] = (self.heating_set_point*128).to_bytes(2,"big")
        return values

class SetPoint(Feature):
    """
    This class is used to control the Set Point temperatures (temperatures set by the user)

    Attributes:
        status (SetPointStatus): Current status
    """
    def __init__(self, connection: Connection):
        """See base class."""
        self.status = None
        super().__init__(connection)

    def query_cmd_id(self) -> int:
        """See base class."""
        return 64
    
    def update_cmd_id(self) -> int:
        """See base class."""
        return 16448

    def new_status(self) -> FeatureStatus:
        """See base class."""
        return SetPointStatus(0,0)
