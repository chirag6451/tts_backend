import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import SQLALCHEMY_DATABASE_URL
from models import Task
from constants.task_status import TaskStatus

def update_task_statuses():
    """Update existing task statuses to match the new enum values."""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get all tasks
        tasks = db.query(Task).all()
        
        # Update status for each task if needed
        for task in tasks:
            if task.status == "pending":
                task.status = TaskStatus.PENDING.value
            elif task.status == "in_progress":
                task.status = TaskStatus.IN_PROGRESS.value
            elif task.status == "cancelled":
                task.status = TaskStatus.CANCELLED.value
            elif task.status == "completed":
                task.status = TaskStatus.COMPLETED.value
        
        db.commit()
        print("Successfully updated task statuses")
        
    except Exception as e:
        print(f"Error updating task statuses: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_task_statuses()
