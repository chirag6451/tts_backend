from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Dict
from database import get_db
from models import Task, User
from auth import get_current_user
from constants.task_status import TaskStatus
from dashboard_schemas import (
    DashboardStats, AssigneeInfo, UserActivityInfo,
    LongOpenTask, OverdueTask
)

router = APIRouter()

def calculate_days_difference(date: datetime) -> int:
    if not date:
        return 0
    current_time = datetime.now(timezone.utc)
    difference = current_time - date.replace(tzinfo=timezone.utc)
    return difference.days

def get_task_stats(db: Session) -> Dict:
    # Get counts for each status
    status_counts = dict(
        db.query(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )
    
    # Add overdue count
    overdue_count = db.query(func.count(Task.id)).filter(
        Task.due_date < datetime.now(timezone.utc),
        Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value])
    ).scalar()
    
    status_counts['overdue'] = overdue_count or 0
    
    # Calculate completion rates
    total_tasks = sum(count for status, count in status_counts.items() if status != 'overdue')
    if total_tasks > 0:
        completion_rate = {
            'completed': round((status_counts.get(TaskStatus.COMPLETED.value, 0) / total_tasks) * 100, 2),
            'in_progress': round((status_counts.get(TaskStatus.IN_PROGRESS.value, 0) / total_tasks) * 100, 2),
            'pending': round((status_counts.get(TaskStatus.PENDING.value, 0) / total_tasks) * 100, 2)
        }
    else:
        completion_rate = {'completed': 0, 'in_progress': 0, 'pending': 0}
    
    return {
        'status_counts': status_counts,
        'completion_rate': completion_rate
    }

def get_user_activity(db: Session) -> Dict[str, List[UserActivityInfo]]:
    user_stats = (
        db.query(
            User,
            func.count(Task.id).label('task_count'),
            func.max(Task.updated_at).label('last_active')
        )
        .outerjoin(Task)
        .group_by(User.id)
        .all()
    )
    
    # Sort users by task count
    user_stats.sort(key=lambda x: (x[1], x[2] or datetime.min), reverse=True)
    
    def create_user_activity(user_stat) -> UserActivityInfo:
        user, task_count, last_active = user_stat
        # Default to "User {id}" if both name and email are None
        display_name = user.name or user.email or f"User {user.id}"
        return UserActivityInfo(
            id=user.id,
            name=display_name,
            task_count=task_count,
            last_active=last_active or user.created_at
        )
    
    return {
        'most_active_users': [create_user_activity(stat) for stat in user_stats[:3]],
        'inactive_users': [create_user_activity(stat) for stat in user_stats[-3:]]
    }

def get_longest_open_tasks(db: Session) -> List[LongOpenTask]:
    tasks = (
        db.query(Task, User)
        .join(User)
        .filter(Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]))
        .order_by(Task.created_at.asc())
        .limit(5)
        .all()
    )
    
    return [
        LongOpenTask(
            id=task.id,
            title=task.title,
            assignee=AssigneeInfo(
                id=user.id,
                name=user.name or user.email or f"User {user.id}"
            ),
            created_at=task.created_at,
            days_open=calculate_days_difference(task.created_at),
            status=task.status
        ) for task, user in tasks
    ]

def get_overdue_tasks(db: Session) -> List[OverdueTask]:
    current_time = datetime.now(timezone.utc)
    tasks = (
        db.query(Task, User)
        .join(User)
        .filter(
            Task.due_date < current_time,
            Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value])
        )
        .order_by(Task.due_date.asc())
        .limit(10)
        .all()
    )
    
    return [
        OverdueTask(
            id=task.id,
            title=task.title,
            assignee=AssigneeInfo(
                id=user.id,
                name=user.name or user.email or f"User {user.id}"
            ),
            due_date=task.due_date,
            days_overdue=calculate_days_difference(task.due_date),
            priority="high" if calculate_days_difference(task.due_date) > 7 else "medium"
        ) for task, user in tasks if task.due_date
    ]

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard statistics including:
    - Task status counts and completion rates
    - User activity metrics
    - Longest open tasks
    - Overdue tasks
    """
    try:
        task_stats = get_task_stats(db)
        user_activity = get_user_activity(db)
        
        return DashboardStats(
            status_counts=task_stats['status_counts'],
            completion_rate=task_stats['completion_rate'],
            most_active_users=user_activity['most_active_users'],
            inactive_users=user_activity['inactive_users'],
            longest_open_tasks=get_longest_open_tasks(db),
            overdue_tasks=get_overdue_tasks(db)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving dashboard statistics: {str(e)}"
        )
