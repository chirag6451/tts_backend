import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    try:
        # Load environment variables
        load_dotenv()
        
        # Get database URL from environment variable
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        logger.info("Connecting to database...")
        
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Drop all existing tables
        logger.info("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully!")
        
        # Create all tables fresh
        logger.info("Creating new tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully!")
        
        # Create session for verification
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Verify tables exist by running a simple query
        try:
            # Try to query each table
            tables = Base.metadata.tables.keys()
            for table in tables:
                result = db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                logger.info(f"Table '{table}' verified successfully!")
        except Exception as e:
            logger.error(f"Error verifying tables: {str(e)}")
            raise
        finally:
            db.close()
        
        logger.info("Database reset completed successfully!")
        
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting database reset process...")
    reset_database()
    logger.info("Database reset process completed!")
