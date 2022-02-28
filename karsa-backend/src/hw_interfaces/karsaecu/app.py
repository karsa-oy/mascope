from client import AsyncTCPClient

from messages import Command
from nodes import DEVICES, NODES, NodeId, NodeType


class KarsaClient(AsyncTCPClient):
    def __init__(self, host, port):
        super().__init__(host, port)
        self._node_dict = {}
        
    async def get_version(self):
        resp = await self.send_cmd_wait_resp(Command.CMD_READ_FW_VERSION.value, [])
        nbytes = len(resp)
        if (nbytes == 2):
            return '{0}.{1}'.format(resp[0], resp[1])
        raise Exception("Failed to get FW version")

    async def get_node_list(self):
        self._node_dict = {}
        resp = await self.send_cmd_wait_resp(Command.CMD_GET_NODE_LIST.value, [])
        for n in range(0, len(resp), 2):
            node_id = NodeId(resp[n])
            node_type = NodeType(resp[n+1])
            device = DEVICES[node_id]
            node = NODES[node_type](self, device)
            self._node_dict.update({node_id: node})

    async def on_NODE_INSERTED(self, node_id):
        pass
    
    async def on_NODE_REMOVED(self, node_id):
        pass