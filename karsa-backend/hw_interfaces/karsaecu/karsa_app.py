import sys
import os
import socket
import time
import struct

from time import sleep
from karsa_client import *

KRS_APP_PORT = 65142            # The port used by the server

CMD_GET_VERSION = 0x01
CMD_RESET_NODE = 0x02
CMD_GET_NODE_LIST = 0x03
CMD_GET_NODE_DATA = 0x04
CMD_SET_NODE_DATA = 0x05
CMD_START_MFC_MEAS = 0x10
CMD_STOP_MFC_MEAS = 0x11
CMD_START_AI_MEAS = 0x12
CMD_STOP_AI_MEAS = 0x13
CMD_START_DIO_MEAS = 0x14
CMD_STOP_DIO_MEAS = 0x15

KRS_NODE_TYPE_MFC = 0
KRS_NODE_TYPE_DIO = 1
KRS_NODE_TYPE_AI = 2

ALL_NODES = 0x00

KRS_MAX_NODES = 32

class KarsaClient(TCPClient):
    def __init__(self):
        super().__init__(KRS_APP_PORT)
        self._nodeCnt = 0
        self._nodeList = bytearray(KRS_MAX_NODES)
        self._nodeTypes = bytearray(KRS_MAX_NODES)
        
    def getVersion(self):
        nBytes,ver = self.sendCmdWaitResp(CMD_GET_VERSION,[])
        if (nBytes == 2):
            print("Karsa FW version {0}.{1}".format(ver[0],ver[1]))
            return
        print("Failed to read FW version")

    def getNodeList(self):
        self._nodeCnt = 0
        nBytes,resp = self.sendCmdWaitResp(CMD_GET_NODE_LIST,[])
        if (nBytes > 0):
            self._nodeCnt = nBytes >> 1;
            if (self._nodeCnt > 0):
                for n in range(self._nodeCnt):
                    self._nodeList[n] = resp[n*2]
                    self._nodeTypes[n] = resp[n*2+1]
            return
        print("Failed to get Node list")

    def getNodeData(self,nId,obj,subIndex):
        payload = bytearray(4)
        payload[0] = nId
        payload[1] = (obj & 0xFF)
        payload[2] = (obj >> 8)
        payload[3] = subIndex
        nBytes,resp = self.sendCmdWaitResp(CMD_GET_NODE_DATA,payload)
        if (nBytes > 0):
            return nBytes,resp
        print("Failed to get Node 0x{0:02X} data".format(nId))
        return 0, None

    def setNodeData(self,nId,obj,subIndex,l,data):
        payload = bytearray(4+l)
        payload[0] = nId
        payload[1] = (obj & 0xFF)
        payload[2] = (obj >> 8)
        payload[3] = subIndex
        for i in range(0, l):
            payload[4+i] = data & 0xFF
            data >>= 8
        nBytes, resp = self.sendCmdWaitResp(CMD_SET_NODE_DATA,payload)
        if (resp != None and resp[0] == 0x00):
            return False
        print("Failed to Write Data to Node 0x{0:02X}".format(nId))
        return True

    def resetNode(self,nId):
        payload = bytearray(1)
        payload[0] = nId
        nBytes, resp = self.sendCmdWaitResp(CMD_RESET_NODE,payload)
        if (resp != None and resp[0] == 0x00):
            return
        print("Failed to reset Node 0x{0:02X}".format(nId))
        
    def getNodeInfo(self):
        self.getNodeList()
        if (self._nodeCnt > 0):
            print("{0} nodes found".format(self._nodeCnt))
            for n in range(self._nodeCnt):
                print("\nNode 0x{0:02X}, Type {1} :".format(self._nodeList[n],self._nodeTypes[n]))
                nbytes, data = self.getNodeData(self._nodeList[n],0x1008,0x00)
                if (nbytes > 0):
                    print("  Device name : {0}".format(data.decode("utf-8")))
                nbytes, data = self.getNodeData(self._nodeList[n],0x1009,0x00)
                if (nbytes > 0):
                    print("  HW Version  : {0}".format(data.decode("utf-8")))
                nbytes, data = self.getNodeData(self._nodeList[n],0x100A,0x00)
                if (nbytes > 0):
                    print("  SW Version  : {0}".format(data.decode("utf-8")))
        else:
            print("No nodes found")

    def startMfcMeas(self,nId,obj,subIndex,interval):
        payload = bytearray(5)
        payload[0] = nId
        payload[1] = (obj & 0xFF)
        payload[2] = (obj >> 8)
        payload[3] = subIndex
        payload[4] = interval
        nBytes, resp = self.sendCmdWaitResp(CMD_START_MFC_MEAS,payload)
        if (resp != None and resp[0] == 0x00):
            return False, None
        else:
            if (resp != None):
                print("Failed to start MFC measurement, Node 0x{0:02X}, err = 0x{1:02X}".format(nId,resp[0]))
        return True, resp

    def stopMfcMeas(self,nId,obj,subIndex):
        payload = bytearray(4)
        payload[0] = nId
        payload[1] = (obj & 0xFF)
        payload[2] = (obj >> 8)
        payload[3] = subIndex
        nBytes, resp = self.sendCmdWaitResp(CMD_STOP_MFC_MEAS,payload)
        if (resp != None and resp[0] == 0x00):
            return False
        else:
            if (resp != None):
                print("CMD_STOP_MFC_MEAS resp {0}, status = 0x{1:02X}".format(nBytes,resp[0]))
        print("Error stopping MFC measurement")
        return True

    def startAiMeas(self,nId,chMask,interval):
        payload = bytearray(3)
        payload[0] = nId
        payload[1] = chMask
        payload[2] = interval
        nBytes, resp = self.sendCmdWaitResp(CMD_START_AI_MEAS,payload)
        if (resp != None and resp[0] == 0x00):
            return False, None
        else:
            if (resp != None):
                print("Failed to start AI measurement, Node 0x{0:02X}, err = 0x{1:02X}".format(nId,resp[0]))
        return True, resp

    def stopAiMeas(self,nId,chMask):
        payload = bytearray(2)
        payload[0] = nId
        payload[1] = chMask
        nBytes, resp = self.sendCmdWaitResp(CMD_STOP_AI_MEAS,payload)
        if (resp != None and resp[0] == 0x00):
            return False
        else:
            if (resp != None):
                print("CMD_STOP_AI_MEAS resp {0}, status = 0x{1:02X}".format(nBytes,resp[0]))
        print("Error stopping AI measurement")
        return True

    def startDioMeas(self,nId,interval):
        payload = bytearray(2)
        payload[0] = nId
        payload[1] = interval
        nBytes, resp = self.sendCmdWaitResp(CMD_START_DIO_MEAS,payload)
        if (resp != None and resp[0] == 0x00):
            return False, None
        else:
            if (resp != None):
                print("Failed to start DIO measurement, Node 0x{0:02X}, err = 0x{1:02X}".format(nId,resp[0]))
        return True, resp

    def stopDioMeas(self,nId):
        payload = bytearray(1)
        payload[0] = nId
        nBytes, resp = self.sendCmdWaitResp(CMD_STOP_DIO_MEAS,payload)
        if (resp != None and resp[0] == 0x00):
            return False
        else:
            if (resp != None):
                print("CMD_STOP_DIO_MEAS resp {0}, status = 0x{1:02X}".format(nBytes,resp[0]))
        print("Error stopping DIO measurement")
        return True

