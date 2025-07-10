import json
import os
import sys
from functools import singledispatch
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add parent and src directories to path for local module resolution
app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'src')
)
sys.path.insert(0, app_dir)
sys.path.insert(0, src_dir)
from db.models import Session as SessionModel  # noqa: E402
from db.operations import persona_db, session_db  # noqa: E402

print(sys.path)
# Local application imports
from agents.run_session import run_session_from_config  # noqa: E402

# Database imports
try:
    from db.models import Session as SessionModel  # noqa: E402
    from db.operations import persona_db, session_db  # noqa: E402
    DB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Database modules not found: {e}")
    DB_AVAILABLE = False
    persona_db = None
    session_db = None
    SessionModel = None


# Add a JSON serializer for Pydantic models and other types
@singledispatch
def to_serializable(val):
    """Used by default - convert objects to dictionaries if possible."""
    # Check if object has a to_dict method
    if hasattr(val, 'to_dict') and callable(getattr(val, 'to_dict')):
        return to_serializable(val.to_dict())
    elif hasattr(val, '__dict__'):
        # For custom objects, convert their __dict__ recursively
        return to_serializable(val.__dict__)
    elif hasattr(val, '_asdict'):
        # For namedtuples
        return to_serializable(val._asdict())
    else:
        # Last resort: convert to string
        return str(val)


@to_serializable.register(BaseModel)
def ts_model(val: BaseModel):
    """Used for Pydantic models."""
    return val.dict()


@to_serializable.register(list)
def ts_list(val: list):
    """Used for lists."""
    return [to_serializable(v) for v in val]


@to_serializable.register(dict)
def ts_dict(val: dict):
    """Used for dicts."""
    return {k: to_serializable(v) for k, v in val.items()}


app = FastAPI(title="Persona Red Teaming API", version="1.0.0")


# Initialize database and load personas on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and load personas on application startup"""
    if DB_AVAILABLE:
        try:
            # Create database tables if they don't exist
            from db.models import create_tables
            create_tables()
            print("✅ Database tables created/verified")
            
            # Check if personas are already loaded
            existing_personas = persona_db.get_all_personas()
            if existing_personas:
                count = len(existing_personas)
                print(f"✅ Database already contains {count} personas")
                return
            
            # Load personas from JSON files
            personas_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'personas')
            )
            
            if os.path.exists(personas_dir):
                count = persona_db.load_personas_from_json_files(personas_dir)
                print(f"✅ Loaded {count} personas from JSON files")
            else:
                print("⚠️  Personas directory not found, skipping loading")
                
        except Exception as e:
            print(f"❌ Error during startup: {e}")
    else:
        print("⚠️  Database not available")


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
    session_id: Optional[str] = None


class PersonaResponse(BaseModel):
    id: str
    participant_id: str
    response_language: str
    high_level_AI_view: str
    demographic_info: Dict[str, Any]
    survey_responses: Dict[str, str]


class SessionResponse(BaseModel):
    id: str
    persona_id: str
    num_goals: Optional[int] = None
    max_turns: Optional[int] = None
    session_data: Dict[str, Any]
    good_faith: Optional[Any] = None


@app.post("/run-red-teaming-session", response_model=RedTeamingResponse)
async def run_red_teaming_session(request: RedTeamingRequest):
    """
    Run a red teaming session with a specified persona.
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
        
        # Handle persona path
        persona_id_or_fname = request.persona_fname
        persona_config = None

        if DB_AVAILABLE and request.use_db:
            persona_obj = persona_db.get_persona_by_id(persona_id_or_fname)
            if persona_obj:
                persona_config = persona_obj.to_dict()
            else:
                # Fallback to checking filesystem if not in DB
                persona_fpath = os.path.join(repo_root, persona_id_or_fname)
                if os.path.exists(persona_fpath):
                    persona_config = persona_fpath
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            f"Persona '{persona_id_or_fname}' not found "
                            "in DB or filesystem."
                        )
                    )
        else:
            # Fallback to checking filesystem if not using DB
            persona_fpath = os.path.join(repo_root, persona_id_or_fname)
            if os.path.exists(persona_fpath):
                persona_config = persona_fpath
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Persona file '{persona_id_or_fname}' not found."
                )

        # Validate target agent config exists
        if not os.path.exists(request.target_agent_config):
            raise HTTPException(
                status_code=404,
                detail="Target agent config not found: "
                       f"{request.target_agent_config}"
            )
        
        # Prepare kwargs for run_session_from_config
        session_kwargs = {
            'persona_config': persona_config,
            'target_agent_config': request.target_agent_config,
            'verbose': request.verbose,
        }
        
        if request.num_goals is not None:
            session_kwargs['num_goals'] = request.num_goals
        
        if request.max_turns is not None:
            session_kwargs['max_turns'] = request.max_turns
        
        # Run the session
        output = await run_session_from_config(**session_kwargs)
        
        # Convert output to be JSON serializable
        serializable_output = to_serializable(output)
        
        # Save session to database if enabled
        session_id = None
        if request.use_db and DB_AVAILABLE:
            new_session = SessionModel(
                persona_id=persona_id_or_fname,
                num_goals=request.num_goals,
                max_turns=request.max_turns,
                session_data=json.dumps(serializable_output),
                good_faith=json.dumps(
                    serializable_output.get('good_faith')
                )
            )
            created_session = session_db.create_session(new_session)
            session_id = created_session.id

        return RedTeamingResponse(
            success=True,
            good_faith=serializable_output.get('good_faith'),
            session_data=serializable_output,
            session_id=session_id
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
            "POST /run-red-teaming-session":
                "Run a red teaming session with a persona",
            "GET /health": "Health check",
            "GET /": "This endpoint",
            "GET /personas": "List all personas",
            "GET /personas/{persona_id}": "Get a specific persona",
            "GET /sessions": "List all completed sessions",
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
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )


@app.get("/sessions")
async def list_sessions():
    """Get a list of all completed sessions"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        sessions = session_db.get_all_sessions()
        return [s.to_dict() for s in sessions]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )


@app.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(persona_id: str):
    """Get a specific persona by ID"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        persona = persona_db.get_persona_by_id(persona_id)
        if not persona:
            raise HTTPException(
                status_code=404, detail=f"Persona {persona_id} not found"
            )
        
        return PersonaResponse(**persona.to_dict(), id=persona.id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )

@app.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a specific session by ID"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        session = session_db.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Persona {session_id} not found"
            )
        
        return SessionResponse(**session.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )


@app.post("/load-personas")
async def load_personas_from_files():
    """Load personas from JSON files into the database"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        personas_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'personas')
        )
        
        if not os.path.exists(personas_dir):
            raise HTTPException(
                status_code=404, detail="Personas directory not found"
            )
        
        count = persona_db.load_personas_from_json_files(personas_dir)
        return {
            "message": f"Successfully loaded {count} personas",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading personas: {e}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
