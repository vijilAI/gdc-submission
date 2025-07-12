# Global Dialogues with AI: Simulating Diverse User Preferences on AI Interactions

An exploratory platform for understanding how AI conversational agents interact with diverse, culturally-aware virtual users based on the Global Dialogues Challenge dataset. This system facilitates conversations between virtual users from different backgrounds and AI assistants to explore cultural preferences and communication patterns with AI across global demographics.

## 📖 Table of Contents

- [🌟 Key Features](#-key-features)
- [🚀 Quick Start](#-quick-start)
- [📱 Frontend Interface](#-frontend-interface)
- [�️ Architecture](#️-architecture)
- [🎭 Configuring Different Chatbots](#-configuring-different-chatbots)
- [🌍 Understanding Virtual Users](#-understanding-virtual-users)
- [📊 Analysis and Insights](#-analysis-and-insights)
- [🔧 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [🆘 Support](#-support)

## 🌟 Key Features

- **🌍 Diverse Virtual Users**: Personas representing people from around the world with different backgrounds, languages, and perspectives on AI
- **🔍 Cultural Exploration**: Generate contextual goals and facilitate authentic conversations to explore cultural nuances
- **📊 Rich Insights**: Examine how demographics influence AI interactions and communication patterns
- **🔄 Batch Exploration**: Engage multiple personas simultaneously for comprehensive cultural insights
- **📱 Interactive Web Interface**: Clean, modern Streamlit frontend for intuitive exploration
- **🔧 Configurable Agents**: Easy configuration for exploring different chatbots and AI systems

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** with pip
2. **Together AI API Key** (for LLM access)
3. **Git** for cloning the repository

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd gdc-submission
   ```

2. **Install dependencies**:

    Create a new virtual environment using your favorite environment manager and install dependencies.

   ```bash
   pip install .
   ```
   # Or if using Poetry:
   ```bash
   poetry install
   ```

   Activate your virtual environment. If you're using poetry, you can do this with
   ```bash
   $(poetry env activate)
   ```

3. **Set up environment variables**:

   Create an `.env` file in the root directory of the repository and add your Together AI API key. Example `.env` file:

   ```bash
   TOGETHER_API_KEY=your_together_ai_api_key
   ```

   Alternatively, manually set your `TOGETHER_API_KEY` environment variable as follows:

   ```bash
   export TOGETHER_API_KEY="your_together_ai_api_key"
   ```

### Running the Application

**Start the API Server**:
```bash
python app/api/run_api.py
```
The API will be available at `http://localhost:8000`.

After starting the API server, you can interact with it through the frontend or through API calls.

## 📱 Frontend Interface

The Streamlit-based frontend provides an intuitive interface to select your virtual users and run sessions where they interact with the chatbot..

### Navigation Pages

1. **🏠 Getting Started**
   - Platform overview and quick stats
   - Workflow guidance and tips
   - Virtual user statistics and demographics overview

2. **👥 Browse Personas**
   - View all virtual users in the database
   - Advanced filtering by demographics, language, opinions about AI
   - Select personas for exploration sessions
   - Detailed persona information cards

3. **▶️ Run Sessions**
   - Configure session parameters (goals, turns, conversations)
   - Run exploration sessions with selected personas
   - Real-time progress tracking with visual feedback
   - Conditional UI: persona selection panel or configuration interface

4. **📊 Session Results**
   - View conversation results organized by goal type
   - Export session data as JSON
   - Browse conversation transcripts
   - Download results for further analysis

5. **🔬 Session Analysis**
   - Analyze patterns across demographics
   - Generate insights from conversation data
   - Visualize cultural differences in AI interactions

### Frontend Setup and Usage

#### Prerequisites

Make sure you have installed the project dependencies as outlined in the [Installation](#-installation) section.

#### Running the Frontend

1. **Start the API Server** (required):
   ```bash
   cd /path/to/gdc-submission
   python app/api/run_api.py
   ```
   The API will be available at `http://localhost:8000`

2. **Start the Streamlit Frontend**:
   ```bash
   cd app/frontend
   python run_streamlit.py
   ```
   
   Or directly with Streamlit:
   ```bash
   streamlit run streamlit_app.py --server.port=8501
   ```

3. **Access the Application**:
   Open your browser and go to `http://localhost:8501`

## 🎭 Configuring Different Chatbots

The platform comes pre-configured with "Alex" - a Mental Health Assistant, but you can easily configure it to explore any chatbot or AI system. This section provides comprehensive instructions for setting up custom chatbots for cultural exploration.

### Quick Start: Creating a New Chatbot

1. **Create a new YAML config file** in `src/configs/`:
   ```bash
   cp src/configs/alex.yaml src/configs/your_bot.yaml
   ```

2. **Edit the configuration** with your chatbot's details:

```yaml
metadata:
    id: your-bot-id
    name: Your Bot Name
    description: Description of your chatbot's purpose
    version: 1.0.0

llm:
    hub: together  # Options: together, openai, anthropic
    model: meta-llama/Llama-Vision-Free-7B-Instruct  # Your preferred model
    params:
        temperature: 0.7
        max_completion_tokens: 1024

templates:
    system_prompt: |
        # ROLE: 
        You are [Your Bot Name], a [description of bot's purpose].
        
        # CORE CAPABILITIES:
        - [List your bot's main functions]
        - [What topics it covers]
        - [Any special features]
        
        # GUIDELINES:
        - [How it should behave]
        - [Response style]
        - [Any restrictions]
        
        # CONVERSATION RULES:
        1. [Rule 1: e.g., Always be helpful and respectful]
        2. [Rule 2: e.g., Stay within your domain expertise]
        3. [Rule 3: e.g., Ask clarifying questions when needed]
```

### Step-by-Step Configuration Process

#### Step 1: Update API Configuration

Edit `app/api/api.py` to use your new configuration:

```python
# Find this line (around line 15-20) and change it:
AGENT_CONFIG_PATH = "src/configs/your_bot.yaml"  # Change from alex.yaml
```

#### Step 2: Update Frontend Description

Edit `app/frontend/streamlit_app.py` to describe your chatbot:

```python
# In the run_sessions_page() function, find the agent description and update:
st.markdown("""
In this exercise, we let our virtual users chat with **Your Bot Name**, 
a specialized conversational agent focused on [your bot's domain].

Its key capabilities include:
- 🎯 [Capability 1: e.g., Answering questions about X]
- 💡 [Capability 2: e.g., Providing guidance on Y]
- 🔧 [Capability 3: e.g., Helping with Z tasks]

The bot adapts its responses based on the cultural background and preferences 
of each virtual user, allowing us to test how different demographics interact 
with AI systems in [your domain].
""")
```

#### Step 3: Restart and Test

1. **Restart the API server**:
   ```bash
   # Stop the current server (Ctrl+C) and restart
   python app/api/run_api.py
   ```

2. **Explore the configuration**:
   - Visit the frontend at `http://localhost:8501`
   - Select a persona and run an exploration session
   - Observe how your bot responds according to its configuration

### Troubleshooting Configuration Issues

#### Common Configuration Problems

1. **YAML Syntax Errors**
   ```bash
   # Test YAML syntax
   python -c "import yaml; yaml.safe_load(open('src/configs/your_bot.yaml'))"
   ```

2. **Missing Required Fields**
   - Ensure all required fields are present: `metadata`, `llm`, `templates`
   - Check that `system_prompt` is properly indented

3. **Model Not Found**
   - Verify model name is correct for your LLM provider
   - Check API credentials are properly set

4. **Variable Substitution Issues**
   - Test variables with simple personas first
   - Ensure variable names match exactly (case-sensitive)

#### Testing Your Configuration

1. **Quick API Test**:
   ```bash
   curl -X POST http://localhost:8000/health
   ```

2. **Configuration Validation**:
   ```bash
   # Check if config loads properly
   python -c "
   import yaml
   with open('src/configs/your_bot.yaml') as f:
       config = yaml.safe_load(f)
       print('✅ Configuration loaded successfully')
       print(f'Bot: {config[\"metadata\"][\"name\"]}')
   "
   ```

3. **Frontend Integration Exploration**:
   - Load the frontend and navigate to "Run Sessions"
   - Select a simple persona (e.g., English-speaking user)
   - Run a short 2-turn conversation to explore functionality



## 🏗️ Architecture

### Project Structure

```
gdc-submission/
├── app/
│   ├── api/                    # FastAPI backend
│   │   ├── api.py             # Main API endpoints
│   │   └── run_api.py         # API server launcher
│   ├── db/                    # Database models and operations
│   └── frontend/              # Streamlit web interface
│       └── streamlit_app.py   # Main application
├── src/
│   ├── configs/               # Chatbot configurations
│   │   ├── alex.yaml         # Default: Mental Health Assistant
│   │   ├── goal_generator.yaml # Goal generation config
│   │   └── tester.yaml       # Virtual user config
│   ├── agents/               # Core agent logic
│   └── creation/            # Persona creation utilities
├── personas/                 # Persona JSON files
├── scripts/                 # Utility scripts
└── notebooks/               # Analysis notebooks
```

### System Components

1. **Virtual Users**: Culturally-aware personas based on real survey data
2. **Goal Generator**: Creates realistic conversation objectives
3. **Conversation Engine**: Manages multi-turn dialogues for cultural exploration
4. **Results Analysis**: Processes and visualizes outcomes
5. **Web Interface**: User-friendly frontend for intuitive exploration

## 🌍 Understanding Virtual Users

Virtual users are based on the Global Dialogues Challenge dataset and represent real people from around the world:

### Demographics Covered
- **195+ Countries**: Global representation
- **50+ Languages**: Multilingual perspectives
- **All Age Groups**: From young adults to seniors
- **Diverse Backgrounds**: Various religions, communities, education levels
- **AI Attitudes**: From enthusiastic to skeptical

### Conversation Realism
- **Cultural Context**: Responses reflect cultural backgrounds
- **Authentic Goals**: Realistic conversation objectives
- **Natural Patterns**: Human-like interaction styles
- **Contextual Adaptation**: Adjusts based on bot responses

## 📊 Analysis and Insights

### What You Can Discover

1. **Cultural Patterns**: How different cultures approach AI interactions
2. **Language Preferences**: Communication style variations
3. **Demographic Trends**: Age, gender, location-based differences
4. **AI Perception**: How attitudes toward AI affect conversations
5. **Goal Variations**: What different groups want from AI

### Export and Analysis

- **JSON Export**: Download complete session data
- **Conversation Transcripts**: Full dialogue records
- **Metadata**: Persona demographics and session parameters
- **Statistical Analysis**: Integration with analysis tools

### Development Guidelines

- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation for changes
- Test with multiple persona configurations

## 📝 License

This project is licensed under [LICENSE](LICENSE) - see the file for details.