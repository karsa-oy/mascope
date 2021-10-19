from enum import Enum

STX = 0x02      # Start byte
ETX = 0x03      # End byte

# Command message minimum length
APP_CMD_MIN_LEN = 4     # STX (1) + CMD (1) + LEN (1) + ETX (1)

# Reply (to command) message minimum length
APP_RSP_MIN_LEN = 5     # STX (1) + CMD (1) + LEN (1) + STATUS (1) + ETX (1)

# Notification message minimum length
MIN_MEAS_MSG_SIZE = 6   # DIO Data : Header (4) + Node (1) + data (1)

# Notification message header lemgth
MEAS_MSG_HEADER_LEN = 4 # STX (1) + CMD (1) + LEN (1) + ETX (1)


class Command(Enum):
    # Command messages
    CMD_READ_FW_VERSION = 0x01
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
    # //


class Notification(Enum):
    # Notification messages
    NTF_AI_MEAS_DATA_CH_1_4 = 0x80
    NTF_AI_MEAS_DATA_CH_5_6 = 0x81
    NTF_DIO_MEAS_DATA = 0x82
    NTF_MFC_MEAS_DATA = 0x83

    NTF_NODE_INSERTED = 0x90
    NTF_NODE_REMOVED = 0x91
    # //