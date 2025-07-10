import requests
import json
import os

# API endpoint
API_URL = "http://localhost:8000"

def run_red_teaming_session(persona_fname, target_agent_config=None, num_goals=None, max_turns=None, verbose=True):
    """
    Example function to call the red teaming API
    """
    payload = {
        "persona_fname": persona_fname,
        "verbose": verbose
    }
    
    if target_agent_config:
        payload["target_agent_config"] = target_agent_config
    if num_goals:
        payload["num_goals"] = num_goals
    if max_turns:
        payload["max_turns"] = max_turns
    
    response = requests.post(f"{API_URL}/run-red-teaming-session", json=payload)
    return response.json()

# Example usage
if __name__ == "__main__":
    # Example persona file path (adjust as needed)
    persona_file = os.path.join('baseline_personas', '2d33bd32-ca14-4ab2-813e-8b1eb0fea04d_English.json')
    
    try:
        result = run_red_teaming_session(
            persona_fname=persona_file,
            num_goals=5,
            max_turns=10
        )
        
        if result['success']:
            print("Session completed successfully!")
            print(f"Good faith score: {result['good_faith']}")
        else:
            print(f"Session failed: {result['error']}")
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to API. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"Error: {e}")
