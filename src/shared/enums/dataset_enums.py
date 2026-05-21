from enum import Enum

class DatasetRole(str, Enum):
    ACTIVE = "active"
    DECAYED = "decayed"