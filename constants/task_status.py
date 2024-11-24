from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    @classmethod
    def has_value(cls, value):
        return value in [item.value for item in cls]
