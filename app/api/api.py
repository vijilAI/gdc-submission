import json
import math
import os
import sys
import asyncio
import uuid
from datetime import datetime
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

print(sys.path)

# Global state for tracking multi-persona sessions
multi_session_status = {}

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


app = FastAPI(title="Virtual User Conversation Testing API", version="1.0.0")


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


class VirtualUserTestingRequest(BaseModel):
    persona_fname: str  # Can be file path or persona ID
    target_agent_config: Optional[str] = None
    num_goals: Optional[int] = None
    max_turns: Optional[int] = None
    conversations_per_goal: Optional[int] = 1  # Conversations per goal
    verbose: Optional[bool] = True
    use_db: Optional[bool] = True  # Whether to use database lookup


class MultiPersonaTestingRequest(BaseModel):
    persona_ids: List[str]  # List of persona IDs
    target_agent_config: Optional[str] = None
    num_goals: Optional[int] = None
    max_turns: Optional[int] = None
    conversations_per_goal: Optional[int] = 1
    verbose: Optional[bool] = True
    use_db: Optional[bool] = True


class PersonaSessionStatus(BaseModel):
    persona_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int  # 0-100
    message: str
    session_id: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class MultiPersonaTestingResponse(BaseModel):
    success: bool
    batch_id: str
    message: str
    total_personas: int
    error: Optional[str] = None


class BatchStatusResponse(BaseModel):
    batch_id: str
    total_personas: int
    completed: int
    failed: int
    running: int
    pending: int
    overall_status: str  # "pending", "running", "completed", "failed"
    persona_statuses: List[PersonaSessionStatus]


class VirtualUserTestingResponse(BaseModel):
    success: bool
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
    conversations_per_goal: Optional[int] = None
    session_data: Dict[str, Any]


@app.post(
    "/run-virtual-user-testing",
    response_model=VirtualUserTestingResponse
)
async def run_virtual_user_testing(request: VirtualUserTestingRequest):
    """
    Run a virtual user testing session with a specified persona.
    """
    try:
        # Get absolute paths relative to the API directory
        api_dir = os.path.dirname(__file__)
        repo_root = os.path.abspath(os.path.join(api_dir, '..', '..'))
        src_dir = os.path.join(repo_root, 'src')
        
        # Set default target agent config if not provided
        if request.target_agent_config is None:
            request.target_agent_config = os.path.join(
                src_dir, 'configs', 'alex.yaml'
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
                            f"Virtual user '{persona_id_or_fname}' not found "
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
                    detail=(
                        f"Virtual user file '{persona_id_or_fname}' not found."
                    )
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
            
        if request.conversations_per_goal is not None:
            session_kwargs['conversations_per_goal'] = (
                request.conversations_per_goal
            )
        
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
                conversations_per_goal=request.conversations_per_goal,
                session_data=json.dumps(serializable_output)
            )
            created_session = session_db.create_session(new_session)
            session_id = created_session.id

        return VirtualUserTestingResponse(
            success=True,
            session_data=serializable_output,
            session_id=session_id
        )
        
    except Exception as e:
        return VirtualUserTestingResponse(
            success=False,
            error=str(e)
        )


async def run_single_persona_session(
    batch_id: str, persona_id: str, session_kwargs: dict
):
    """Legacy function - replaced by run_single_persona_session_async"""
    # This function is no longer used but kept for backwards compatibility
    pass


