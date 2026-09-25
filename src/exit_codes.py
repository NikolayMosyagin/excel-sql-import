from enum import IntEnum


class ExitCodes(IntEnum):
    SUCCESS = 0
    CRITICAL_ERROR = 1
    NO_SOURCE_DATA = 2