#!/usr/bin/env python3
"""
Script to run the Streamlit frontend for the Virtual User Testing application.
"""
import subprocess
import sys
import os

def main():
    """Run the Streamlit app"""
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'streamlit_app.py')
    
    # Check if streamlit_app.py exists
    if not os.path.exists(app_path):
        print(f"Error: {app_path} not found!")
        return 1
    
    # Run Streamlit
    try:
        cmd = [sys.executable, '-m', 'streamlit', 'run', app_path, '--server.port=8501']
        print(f"Starting Streamlit app...")
        print(f"Command: {' '.join(cmd)}")
        print(f"App will be available at: http://localhost:8501")
        print("Press Ctrl+C to stop the server")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\nStreamlit app stopped.")
        return 0
    except Exception as e:
        print(f"Error running Streamlit: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
