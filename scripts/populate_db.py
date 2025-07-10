#!/usr/bin/env python3
"""
Script to populate the database with persona data from JSON files.
"""
import sys
import os

# Add the app/db directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app', 'db'))

from operations import persona_db

def main():
    """
    Main function to populate database with personas from JSON files.
    """
    # Path to the personas directory
    personas_dir = os.path.join(os.path.dirname(__file__), '..', 'personas')
    personas_dir = os.path.abspath(personas_dir)
    
    if not os.path.exists(personas_dir):
        print(f"Personas directory not found: {personas_dir}")
        return
    
    print(f"Loading personas from: {personas_dir}")
    
    try:
        count = persona_db.load_personas_from_json_files(personas_dir)
        print(f"Successfully loaded {count} personas into the database.")
        
        # Show summary
        all_personas = persona_db.get_all_personas()
        print(f"Total personas in database: {len(all_personas)}")
        
        print("\nPersonas in database:")
        for persona in all_personas[:10]:  # Show first 10
            print(f"  - {persona.id} ({persona.response_language})")
        
        if len(all_personas) > 10:
            print(f"  ... and {len(all_personas) - 10} more")
            
    except Exception as e:
        print(f"Error loading personas: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
