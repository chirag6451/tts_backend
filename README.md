# Task Management API

A FastAPI-based backend for the Task Management Flutter application with voice recording support.

## Features

- User authentication with JWT tokens
- Task management (CRUD operations)
- Voice recording storage and retrieval
- SQLite database with SQLAlchemy ORM
- File upload handling for audio recordings

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

After starting the server, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication
- POST `/auth/register` - Register new user
- POST `/auth/login` - Login and get access token

### Tasks
- GET `/tasks` - List all tasks for current user
- GET `/tasks/{task_id}` - Get specific task
- POST `/tasks` - Create new task with optional audio recording
- PUT `/tasks/{task_id}` - Update existing task
- DELETE `/tasks/{task_id}` - Delete task

## Project Structure

- `main.py` - FastAPI application and route handlers
- `models.py` - SQLAlchemy database models
- `schemas.py` - Pydantic models for request/response validation
- `database.py` - Database configuration
- `auth.py` - Authentication utilities

## Security Notes

- Change the `SECRET_KEY` in `auth.py` before deploying to production
- Configure CORS settings in `main.py` for production
- Use environment variables for sensitive configuration
- Implement rate limiting for production use