async def run_multi_persona_sessions_background(
    batch_id: str, request: MultiPersonaTestingRequest
):
    """Run sessions for multiple personas in background with concurrency control"""
    try:
        # Get absolute paths relative to the API directory
        api_dir = os.path.dirname(__file__)
        repo_root = os.path.abspath(os.path.join(api_dir, '..', '..'))
        src_dir = os.path.join(repo_root, 'src')
        
        # Set default target agent config if not provided
        target_agent_config = request.target_agent_config
        if target_agent_config is None:
            target_agent_config = os.path.join(src_dir, 'configs', 'alex.yaml')
        
        # Validate target agent config exists
        if not os.path.exists(target_agent_config):
            raise Exception(f"Target agent config not found: {target_agent_config}")
        
        # Prepare kwargs for run_session_from_config (without persona_config)
        session_kwargs = {
            'target_agent_config': target_agent_config,
            'verbose': request.verbose,
            'use_db': request.use_db,
        }
        
        if request.num_goals is not None:
            session_kwargs['num_goals'] = request.num_goals
        
        if request.max_turns is not None:
            session_kwargs['max_turns'] = request.max_turns
            
        if request.conversations_per_goal is not None:
            session_kwargs['conversations_per_goal'] = request.conversations_per_goal
        
        # Concurrency control: limit to 3 concurrent persona sessions
        # This prevents overwhelming the system and API rate limits
        MAX_CONCURRENT_PERSONAS = 3
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PERSONAS)
        
        # Storage for completed session data (for batch database writes)
        completed_sessions = []
        session_lock = asyncio.Lock()
        
        async def run_persona_with_concurrency_control(persona_id: str):
            """Run a single persona session with concurrency control"""
            async with semaphore:  # Limit concurrent executions
                session_data = await run_single_persona_session_async(
                    batch_id, persona_id, session_kwargs.copy(),
                    completed_sessions, session_lock
                )
                return session_data
        
        # Create tasks for all personas
        tasks = [
            run_persona_with_concurrency_control(persona_id)
            for persona_id in request.persona_ids
        ]
        
        # Wait for all sessions to complete with exception handling
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Batch database write for all completed sessions
        await batch_write_sessions_to_db(completed_sessions)
        
        # Update overall batch status
        persona_statuses = multi_session_status[batch_id]["persona_statuses"]
        completed_count = sum(1 for status in persona_statuses.values() if status["status"] == "completed")
        failed_count = sum(1 for status in persona_statuses.values() if status["status"] == "failed")
        
        if failed_count == 0:
            overall_status = "completed"
        elif completed_count == 0:
            overall_status = "failed"
        else:
            overall_status = "partially_completed"
        
        multi_session_status[batch_id]["overall_status"] = overall_status
        multi_session_status[batch_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        multi_session_status[batch_id]["overall_status"] = "failed"
        multi_session_status[batch_id]["error"] = str(e)
        multi_session_status[batch_id]["completed_at"] = datetime.now().isoformat()


async def run_single_persona_session_async(
    batch_id: str, persona_id: str, session_kwargs: dict, 
    completed_sessions: list, session_lock: asyncio.Lock
):
    """Run a session for a single persona and update status (async version)"""
    try:
        # Update status to running
        multi_session_status[batch_id]["persona_statuses"][persona_id].update({
            "status": "running",
            "progress": 10,
            "message": "Starting session...",
            "started_at": datetime.now().isoformat()
        })
        
        # Prepare persona config
        if DB_AVAILABLE and session_kwargs.get('use_db', True):
            persona_obj = persona_db.get_persona_by_id(persona_id)
            if persona_obj:
                persona_config = persona_obj.to_dict()
            else:
                raise Exception(f"Persona {persona_id} not found in database")
        else:
            raise Exception("Database not available for persona lookup")
        
        session_kwargs['persona_config'] = persona_config
        
        # Update progress
        multi_session_status[batch_id]["persona_statuses"][persona_id].update({
            "progress": 30,
            "message": "Generating goals..."
        })
        
        # Create a callback function to update progress during session execution
        def progress_callback(stage: str, progress: int):
            multi_session_status[batch_id]["persona_statuses"][persona_id].update({
                "progress": min(progress, 90),  # Cap at 90% until completion
                "message": stage
            })
        
        # Add progress callback to session kwargs
        session_kwargs['progress_callback'] = progress_callback
        
        # Run the session (this is now fully async including conversations)
        output = await run_session_from_config(**session_kwargs)
        
        # Update progress
        multi_session_status[batch_id]["persona_statuses"][persona_id].update({
            "progress": 95,
            "message": "Processing session data..."
        })
        
        # Convert output to be JSON serializable
        serializable_output = to_serializable(output)
        
        # Prepare session data for batch database write
        session_data = {
            'persona_id': persona_id,
            'num_goals': session_kwargs.get('num_goals'),
            'max_turns': session_kwargs.get('max_turns'),
            'conversations_per_goal': session_kwargs.get('conversations_per_goal'),
            'session_data': json.dumps(serializable_output)
        }
        
        # Thread-safe addition to completed sessions list
        async with session_lock:
            completed_sessions.append(session_data)
        
        # Update status to completed (session_id will be set after batch write)
        multi_session_status[batch_id]["persona_statuses"][persona_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Session completed successfully",
            "completed_at": datetime.now().isoformat()
        })
        
        return serializable_output
        
    except Exception as e:
        # Update status to failed
        multi_session_status[batch_id]["persona_statuses"][persona_id].update({
            "status": "failed",
            "progress": 0,
            "message": f"Session failed: {str(e)}",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })
        return None


async def batch_write_sessions_to_db(completed_sessions: list):
    """Batch write all completed sessions to database"""
    if not completed_sessions or not DB_AVAILABLE:
        return
    
    try:
        # Create all session models
        session_models = []
        for session_data in completed_sessions:
            session_model = SessionModel(**session_data)
            session_models.append(session_model)
        
        # Batch create sessions in database
        created_sessions = session_db.create_sessions_batch(session_models)
        
        # Update session IDs in status tracking
        for i, created_session in enumerate(created_sessions):
            persona_id = completed_sessions[i]['persona_id']
            # Find the batch that contains this persona
            for batch_id, batch_data in multi_session_status.items():
                if persona_id in batch_data.get("persona_statuses", {}):
                    multi_session_status[batch_id]["persona_statuses"][persona_id]["session_id"] = created_session.id
                    break
        
        print(f"✅ Batch created {len(created_sessions)} sessions in database")
        
    except Exception as e:
        print(f"❌ Error in batch database write: {e}")
        # Don't fail the entire batch for database write issues


