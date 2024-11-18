from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import os
import time
from database import get_db
from models import Task, User
from auth import get_current_user
from datetime import datetime
from schemas import AudioUploadResponse

router = APIRouter()

@router.post("/upload", response_model=AudioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload audio file and create a new task
    """
    try:
        # Create audio directory if it doesn't exist
        audio_dir = "audio_files"
        os.makedirs(audio_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(time.time())
        file_extension = os.path.splitext(audio_file.filename)[1] or '.m4a'
        filename = f"audio_{timestamp}{file_extension}"
        file_path = os.path.join(audio_dir, filename)
        
        # Save the file
        contents = await audio_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Create a new task with default values
        task = Task(
            title=f"Voice Note {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description="Voice recording",
            audio_path=file_path,
            user_id=current_user.id
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return AudioUploadResponse(
            message="Audio uploaded successfully",
            task=task
        )
    except Exception as e:
        # Clean up the file if task creation fails
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio: {str(e)}"
        )
    finally:
        await audio_file.close()
