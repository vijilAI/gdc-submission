import uvicorn
import os
import sys

# Add the current directory to the path so we can import api
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from api import app

if __name__ == "__main__":
    uvicorn.run(
        "api:app",  # Use string import for reload to work
        host="0.0.0.0", 
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
