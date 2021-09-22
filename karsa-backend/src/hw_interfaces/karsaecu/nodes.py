from enum import Enum


KRS_MAX_NODES = 32  # Maximum number of nodes

class NodeId(Enum):
    # Node IDs
    ALL_NODES = 0x00    # Node ID for "all nodes"
    # //

class NodeType(Enum):
    # Node types
    KRS_NODE_TYPE_MFC = 0
    KRS_NODE_TYPE_DIO = 1
    KRS_NODE_TYPE_AI = 2
    KRS_NODE_TYPE_UNKNOWN = 255
    # //


class BaseNode():
    def __init__(self, client):
        self._client = client
        self._id = NodeId.ALL_NODES
        self._type = NodeType.KRS_NODE_TYPE_UNKNOWN

    async def get_hw_version(self):
        data = await self.client.getNodeData(self._id,
                                             0x1009,
                                             0x00
                                             )
        if data:
            return data
        else:
            raise

    async def get_name(self):
        data = await self.client.getNodeData(self._id,
                                             0x1008,
                                             0x00
                                             )
        if data:
            return data
        else:
            raise
    
    async def get_sw_version(self):
        data = await self.client.getNodeData(self._id, 
                                             0x100A,
                                             0x00
                                             )
        if data:
            return data
        else:
            raise

    


class AiNode(BaseNode):
    def __init__(self, id):
        self._id = id
        self._type = NodeType.KRS_NODE_TYPE_AI

class DioNode(BaseNode):
    def __init__(self, id):
        self._id = id
        self._type = NodeType.KRS_NODE_TYPE_DIO

class MfcNode(BaseNode):
    def __init__(self, id):
        self._id = id
        self._type = NodeType.KRS_NODE_TYPE_MFC