from enum import Enum

# Message format specifications, refer to interface document
STX = 0x02      # Start byte
ETX = 0x03      # End byte

# Command message minimum length
APP_CMD_MIN_LEN = 4     # STX (1) + CMD (1) + LEN (1) + ETX (1)

# Reply (to command) message minimum length
APP_RSP_MIN_LEN = 5     # STX (1) + CMD (1) + LEN (1) + STATUS (1) + ETX (1)

# Notification message minimum length
MIN_MEAS_MSG_SIZE = 5   # STX (1) + Type (1) + LEN (1) + data (1) + ETX (1)

# Notification message header lemgth
MEAS_MSG_HEADER_LEN = 4 # STX (1) + CMD (1) + LEN (1) + ETX (1)


class Command(Enum):
    """Command messages
    
    Refer to interface specification
    """
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
    CMD_START_HV_MEAS = 0x16
    CMD_STOP_HV_MEAS = 0x17
    CMD_START_VALVE_MEAS = 0x18
    CMD_STOP_VALVE_MEAS = 0x19


class Notification(Enum):
    """Notification messages
    
    Refer to interface specification
    """
    NTF_AI_MEAS_DATA_CH_1_4 = 0x80
    NTF_AI_MEAS_DATA_CH_5_6 = 0x81
    NTF_DIO_MEAS_DATA = 0x82
    NTF_MFC_MEAS_DATA = 0x83
    NTF_HV_MEAS_DATA = 0x84
    NTF_VALVE_MEAS_DATA = 0x85

    NTF_NODE_INSERTED = 0x90
    NTF_NODE_REMOVED = 0x91