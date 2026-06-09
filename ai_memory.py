"""
AI Memory models for PopoCorps conversation storage and learning
"""
from sqlalchemy import Column, Integer, BigInteger, Text, DateTime, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class ConversationMemory(Base):
    """Store all conversations with users"""
    __tablename__ = 'conversation_memory'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    message_content = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=True)
    message_type = Column(String(50), nullable=True)
    sentiment = Column(String(20), nullable=True)
    relationship_level = Column(String(50), nullable=True)
    conversation_stage = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ConversationMemory(guild={self.guild_id}, user={self.user_id}, content='{self.message_content[:50]}...')>"

class UserProfile(Base):
    """Store learned information about users"""
    __tablename__ = 'user_profiles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(100), nullable=True)
    total_messages = Column(Integer, default=0)
    preferred_language = Column(String(10), default='fr')
    communication_style = Column(String(50), nullable=True)  # formal, casual, vulgar
    common_topics = Column(Text, nullable=True)  # JSON list of topics
    personality_traits = Column(Text, nullable=True)  # JSON dict
    relationship_strength = Column(Float, default=0.0)  # 0-1 scale
    last_interaction = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserProfile(guild={self.guild_id}, user={self.user_id}, messages={self.total_messages})>"

class BotKnowledge(Base):
    """Store learned patterns and knowledge"""
    __tablename__ = 'bot_knowledge'
    
    id = Column(Integer, primary_key=True)
    knowledge_type = Column(String(50), nullable=False)  # pattern, response, fact, preference
    category = Column(String(100), nullable=True)
    key_phrase = Column(Text, nullable=False)
    learned_response = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.5)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    guild_specific = Column(Boolean, default=False)
    guild_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BotKnowledge(type={self.knowledge_type}, phrase='{self.key_phrase[:30]}...')>"

class ConversationStats(Base):
    """Store conversation statistics and metrics"""
    __tablename__ = 'conversation_stats'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    total_conversations = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    average_sentiment = Column(Float, default=0.0)
    most_common_topic = Column(String(100), nullable=True)
    response_satisfaction = Column(Float, default=0.0)
    
    def __repr__(self):
        return f"<ConversationStats(guild={self.guild_id}, date={self.date.date()})>"

# Database connection
def get_ai_memory_engine():
    """Get database engine for AI memory"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=300)

def get_ai_memory_session():
    """Get database session for AI memory"""
    engine = get_ai_memory_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def create_ai_memory_tables():
    """Create all AI memory tables"""
    engine = get_ai_memory_engine()
    Base.metadata.create_all(engine)

# Initialize tables on import
try:
    create_ai_memory_tables()
except Exception as e:
    print(f"Warning: Could not create AI memory tables: {e}")