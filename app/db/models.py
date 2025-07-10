"""
Database models for the GDC Submission application.
"""
from sqlalchemy import Column, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os

Base = declarative_base()

class Persona(Base):
    """
    SQLAlchemy model for storing persona data.
    """
    __tablename__ = 'personas'
    
    # Primary key: persona filename without .json extension
    id = Column(String(255), primary_key=True)
    
    # Core persona fields
    participant_id = Column(String(255), nullable=False)
    response_language = Column(String(50), nullable=False)
    high_level_AI_view = Column(Text, nullable=False)
    
    # JSON fields stored as text
    demographic_info = Column(Text, nullable=False)  # JSON string
    survey_responses = Column(Text, nullable=False)  # JSON string
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """
        Convert the database model to a dictionary matching the JSON structure
        """
        return {
            'participant_id': self.participant_id,
            'response_language': self.response_language,
            'high_level_AI_view': self.high_level_AI_view,
            'demographic_info': json.loads(self.demographic_info),
            'survey_responses': json.loads(self.survey_responses)
        }
    
    @classmethod
    def from_json_file(cls, json_path: str):
        """
        Create a Persona instance from a JSON file.
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract ID from filename (remove .json extension)
        filename = os.path.basename(json_path)
        persona_id = filename.replace('.json', '')
        
        return cls(
            id=persona_id,
            participant_id=data['participant_id'],
            response_language=data['response_language'],
            high_level_AI_view=data['high_level_AI_view'],
            demographic_info=json.dumps(data['demographic_info']),
            survey_responses=json.dumps(data['survey_responses'])
        )

# Database configuration
def get_db_path():
    """Get the absolute path for the database file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'personas.db')

DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{get_db_path()}')

def get_engine():
    """Create and return database engine"""
    return create_engine(DATABASE_URL, echo=False)

def get_session():
    """Create and return database session"""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def create_tables():
    """Create all database tables"""
    engine = get_engine()
    Base.metadata.create_all(engine)

def drop_tables():
    """Drop all database tables"""
    engine = get_engine()
    Base.metadata.drop_all(engine)
