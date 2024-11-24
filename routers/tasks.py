from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Task, User
from auth import get_current_user
from constants.task_status import TaskStatus
from pydantic import BaseModel, validator

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"]
)

class TaskStatusUpdate(BaseModel):
    status: str

    @validator('status')
    def validate_status(cls, v):
        if not TaskStatus.has_value(v):
            valid_statuses = [status.value for status in TaskStatus]
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v

@router.patch("/{task_id}/status", response_model=dict)
def update_task_status(
    task_id: int,
    status_update: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the status of a task."""
    # Get the task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify the user owns the task
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Update the task status
    task.status = status_update.status
    db.commit()
    db.refresh(task)

    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "message": "Task status updated successfully"
    }
