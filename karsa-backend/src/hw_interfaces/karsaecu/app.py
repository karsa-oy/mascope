import asyncio
import sys
import time

from time import sleep
from .client import AsyncTCPClient

from .messages import Command
from .nodes import DEVICES, NODES, AiNode, DioNode, MfcNode, NodeId, NodeType

KRS_APP_PORT = 65142        # KECU command port



class KarsaClient(AsyncTCPClient):
    def __init__(self):
        super().__init__(KRS_APP_PORT)
        self._node_list = []
        
    async def get_version(self):
        resp = await self.send_cmd_wait_resp(Command.CMD_READ_FW_VERSION.value, [])
        nbytes = len(resp)
        if (nbytes == 2):
            return '{0}.{1}'.format(resp[0], resp[1])
        raise Exception("Failed to get FW version")

    async def get_node_list(self):
        self._node_list = []
        resp = await self.send_cmd_wait_resp(Command.CMD_GET_NODE_LIST.value, [])
        for n in range(0, len(resp), 2):
            node_id = NodeId(resp[n])
            node_type = NodeType(resp[n+1])
            device = DEVICES[node_id]
            node = NODES[node_type](self, device)
            self._node_list.append(node)


async def main():
    '''Main program'''
    tcp = KarsaClient()
    await tcp.connect()

    time.sleep(1)
    await tcp.get_version()
    await tcp.get_node_list()

    # print(tcp._nodeList)
    # print(tcp._nodeTypes)

    if (tcp._nodeCnt > 0):
        for n in range(tcp._nodeCnt):
            time.sleep(1)
            if (tcp._nodeTypes[n] == NodeType.KRS_NODE_TYPE_MFC.value):
                await tcp.startMfcMeas(tcp._nodeList[n], 0x2004, 0x03, 10)
                await tcp.startMfcMeas(tcp._nodeList[n], 0x2503, 0x01, 10)
                await tcp.startMfcMeas(0x00, 0x2C00, 0x01, 30)
                await tcp.startMfcMeas(0x00, 0x2540, 0x01, 30)
            if (tcp._nodeTypes[n] == NodeType.KRS_NODE_TYPE_DIO.value):
                await tcp.startDioMeas(tcp._nodeList[n], 50)
            if (tcp._nodeTypes[n] == NodeType.KRS_NODE_TYPE_AI.value):
                await tcp.startAiMeas(tcp._nodeList[n], 0x03, 30)

        time.sleep(30)

        # tcp.stopMfcMeas(0x00,0x0000,0x00) # stop all measurements from all MFC nodes
        for n in range(tcp._nodeCnt):
            time.sleep(2)
            if (tcp._nodeTypes[n] == NodeType.KRS_NODE_TYPE_MFC.value):
                # tcp.stopMfcMeas(tcp._nodeList[n],0x2004,0x03)
                await tcp.stopMfcMeas(tcp._nodeList[n], 0x0000, 0x00) # stop all measurements from the node
            if (tcp._nodeTypes[n] == NodeType.KRS_NODE_TYPE_DIO.value):
                await tcp.stopDioMeas(tcp._nodeList[n])
            if (tcp._nodeTypes[n] == NodeType.KRS_NODE_TYPE_AI.value):
                await tcp.stopAiMeas(tcp._nodeList[n], 0x03)

    # time.sleep(3)

    if (tcp.connected):
        tcp.close()

    print("exiting")

# Run main.
if __name__ == "__main__":
    asyncio.run(main())
