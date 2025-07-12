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
Database operations for persona management.
"""
from typing import Optional, List
import os
import glob
from .models import (
    Persona as PersonaModel,
    Session as SessionModel,
    get_session,
    create_tables
)


class PersonaDB:
    """
    Database operations for personas.
    """
    
    def __init__(self):
        """Initialize database connection and create tables if needed."""
        create_tables()
    
    def create_persona(self, persona: PersonaModel) -> PersonaModel:
        """
        Create a new persona in the database.
        """
        session = get_session()
        try:
            session.add(persona)
            session.commit()
            session.refresh(persona)
            return persona
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_persona_by_id(self, persona_id: str) -> Optional[PersonaModel]:
        """
        Get a persona by ID.
        """
        session = get_session()
        try:
            return session.query(PersonaModel).filter(
                PersonaModel.id == persona_id
            ).first()
        finally:
            session.close()
    
    def get_all_personas(self) -> List[PersonaModel]:
        """
        Get all personas from the database.
        """
        session = get_session()
        try:
            return session.query(PersonaModel).all()
        finally:
            session.close()
    
    def update_persona(self, persona_id: str, **kwargs) -> Optional[PersonaModel]:
        """
        Update a persona by ID.
        """
        session = get_session()
        try:
            persona = session.query(PersonaModel).filter(
                PersonaModel.id == persona_id
            ).first()
            if persona:
                for key, value in kwargs.items():
                    setattr(persona, key, value)
                session.commit()
                session.refresh(persona)
            return persona
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_persona(self, persona_id: str) -> bool:
        """
        Delete a persona by ID.
        """
        session = get_session()
        try:
            persona = session.query(PersonaModel).filter(
                PersonaModel.id == persona_id
            ).first()
            if persona:
                session.delete(persona)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def load_personas_from_json_files(self, json_directory: str) -> int:
        """
        Load all persona JSON files from a directory into the database.
        Returns the number of personas loaded.
        """
        if not os.path.exists(json_directory):
            raise FileNotFoundError(f"Directory not found: {json_directory}")
        
        json_files = glob.glob(os.path.join(json_directory, "*.json"))
        loaded_count = 0
        
        session = get_session()
        try:
            for json_file in json_files:
                try:
                    # Create persona from JSON file
                    persona = PersonaModel.from_json_file(json_file)
                    
                    # Check if persona already exists
                    existing = session.query(PersonaModel).filter(
                        PersonaModel.id == persona.id
                    ).first()
                    
                    if existing:
                        print(f"Persona {persona.id} already exists, skipping...")
                        continue
                    
                    # Add new persona
                    session.add(persona)
                    loaded_count += 1
                    print(f"Loaded persona: {persona.id}")
                    
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")
                    continue
            
            session.commit()
            return loaded_count
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Global instance
persona_db = PersonaDB()


class SessionDB:
    """
    Database operations for sessions.
    """

    def __init__(self):
        """Initialize database connection and create tables if needed."""
        create_tables()

    def create_session(self, session: SessionModel) -> SessionModel:
        """
        Create a new session in the database.
        """
        session_db_conn = get_session()
        try:
            session_db_conn.add(session)
            session_db_conn.commit()
            session_db_conn.refresh(session)
            return session
        except Exception as e:
            session_db_conn.rollback()
            raise e
        finally:
            session_db_conn.close()

    def create_sessions_batch(
        self, sessions: List[SessionModel]
    ) -> List[SessionModel]:
        """
        Create multiple sessions in the database as a batch operation.
        Returns the list of sessions with their assigned IDs.
        """
        if not sessions:
            return []
            
        session_db_conn = get_session()
        try:
            session_db_conn.add_all(sessions)
            session_db_conn.commit()
            # Refresh all sessions to get their IDs
            for session in sessions:
                session_db_conn.refresh(session)
            return sessions
        except Exception as e:
            session_db_conn.rollback()
            raise e
        finally:
            session_db_conn.close()

    def get_session_by_id(self, session_id: str) -> Optional[SessionModel]:
        """
        Get a session by ID.
        """
        session = get_session()
        try:
            return session.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()
        finally:
            session.close()

    def get_all_sessions(self) -> List[SessionModel]:
        """
        Get all sessions from the database.
        """
        session = get_session()
        try:
            return session.query(SessionModel).order_by(
                SessionModel.created_at.desc()
            ).all()
        finally:
            session.close()

    def get_sessions_by_persona_id(
        self, persona_id: str
    ) -> List[SessionModel]:
        """
        Get all sessions for a given persona ID.
        """
        session = get_session()
        try:
            return session.query(SessionModel).filter(
                SessionModel.persona_id == persona_id
            ).order_by(SessionModel.created_at.desc()).all()
        finally:
            session.close()


# Global instance
session_db = SessionDB()
