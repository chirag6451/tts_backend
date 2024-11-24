from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict

class AssigneeInfo(BaseModel):
    id: int
    name: str

class UserActivityInfo(BaseModel):
    id: int
    name: str
    task_count: int
    last_active: datetime

class LongOpenTask(BaseModel):
    id: int
    title: str
    assignee: AssigneeInfo
    created_at: datetime
    days_open: int
    status: str

class OverdueTask(BaseModel):
    id: int
    title: str
    assignee: AssigneeInfo
    due_date: datetime
    days_overdue: int
    priority: str

class DashboardStats(BaseModel):
    status_counts: Dict[str, int]
    completion_rate: Dict[str, float]
    most_active_users: List[UserActivityInfo]
    inactive_users: List[UserActivityInfo]
    longest_open_tasks: List[LongOpenTask]
    overdue_tasks: List[OverdueTask]
