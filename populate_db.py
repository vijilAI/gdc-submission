#!/usr/bin/env python3
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

"""
Script to populate the database with personas from JSON files.
Run this after starting the API server.
"""

import requests
import sys

API_BASE = "http://localhost:8000"


def populate_database():
    """Load personas from JSON files into the database"""
    try:
        # Check if API is running
        health_response = requests.get(f"{API_BASE}/health")
        if health_response.status_code != 200:
            print("❌ API server is not running. Please start it first with:")
            print("   python app/api/run_api.py")
            return False

        print("✅ API server is running")

        # Load personas
        print("📥 Loading personas from JSON files...")
        response = requests.post(f"{API_BASE}/load-personas")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ Failed to load personas: {response.status_code}")
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('application/json'):
                error_detail = response.json().get('detail', 'Unknown error')
                print(f"   Error: {error_detail}")
            else:
                print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Please start it first with:")
        print("   python app/api/run_api.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Populating database with personas...")
    success = populate_database()
    
    if success:
        print("\n🎉 Database populated successfully!")
        print("You can now use the Streamlit frontend.")
    else:
        print("\n💥 Failed to populate database.")
        sys.exit(1)
