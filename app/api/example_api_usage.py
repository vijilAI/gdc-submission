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

import requests
import json
import os

# API endpoint
API_URL = "http://localhost:8000"

def run_virtual_user_testing_session(
    persona_fname, target_agent_config=None, num_goals=None,
    max_turns=None, verbose=True
):
    """
    Example function to call the virtual user testing API
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
    
    response = requests.post(
        f"{API_URL}/run-virtual-user-testing", json=payload
    )
    return response.json()

# Example usage
if __name__ == "__main__":
    # Example persona file path (adjust as needed)
    persona_file = os.path.join('baseline_personas', '2d33bd32-ca14-4ab2-813e-8b1eb0fea04d_English.json')
    
    try:
        result = run_virtual_user_testing_session(
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
