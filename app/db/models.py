# Copyright 2025 Vijil, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# The vijil trademark is owned by Vijil Inc.

"""
Database models for the GDC Submission application.
"""
from sqlalchemy import (
    Column, String, Text, DateTime, create_engine, ForeignKey, Integer
)
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json
import os
import uuid

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
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
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


class Session(Base):
    """
    SQLAlchemy model for storing virtual user testing session data.
    """
    __tablename__ = 'sessions'

    id = Column(
        String(255), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    persona_id = Column(String(255), ForeignKey('personas.id'), nullable=False)
    
    # Session parameters
    num_goals = Column(Integer, nullable=True)
    max_turns = Column(Integer, nullable=True)
    conversations_per_goal = Column(Integer, nullable=True)

    # Session results
    session_data = Column(Text, nullable=False)  # JSON of the full output

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to Persona
    persona = relationship("Persona")

    def to_dict(self):
        """
        Convert the database model to a dictionary.
        """
        return {
            'id': self.id,
            'persona_id': self.persona_id,
            'num_goals': self.num_goals,
            'max_turns': self.max_turns,
            'conversations_per_goal': self.conversations_per_goal,
            'session_data': json.loads(self.session_data),
            'created_at': self.created_at.isoformat()
        }


# Database setup
# Use an absolute path for the database file
db_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(db_dir, 'personas.db')
engine = create_engine(f'sqlite:///{db_path}')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(engine)


def drop_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(engine)
