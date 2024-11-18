from datetime import datetime, timedelta
import os
import shutil
import time
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from models import Task, User, Base
from database import SessionLocal, engine, get_db, init_db
from schemas import TaskCreate, TaskResponse, UserCreate, UserResponse, Token, AudioUploadResponse
import pydantic
import uvicorn
from auth import (
    get_current_user,
    create_access_token,
    verify_password,
    get_password_hash,
)

app = FastAPI(title="Task Management API")

# Initialize database with new schema
init_db()

# Create a test user if none exists
def create_test_user():
    db = SessionLocal()
    try:
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            test_user = User(
                email="test@example.com",
                hashed_password=get_password_hash("password123")
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
    finally:
        db.close()

# Create test user
create_test_user()

# CORS middleware configuration
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8001",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the audio_files directory to serve static files
app.mount("/audio", StaticFiles(directory="audio_files"), name="audio")

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/login", response_model=Token)
async def login(credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id
    }

# Task endpoints
@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    title: str = Form(...),
    description: str = Form(...),
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Create audio directory if it doesn't exist
        audio_dir = "audio_files"
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generate unique filename with user ID for better organization
        timestamp = int(time.time())
        file_extension = os.path.splitext(audio_file.filename)[1] or '.m4a'
        filename = f"user_{current_user.id}_audio_{timestamp}{file_extension}"
        file_path = os.path.join(audio_dir, filename)
        
        # Save the file
        contents = await audio_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Create task with the audio file and user ID
        task_db = Task(
            title=title,
            description=description,
            audio_path=file_path,
            user_id=current_user.id,  # Explicitly set the user ID
            status="pending"  # Set default status
        )
        
        db.add(task_db)
        db.commit()
        db.refresh(task_db)
        
        # Add audio URL to response
        base_url = "http://localhost:8000"
        if task_db.audio_path:
            filename = os.path.basename(task_db.audio_path)
            task_db.audio_url = f"{base_url}/tasks/audio/{filename}"
        
        return task_db
        
    except Exception as e:
        # Clean up the file if task creation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating task: {str(e)}"
        )

@app.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Query tasks specifically for the current user
        tasks = (
            db.query(Task)
            .filter(Task.user_id == current_user.id)  # Filter by current user's ID
            .order_by(Task.created_at.desc())  # Most recent first
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Add audio URLs to tasks that have audio files
        base_url = "http://localhost:8000"
        for task in tasks:
            if task.audio_path:
                filename = os.path.basename(task.audio_path)
                task.audio_url = f"{base_url}/tasks/audio/{filename}"
            
            # Ensure task belongs to current user
            if task.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: Task belongs to another user"
                )
        
        return tasks
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tasks: {str(e)}"
        )

@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify task belongs to current user
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied: Task belongs to another user"
        )
    
    # Add audio URL if task has audio file
    if task.audio_path:
        base_url = "http://localhost:8000"
        filename = os.path.basename(task.audio_path)
        task.audio_url = f"{base_url}/tasks/audio/{filename}"
    
    return task

@app.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    title: str = None,
    description: str = None,
    audio_file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if title:
        task.title = title
    if description:
        task.description = description
    
    if audio_file:
        # Delete old audio file if exists
        if task.audio_path and os.path.exists(task.audio_path):
            os.remove(task.audio_path)
        
        # Save new audio file
        file_path = f"uploads/{datetime.now().timestamp()}_{audio_file.filename}"
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await audio_file.read()
            await out_file.write(content)
        
        task.audio_path = file_path
    
    db.commit()
    db.refresh(task)
    return task

@app.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get the task
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate status
    status = status.lower()
    if status not in ["pending", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be 'pending' or 'completed'")
    
    # Update the task status
    task.status = status
    task.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Task status updated successfully", "status": status}

@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Delete audio file if exists
    if task.audio_path and os.path.exists(task.audio_path):
        os.remove(task.audio_path)
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}

@app.post("/tasks/audio/upload", response_model=AudioUploadResponse)
async def upload_audio(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Generate a unique filename
        timestamp = int(time.time() * 1000)
        filename = f"audio_{timestamp}.m4a"
        file_path = os.path.join("audio_files", filename)

        # Ensure the audio_files directory exists
        os.makedirs("audio_files", exist_ok=True)

        # Save the file
        with open(file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)

        # Create a new task with the audio file
        new_task = Task(
            title="Voice Note Task",
            description="Task created from voice note",
            status="pending",
            audio_path=file_path,
            user_id=current_user.id
        )
        db.add(new_task)
        db.commit()
        db.refresh(new_task)

        # Create the response
        base_url = "http://localhost:8000"
        filename = os.path.basename(file_path)
        audio_url = f"{base_url}/tasks/audio/{filename}"

        # Return the response with task details
        return AudioUploadResponse(
            success=True,
            message="Audio uploaded successfully",
            task={
                "id": new_task.id,
                "title": new_task.title,
                "description": new_task.description,
                "status": new_task.status,
                "audio_path": new_task.audio_path,
                "audio_url": audio_url,
                "created_at": new_task.created_at,
                "updated_at": new_task.updated_at,
                "user_id": new_task.user_id
            }
        )

    except Exception as e:
        # If there's an error, try to delete the file if it was created
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio: {str(e)}"
        )
    finally:
        await audio_file.close()

@app.get("/tasks/audio/{filename}")
async def get_audio_file(filename: str):
    audio_path = f"audio_files/{filename}"
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/mpeg")

# Create database tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8011, reload=True)

