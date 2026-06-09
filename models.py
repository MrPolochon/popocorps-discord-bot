import os
import logging
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

class Directive(Base):
    """Admin-defined rule: an authorized user/role can make the bot run an action
    (give/remove a role on a mentioned member) by using a trigger keyword."""
    __tablename__ = 'directives'

    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)      # Discord guild ID
    trigger = Column(String(200), nullable=False)      # Keyword that triggers the action (e.g. "whitelist")
    action = Column(String(20), nullable=False)        # 'give_role' or 'remove_role'
    role_id = Column(BigInteger, nullable=False)       # Role to give/remove
    authorized_type = Column(String(10), nullable=False)  # 'user' or 'role'
    authorized_id = Column(BigInteger, nullable=False)    # User ID or Role ID allowed to trigger
    created_by = Column(BigInteger, nullable=True)     # Admin who created the directive
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Directive(guild_id={self.guild_id}, trigger='{self.trigger}', action='{self.action}', role_id={self.role_id})>"


class GuildConfig(Base):
    """Configuration par serveur Discord (setup, bienvenue, etc.)."""
    __tablename__ = 'guild_configs'

    guild_id = Column(BigInteger, primary_key=True)
    settings = Column(Text, nullable=False, default='{}')  # JSON
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<GuildConfig(guild_id={self.guild_id})>"

# Database setup
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logging.warning(
        "DATABASE_URL non defini - repli sur une base SQLite locale "
        "(les donnees ne seront pas persistantes sur un hebergeur ephemere comme Railway). "
        "Ajoutez une base PostgreSQL et la variable DATABASE_URL pour une persistance complete."
    )
    DATABASE_URL = "sqlite:///popocorps.db"

# Some providers expose 'postgres://' which SQLAlchemy 2.x no longer accepts
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine (pooling options only apply to real network databases like PostgreSQL)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
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