"""
Database operations for persona management.
"""
from typing import Optional, List
import os
import glob
from models import Persona as PersonaModel, get_session, create_tables


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
