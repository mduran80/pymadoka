"""This module contains the classes used to control the Operation Mode feature
"""
from enum import Enum
from typing import Dict
from pymadoka.feature import Feature, FeatureStatus
from pymadoka.connection import Connection

class OperationModeEnum(Enum):
     FAN = 0
     DRY = 1
     AUTO = 2
     COOL = 3
     HEAT = 4
     VENTILATION = 5
     def __str__(self):
        return self.name


class OperationModeStatus(FeatureStatus):

    """
    This class is used to store the Operation Mode status.
    
    Attributes:
        operation_mode (OperationModeEnum): Operation mode
       
    """

    DATA_IDX = 0x20
    
    def __init__(self,value:OperationModeEnum):
        """Inits with the operation mode.
        
        Attributes:
            operation_mode (OperationModeEnum): Operation mode
        """
        self.operation_mode = value
    
    def set_values(self, values:Dict[str,bytearray]):
        """See base class."""
        self.operation_mode = OperationModeEnum(int.from_bytes(values[self.DATA_IDX],"big"))
        
    def get_values(self) -> Dict[str,bytearray]:
        """See base class."""
        values = {}
        values[self.DATA_IDX] = self.operation_mode.value.to_bytes(1,"big")
        return values

class OperationMode(Feature):
    """
    This class is used to control the Operation Mode.

    Attributes:
        status (OperationModeStatus): Current status
    """
    def __init__(self, connection: Connection):
        """See base class."""
        self.status = None
        super().__init__(connection)

    def query_cmd_id(self) -> int:
        """See base class."""
        return 48
    
    def update_cmd_id(self) -> int:
        """See base class."""
        return 16432

    def new_status(self) -> FeatureStatus:
        """See base class."""
        return OperationModeStatus(OperationModeEnum.AUTO)
