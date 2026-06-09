import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Warning(Base):
    __tablename__ = 'warnings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)  # Discord guild ID
    user_id = Column(BigInteger, nullable=False)   # Warned user ID
    moderator_id = Column(BigInteger, nullable=True)  # Who issued the warning
    reason = Column(Text, nullable=True)           # Warning reason
    bot_source = Column(String(100), nullable=True)  # Which bot issued the warning
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_id = Column(BigInteger, nullable=True)  # Original warning message ID
    channel_id = Column(BigInteger, nullable=True)  # Channel where warning was issued

    def __repr__(self):
        return f"<Warning(user_id={self.user_id}, reason='{self.reason}', bot_source='{self.bot_source}')>"

# Database setup
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine with connection pooling and retry settings
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_timeout=20,     # Timeout for getting connection from pool
    max_overflow=10,     # Allow up to 10 additional connections
    echo=False           # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Get a database session with proper error handling"""
    return SessionLocal()

def safe_db_operation(func):
    """Decorator for safe database operations with automatic retry"""
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            db = None
            try:
                db = get_db_session()
                result = func(db, *args, **kwargs)
                db.commit()
                return result
            except Exception as e:
                if db:
                    db.rollback()
                if attempt == max_retries - 1:
                    raise e
                # Wait before retry
                import time
                time.sleep(0.5)
            finally:
                if db:
                    db.close()
    return wrapper