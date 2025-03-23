from enum import Enum, auto


class ShutdownStatus(Enum):
    OK = auto()
    TIMEOUT = auto()
