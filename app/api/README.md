# API Documentation

This directory contains the API components for the GDC Persona Application.

## Files

- `api.py` - Main FastAPI application with endpoints for virtual user testing sessions
- `run_api.py` - Script to start the API server
- `example_api_usage.py` - Example usage of the API endpoints

## API Endpoints

### Health Check
- **GET** `/health` - Check if the API is running
- Response: `{"status": "healthy"}`

### Virtual User Testing Session
- **POST** `/run-virtual-user-testing` - Run a virtual user testing session with a persona
- Request body:
  ```json
  {
    "persona_fname": "2d33bd32-ca14-4ab2-813e-8b1eb0fea04d_English",
    "num_goals": 5,
    "max_turns": 10,
    "use_db": true
  }
  ```

### Persona Management
- **GET** `/personas` - List all personas in the database
- **GET** `/personas/{persona_id}` - Get a specific persona by ID
- **POST** `/load-personas` - Load personas from JSON files into database
- Response:
  ```json
  {
    "success": true,
    "good_faith": [...],
    "session_data": {...}
  }
  ```

## Usage Example

```python
import requests

# Check API health
response = requests.get("http://localhost:8000/health")
print(response.json())

# Run a session using persona ID (database lookup)
session_data = {
    "persona_fname": "2d33bd32-ca14-4ab2-813e-8b1eb0fea04d_English",
    "num_goals": 5,
    "max_turns": 10,
    "use_db": True
}

response = requests.post("http://localhost:8000/run-virtual-user-testing", json=session_data)

# Or run a session using JSON file path
session_data_file = {
    "persona_fname": "src/baseline_personas/2d33bd32-ca14-4ab2-813e-8b1eb0fea04d_English.json",
    "num_goals": 5,
    "max_turns": 10,
    "use_db": False
}

response = requests.post("http://localhost:8000/run-virtual-user-testing", json=session_data_file)
result = response.json()

if result["success"]:
    print(f"Session completed. Good faith results: {result['good_faith']}")
```

## Notes

- Ensure the persona files exist in the `src/baseline_personas/` directory
- The API server must be running before making requests
- All file paths in requests should be relative to the repository root

## Database

The application now uses SQLite database to store persona data for efficient querying.

### Database Setup

1. **Populate Database**: Load personas from JSON files
   ```bash
   python scripts/populate_db.py
   ```

2. **Via API**: Load personas using the API endpoint
   ```bash
   curl -X POST http://localhost:8000/load-personas
   ```

### Database Schema

The `personas` table contains:
- `id` (Primary Key): Persona filename without .json extension
- `participant_id`: Original participant ID
- `response_language`: Language of responses
- `high_level_AI_view`: High-level AI perspective 
- `demographic_info`: JSON string of demographic data
- `survey_responses`: JSON string of survey responses
- `created_at`, `updated_at`: Timestamps

### Using Database vs JSON Files

**Database Mode (Recommended)**:
```python
# In run_session calls
result = await run_session_from_config(
    persona_config="2d33bd32-ca14-4ab2-813e-8b1eb0fea04d_English",
    target_agent_config="configs/alex.yaml",
    use_db=True  # Default
)
```

**File Mode**:
```python
result = await run_session_from_config(
    persona_config="path/to/persona.json",
    target_agent_config="configs/alex.yaml", 
    use_db=False
)
```
