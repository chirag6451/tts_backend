import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Server Configuration
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
BASE_URL = os.getenv("BASE_URL", f"http://{SERVER_HOST}:{SERVER_PORT}")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "chirag")  # Make sure to change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
