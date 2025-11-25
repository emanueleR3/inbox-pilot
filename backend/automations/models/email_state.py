from enum import Enum

class EmailStatus(Enum):
    HIGH_PRIORITY = "HIGH_PRIORITY_MAIL"

class EmailOutcome(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    