@app.post("/run-multi-persona-testing", response_model=MultiPersonaTestingResponse)
async def run_multi_persona_testing(request: MultiPersonaTestingRequest):
    """
    Run virtual user testing sessions for multiple personas concurrently.
    """
    try:
        if not request.persona_ids:
            raise HTTPException(status_code=400, detail="No persona IDs provided")
        
        # Generate unique batch ID
        batch_id = str(uuid.uuid4())
        
        # Initialize status tracking
        multi_session_status[batch_id] = {
            "batch_id": batch_id,
            "total_personas": len(request.persona_ids),
            "overall_status": "pending",
            "created_at": datetime.now().isoformat(),
            "persona_statuses": {}
        }
        
        # Initialize status for each persona
        for persona_id in request.persona_ids:
            multi_session_status[batch_id]["persona_statuses"][persona_id] = {
                "persona_id": persona_id,
                "status": "pending",
                "progress": 0,
                "message": "Waiting to start...",
                "session_id": None,
                "error": None,
                "started_at": None,
                "completed_at": None
            }
        
        # Start background task
        asyncio.create_task(run_multi_persona_sessions_background(batch_id, request))
        
        return MultiPersonaTestingResponse(
            success=True,
            batch_id=batch_id,
            message=f"Started sessions for {len(request.persona_ids)} personas",
            total_personas=len(request.persona_ids)
        )
        
    except Exception as e:
        return MultiPersonaTestingResponse(
            success=False,
            batch_id="",
            message="Failed to start multi-persona sessions",
            total_personas=0,
            error=str(e)
        )


@app.get("/batch-status/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """Get the status of a multi-persona testing batch"""
    if batch_id not in multi_session_status:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    batch_data = multi_session_status[batch_id]
    persona_statuses = [
        PersonaSessionStatus(**status) 
        for status in batch_data["persona_statuses"].values()
    ]
    
    # Count statuses
    completed = sum(1 for s in persona_statuses if s.status == "completed")
    failed = sum(1 for s in persona_statuses if s.status == "failed")
    running = sum(1 for s in persona_statuses if s.status == "running")
    pending = sum(1 for s in persona_statuses if s.status == "pending")
    
    return BatchStatusResponse(
        batch_id=batch_id,
        total_personas=batch_data["total_personas"],
        completed=completed,
        failed=failed,
        running=running,
        pending=pending,
        overall_status=batch_data.get("overall_status", "pending"),
        persona_statuses=persona_statuses
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Virtual User Conversation Testing API",
        "version": "1.0.0",
        "description": (
            "Platform for testing conversational agents with virtual users"
        ),
        "endpoints": {
            "POST /run-virtual-user-testing":
                "Run a virtual user testing session with a persona",
            "POST /run-multi-persona-testing":
                "Run virtual user testing sessions for multiple personas",
            "GET /batch-status/{batch_id}":
                "Get status of a multi-persona testing batch",
            "GET /health": "Health check",
            "GET /": "This endpoint",
            "GET /personas": "List all virtual users (basic info)",
            "GET /personas/full": "List all virtual users (full details)",
            "GET /personas/{persona_id}": "Get a specific virtual user",
            "GET /sessions": "List all completed testing sessions",
        }
    }


@app.get("/personas", response_model=List[Dict[str, str]])
async def list_personas():
    """Get a list of all virtual users in the database"""
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


@app.get("/personas/full", response_model=List[PersonaResponse])
async def list_personas_full():
    """Get all virtual users with full details in one call"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        personas = persona_db.get_all_personas()
        result = []
        
        for persona in personas:
            try:
                persona_dict = persona.to_dict()
                
                # Clean survey responses to handle NaN values
                if 'survey_responses' in persona_dict:
                    cleaned_responses = {}
                    for key, value in persona_dict['survey_responses'].items():
                        if (
                            value is None or
                            (isinstance(value, float) and math.isnan(value))
                        ):
                            cleaned_responses[key] = ""
                        else:
                            cleaned_responses[key] = str(value)
                    persona_dict['survey_responses'] = cleaned_responses
                
                persona_response = PersonaResponse(
                    **persona_dict,
                    id=persona.id
                )
                result.append(persona_response)
            except Exception as validation_error:
                # Skip personas with validation issues but continue processing
                print(
                    f"Validation error for persona {persona.id}: "
                    f"{validation_error}"
                )
                continue
                
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )


@app.get("/sessions")
async def list_sessions():
    """Get a list of all completed testing sessions"""
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
    """Get a specific virtual user by ID"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        persona = persona_db.get_persona_by_id(persona_id)
        if not persona:
            raise HTTPException(
                status_code=404, detail=f"Virtual user {persona_id} not found"
            )
        
        return PersonaResponse(**persona.to_dict(), id=persona.id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )


@app.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a specific testing session by ID"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        session = session_db.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )
        
        return SessionResponse(**session.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database error: {e}"
        )


@app.post("/load-personas")
async def load_personas_from_files():
    """Load virtual users from JSON files into the database"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        personas_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'personas')
        )
        
        if not os.path.exists(personas_dir):
            raise HTTPException(
                status_code=404, detail="Virtual users directory not found"
            )
        
        count = persona_db.load_personas_from_json_files(personas_dir)
        return {
            "message": f"Successfully loaded {count} virtual users",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading virtual users: {e}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
