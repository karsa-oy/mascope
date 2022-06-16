from .client import AsyncTCPClient
from .devices import DEVICES
from .messages import Command
from .nodes import NODES, NodeId, NodeType

import logging
logger = logging.getLogger(__name__)


class KarsaClient(AsyncTCPClient):
    def __init__(self, host, port, parent):
        """Wrapper for TCP client

        Implements some convenience methods and
        handlers for some notification messages.

        Parameters
        ----------
        host : str
            KECU IP address
        port : int
            KECU TCP port
        """
        super().__init__(host, port, parent)
        self.kecu = parent
        self._nodes = {}
        self._version = None

    @property
    def nodes(self) -> dict:
        return self._nodes
        
    async def get_version(self):
        resp = await self.send_cmd_wait_resp(
            Command.CMD_READ_FW_VERSION.value,
            []
            )
        nbytes = len(resp)
        if (nbytes == 2):
            self._version = '{0}.{1}'.format(resp[0], resp[1])
        else:
            self._version = "unknown"
            logger.error("Failed to get FW version")

    async def get_node_list(self):
        """Update list of nodes present
        """
        self._nodes = {}
        resp = await self.send_cmd_wait_resp(
            Command.CMD_GET_NODE_LIST.value,
            []
            )
        for n in range(0, len(resp), 2):
            node_id = NodeId(resp[n])
            node_type = NodeType(resp[n+1])
            device = DEVICES[node_id]
            node = NODES[node_type](self, device)
            self._nodes.update({node_id: node})

    async def init_nodes(self):
        for node in self._nodes.values():
            await node.initialize()

    async def on_NTF_NODE_INSERTED(self, node_id, data):
        """Handler for NTF_NODE_INSERTED
        """
        node_id = NodeId(node_id)
        node_type = NodeType(data[0])
        device = DEVICES[node_id]
        node = NODES[node_type](self, device)
        self._nodes.update({node_id: node})
        await node.initialize()
        self.nodes = self._nodes
    
    async def on_NTF_NODE_REMOVED(self, node_id, data):
        """Handler for NTF_NODE_REMOVED
        """
        self._nodes.pop(node_id)
        self.nodes = self._nodes
