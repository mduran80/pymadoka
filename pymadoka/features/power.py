"""This module contains the classes used to control the Power feature (turn HVAC on/off)
"""

from typing import Dict
from pymadoka.feature import Feature, FeatureStatus
from pymadoka.connection import Connection

class PowerStateStatus(FeatureStatus):

    """
    This class is used to store the Power State status.
    
    Attributes:
        turn_on (bool): True if the HVAC is turned on, False otherwise
       
    """

    DATA_IDX = 0x20
    
    def __init__(self,turn_on:bool):
        """Inits with the power state.
        
        Attributes:
           turn_on (bool): True if the HVAC is turned on, False otherwise
        """
        self.turn_on = turn_on
    
    def set_values(self, values:Dict[str,bytearray]):
        """See base class."""
        self.turn_on = values[self.DATA_IDX][0] == 0x01
        
    def get_values(self) -> Dict[str,bytearray]:
        """See base class."""
        values = {}
        values[self.DATA_IDX] = bytes([0x01]) if self.turn_on else bytes([0x00])
        return values

class PowerState(Feature):

    """
    This class is used to control the HVAC Power (turn on/off)

    Attributes:
        status (PowerStateStatus): Current status
    """
    def __init__(self, connection: Connection):
        """See base class."""
        self.status = None
        super().__init__(connection)

    def query_cmd_id(self) -> int:
        """See base class."""
        return 32
    
    def update_cmd_id(self) -> int:
        """See base class."""
        return 16416

    def new_status(self) -> FeatureStatus:
        """See base class."""
        return PowerStateStatus(False)
