#!/usr/bin/env python3
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
