from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'db'))

from agents.run_session import run_session_from_config

app = FastAPI(title="Persona Red Teaming API", version="1.0.0")

# Database imports
try:
    from operations import persona_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    persona_db = None


class RedTeamingRequest(BaseModel):
    persona_fname: str  # Can be file path or persona ID
    target_agent_config: Optional[str] = None
    num_goals: Optional[int] = None
    max_turns: Optional[int] = None
    verbose: Optional[bool] = True
    use_db: Optional[bool] = True  # Whether to use database lookup

class RedTeamingResponse(BaseModel):
    success: bool
    good_faith: Optional[Any] = None
    error: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None

class PersonaResponse(BaseModel):
    id: str
    participant_id: str
    response_language: str
    high_level_AI_view: str
    demographic_info: Dict[str, Any]
    survey_responses: Dict[str, str]


@app.post("/run-red-teaming-session", response_model=RedTeamingResponse)
async def run_red_teaming_session(request: RedTeamingRequest):
    """
    Run a red teaming session with the specified persona against a target agent.
    """
    try:
        # Get absolute paths relative to the API directory
        api_dir = os.path.dirname(__file__)
        repo_root = os.path.abspath(os.path.join(api_dir, '..', '..'))
        src_dir = os.path.join(repo_root, 'src')
        
        # Set default target agent config if not provided
        if request.target_agent_config is None:
            request.target_agent_config = os.path.join(
                src_dir, 'configs', 'nora.yaml'
            )
        else:
            # Convert relative paths to absolute paths
            if not os.path.isabs(request.target_agent_config):
                # Try relative to src first, then relative to repo root
                src_relative_path = os.path.join(
                    src_dir, request.target_agent_config
                )
                repo_relative_path = os.path.join(
                    repo_root, request.target_agent_config
                )
                if os.path.exists(src_relative_path):
                    request.target_agent_config = src_relative_path
                elif os.path.exists(repo_relative_path):
                    request.target_agent_config = repo_relative_path
                else:
                    # Default to src relative
                    request.target_agent_config = src_relative_path
        
        # Handle persona path
        if not os.path.isabs(request.persona_fname):
            persona_path = os.path.join(repo_root, request.persona_fname)
        else:
            persona_path = request.persona_fname
        
        config_path = request.target_agent_config
        
        # Validate persona file exists or fetch from DB
        persona = None
        if os.path.exists(persona_path):
            persona = persona_path
        elif request.use_db and DB_AVAILABLE:
            persona = persona_db.get_persona_by_id(request.persona_fname)
            if persona:
                persona = persona.to_dict()
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Persona {request.persona_fname} not found"
                )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Persona file not found: {request.persona_fname}"
            )
        
        # Validate target agent config exists
        if not os.path.exists(config_path):
            raise HTTPException(
                status_code=404,
                detail=f"Target agent config not found: {config_path}"
            )
        
        # Prepare kwargs for run_session_from_config
        session_kwargs = {
            'persona_config': persona,
            'target_agent_config': config_path,
            'verbose': request.verbose,
        }
        
        if request.num_goals is not None:
            session_kwargs['num_goals'] = request.num_goals
        
        if request.max_turns is not None:
            session_kwargs['max_turns'] = request.max_turns
        
        # Run the session
        output = await run_session_from_config(**session_kwargs)
        
        return RedTeamingResponse(
            success=True,
            good_faith=output.get('good_faith'),
            session_data=output
        )
        
    except Exception as e:
        return RedTeamingResponse(
            success=False,
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Persona Red Teaming API",
        "version": "1.0.0",
        "endpoints": {
            "POST /run-red-teaming-session": "Run a red teaming session with a persona",
            "GET /health": "Health check",
            "GET /": "This endpoint"
        }
    }

@app.get("/personas", response_model=List[Dict[str, str]])
async def list_personas():
    """Get a list of all personas in the database"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        personas = persona_db.get_all_personas()
        return [
            {
                "id": p.id,
                "participant_id": p.participant_id,
                "response_language": p.response_language
            }
            for p in personas
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str):
    """Get a specific persona by ID"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        persona = persona_db.get_persona_by_id(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
        
        return PersonaResponse(**persona.to_dict(), id=persona.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/load-personas")
async def load_personas_from_files():
    """Load personas from JSON files into the database"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        personas_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'personas')
        personas_dir = os.path.abspath(personas_dir)
        
        if not os.path.exists(personas_dir):
            raise HTTPException(status_code=404, detail="Personas directory not found")
        
        count = persona_db.load_personas_from_json_files(personas_dir)
        return {"message": f"Successfully loaded {count} personas", "count": count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading personas: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
