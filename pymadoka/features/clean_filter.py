"""This module contains the classes used to control the Clean Filter feature (indicator status and reset indicator)
"""

from typing import Dict
from pymadoka.feature import Feature, FeatureStatus, NotImplementedException
from pymadoka.connection import Connection

class ResetCleanFilterTimerStatus(FeatureStatus):

    """
    This class is used to store the parameters used to reset the Clean Filter Indicator.
    """
    CLEAN_FILTER_TIMER_RESET_IDX = 0xFE

    def set_values(self, values):
        """See base class."""
        pass  

    def get_values(self):
        """See base class."""
        values = {}
        values[self.CLEAN_FILTER_TIMER_RESET_IDX] = bytes([0x01])
       
        return values


class ResetCleanFilterTimer(Feature):
    """
    This class is used to reset the Clean Filter Indicator.

    Attributes:
        status (ResetCleanFilterTimerStatus): Current status
    """

    def __init__(self, connection: Connection):
        """See base class."""
        self.status = None
        super().__init__(connection)

    def query_cmd_id(self) -> int:
        """See base class.
        
        Raises:
            NotImplementedException: This feature cannot be queried
        """
        raise NotImplementedException("This feature cannot be queried")
    
    def update_cmd_id(self)-> int:
        """See base class."""
        16928

    def new_status(self) -> FeatureStatus:
        """See base class."""
        return ResetCleanFilterTimerStatus()


class CleanFilterIndicatorStatus(FeatureStatus):

    """
    This class is used to store the Clean Filter Indicator status.
    
    Attributes:
        clean_filter_indicator (bool): True if indicator is turned on, False otherwise   
    """
    CLEAN_FILTER_IDX = 0x62
 
    def __init__(self,clean_filter_indicator: bool):
        """Inits with the clean filter indicator state.
        
        Attributes:
           clean_filter_indicator (bool): True if the indicator is turned on, False otherwise
        """
        self.clean_filter_indicator = clean_filter_indicator
   
    def set_values(self, values:Dict[int,bytearray]):
        """See base class."""
        self.clean_filter_indicator = values[self.CLEAN_FILTER_IDX][0] & 0x01 == 0x01
        
    def get_values(self) -> Dict[int,bytearray]:
        """See base class."""
        return {self.CLEAN_FILTER_IDX:bytes([0x00])}

class CleanFilterIndicator(Feature):

    """
    This class is used to retrieve the Clean Filter Indicator status.

    Attributes:
        status (CleanFilterIndicatorStatus): Current status
    """
    def __init__(self, connection: Connection):
        """See base class."""
        self.status = None
        super().__init__(connection)

    def query_cmd_id(self) -> int:
        """See base class."""
        return 256
    
    def update_cmd_id(self) -> int:
        """See base class.
        
        Raises:
            NotImplementedException: This feature cannot be updated
        """
        raise NotImplementedException("This feature cannot be updated")

    def new_status(self) -> FeatureStatus:
        """See base class."""
        return CleanFilterIndicatorStatus(False)
