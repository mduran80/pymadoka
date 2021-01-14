"""This module encapsulates the data transfer protocol requirements defined by the device
"""

import logging
import math
import typing
from abc import ABC,abstractmethod


"""
Data transfer size 
"""
MAX_CHUNK_SIZE = 20

logger = logging.getLogger(__name__)

class TransportDelegate(ABC):
    """
    This interface defines the methods used by the Transport to notify the result of the rebuild process.
    """

    """Callback method used when a message has been sucessfully rebuilt.
         
    Args:
        data (bytearray): Rebuilt message data
    """
    @abstractmethod
    def response_rebuilt(self,data:bytearray):
        pass

    """Callback method used when the stored chunks of a message have been discarded.  
    """
    @abstractmethod
    def response_failed(self):
        pass


class Transport:

    """This class encapsulates the data packetizing required by the device (max 20 bytes per package as described in the protocol).

    Therefore, bigger data has to be split into smaller chunks and sent done in sequence.
    The implementation assumes we will receive all the chunks in order as they are being sent in serial order
    However, this will not work if more than one client is attached to the same device
         
    Attributes:
        delegate (`TransportDelegate`): The delegate to be notified when the a message has been rebuilt or discarded.
        chunks (List[bytearray]): Current rebuild chunks data
        last_id (int): ID of the last chunk stored in the list. This is used to check if newly received chunks follow the sequence
    """
    def __init__(self, delegate:TransportDelegate):
        """Inits the transport with the delegate.
        
        Args:
            delegate (`TransportDelegate`): The delegate to be notified when the a message has been rebuilt or discarded.
        """
        self.chunks:list(bytearray) = []
        self.delegate = delegate
        self.last_id = None
        

    def clear(self):
        """
        Clear the list of chunks
        """
        self.chunks.clear()


    def is_message_complete(self) -> bool:
        """Check if the stored chunks can be used to rebuild a message.

        Returns:
            bool: The return value. True for success, False otherwise.
        """
        if len(self.chunks) <= 0:
            return False
        
        expected_size = math.ceil(self.chunks[0][1] / MAX_CHUNK_SIZE)
       
        if len(self.chunks) != expected_size:
            return False

        return True

    def rebuild_chunk(self, chunk:bytearray):
        """Process the chunk.
         
            - The chunk has an id that follows the sequence of the stored chunks .If the message is complete, the delegate is notified
            - The chunk has an id that belongs to a different message .Current chunks are discarded and the delegate is notified

        Args:
            chunk (bytearray): The chunk data to be processed
        """
        if len(chunk) < 2:
            logger.info(F"Chunk received but discarded due to not enough data ({len(chunk)} bytes)")
            return
        
        chunk_id = chunk[0]
        
        if self.last_id is not None and chunk_id <= self.last_id:
            logger.debug("Chunks of a new message received while rebuilding another message. Discarding previous chunks...") 
            out = self.chunks_data()
            self.delegate.response_failed(out)


        self.last_id = chunk[0]
        
        self.chunks.append(chunk)
        
        if self.is_message_complete(): 

            logger.debug("Message complete. Processing...")
            out = self.chunks_data()
            self.last_id = None
            self.delegate.response_rebuilt(out)


    def chunks_data(self):
        out = bytearray()
        
        for c in self.chunks:
            out.extend(c[1:])
        self.chunks.clear()

        return out

    def split_in_chunks(self, data:bytearray) -> typing.List[bytearray]:
        """Split the data in MAX_CHUNK_SIZE bytes chunks. If more than one chunk is produced, numerate each chunk in the sequence.
        
        Args:
            data (bytearray): The data to be split
        Returns:
            List[bytearray]: List of chunks
        """
        chunks:list(bytearray) = []

        idx = 0
        while True:
            chunk = data[idx*19:min((idx+1)*19,len(data))]
            chunks.append(bytearray(idx.to_bytes(1,"big")) + chunk)
            idx+=1
            if idx*19 >= len(data):
                break

        return chunks
          