def main():
    '''Main program'''
    try:
        tcp = KarsaClient()

        time.sleep(1)
        tcp.getVersion()
        tcp.getNodeList()

        if (tcp._nodeCnt > 0):
            for n in range(tcp._nodeCnt):
                time.sleep(1)
                if (tcp._nodeTypes[n] == KRS_NODE_TYPE_MFC):
                    tcp.startMfcMeas(tcp._nodeList[n],0x2004,0x03,10)
                    tcp.startMfcMeas(tcp._nodeList[n],0x2503,0x01,10)
                    tcp.startMfcMeas(0x00,0x2C00,0x01,30)
                    tcp.startMfcMeas(0x00,0x2540,0x01,30)
                if (tcp._nodeTypes[n] == KRS_NODE_TYPE_DIO):
                    tcp.startDioMeas(tcp._nodeList[n],50)
                if (tcp._nodeTypes[n] == KRS_NODE_TYPE_AI):
                    tcp.startAiMeas(tcp._nodeList[n],0x03,30)

            time.sleep(30)

#            tcp.stopMfcMeas(0x00,0x0000,0x00)       # stop all measurements from all MFC nodes
            for n in range(tcp._nodeCnt):
                time.sleep(2)
                if (tcp._nodeTypes[n] == KRS_NODE_TYPE_MFC):
#                    tcp.stopMfcMeas(tcp._nodeList[n],0x2004,0x03)
                    tcp.stopMfcMeas(tcp._nodeList[n],0x0000,0x00)       # stop all measurements from the node
                if (tcp._nodeTypes[n] == KRS_NODE_TYPE_DIO):
                    tcp.stopDioMeas(tcp._nodeList[n])
                if (tcp._nodeTypes[n] == KRS_NODE_TYPE_AI):
                    tcp.stopAiMeas(tcp._nodeList[n],0x03)

        time.sleep(3)

        if (tcp.connected() == True):
            tcp.close()

    except Exception:
        print("Connection to Karsa Application port failed")
    finally:
        print("exiting")

# Run main.
if __name__ == "__main__":
    sys.exit(main())
