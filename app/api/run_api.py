import uvicorn
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

import os
import sys

# Add the current directory to the path so we can import api
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# from api import app

if __name__ == "__main__":
    uvicorn.run(
        "api:app",  # Use string import for reload to work
        host="0.0.0.0", 
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
