import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, List, Any
import time

# Configuration
API_BASE = "http://localhost:8000"

# Set page config
st.set_page_config(
    page_title="GDC Persona Red Teaming",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .persona-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .selected-persona {
        background: #e3f2fd !important;
        border-color: #2196f3 !important;
    }
    
    .status-success {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    
    .status-error {
        background: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
    
    .status-info {
        background: #d1ecf1;
        color: #0c5460;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #bee5eb;
    }
</style>
""", unsafe_allow_html=True)

def check_api_health() -> bool:
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_BASE}/health")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def load_personas() -> List[Dict[str, Any]]:
    """Load personas from the API"""
    try:
        response = requests.get(f"{API_BASE}/personas")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load personas: HTTP {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return []

def get_persona_details(persona_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific persona"""
    try:
        response = requests.get(f"{API_BASE}/personas/{persona_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get persona details: HTTP {response.status_code}")
            return {}
    except requests.exceptions.RequestException as e:
        st.error(f"Error getting persona details: {e}")
        return {}

def run_red_teaming_session(persona_id: str, num_goals: int, max_turns: int, verbose: bool) -> Dict[str, Any]:
    """Run a red teaming session via the API"""
    try:
        session_data = {
            "persona_fname": persona_id,
            "num_goals": num_goals,
            "max_turns": max_turns,
            "verbose": verbose,
            "use_db": True
        }
        
        response = requests.post(f"{API_BASE}/run-red-teaming-session", json=session_data)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Session failed: HTTP {response.status_code}")
            st.error(f"Response: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error running session: {e}")
        return {"success": False, "error": str(e)}

def display_conversation_results(results: Dict[str, Any]):
    """Display the conversation results in a formatted way"""
    if not results.get("success"):
        st.error(f"Session failed: {results.get('error', 'Unknown error')}")
        return
    
    session_data = results.get("session_data", {})
    
    st.success("✅ Session completed successfully!")
    
    # Create tabs for different goal types
    goal_types = list(session_data.keys())
    if goal_types:
        tabs = st.tabs([f"🎯 {goal_type.replace('_', ' ').title()}" for goal_type in goal_types])
        
        for i, goal_type in enumerate(goal_types):
            with tabs[i]:
                conversations = session_data[goal_type]
                
                if isinstance(conversations, list) and conversations:
                    for j, conversation in enumerate(conversations):
                        st.subheader(f"Conversation {j + 1}")
                        
                        # Display goal
                        if hasattr(conversation, 'goal') or (isinstance(conversation, dict) and 'goal' in conversation):
                            goal = conversation.goal if hasattr(conversation, 'goal') else conversation['goal']
                            st.info(f"**Goal:** {goal}")
                        
                        # Display turns
                        if hasattr(conversation, 'turns') or (isinstance(conversation, dict) and 'turns' in conversation):
                            turns = conversation.turns if hasattr(conversation, 'turns') else conversation['turns']
                            
                            for turn in turns:
                                turn_data = turn if isinstance(turn, dict) else turn.__dict__
                                role = turn_data.get('role', 'unknown')
                                content = turn_data.get('content', '')
                                turn_id = turn_data.get('id', '')
                                
                                # Style based on role
                                if role.lower() == 'user':
                                    st.markdown(f"**🔴 Red Teamer ({turn_id}):**")
                                    st.markdown(f"> {content}")
                                else:
                                    st.markdown(f"**🤖 Assistant ({turn_id}):**")
                                    st.markdown(f"> {content}")
                                
                                st.markdown("---")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.info(f"No conversations found for {goal_type}")

# Main app
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 GDC Persona Red Teaming Platform</h1>
        <p>Interactive persona-based AI red teaming interface</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API health
    if not check_api_health():
        st.error("❌ API server is not responding. Please start it with: `python app/api/run_api.py`")
        st.stop()
    else:
        st.sidebar.success("✅ API server is running")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page:",
        ["👥 Browse Personas", "🎯 Run Session", "📊 Session Results"]
    )
    
    # Initialize session state
    if 'personas' not in st.session_state:
        st.session_state.personas = []
    if 'selected_persona' not in st.session_state:
        st.session_state.selected_persona = None
    if 'session_results' not in st.session_state:
        st.session_state.session_results = None
    
    # Page 1: Browse Personas
    if page == "👥 Browse Personas":
        st.header("Available Personas")
        
        # Load personas button
        if st.button("🔄 Refresh Personas", type="primary"):
            with st.spinner("Loading personas..."):
                st.session_state.personas = load_personas()
        
        # Load personas on first visit
        if not st.session_state.personas:
            with st.spinner("Loading personas..."):
                st.session_state.personas = load_personas()
        
        if st.session_state.personas:
            st.success(f"Found {len(st.session_state.personas)} personas in database")
            
            # Create columns for persona grid
            cols = st.columns(3)
            
            for i, persona in enumerate(st.session_state.personas):
                col = cols[i % 3]
                
                with col:
                    # Create persona card
                    card_class = "selected-persona" if st.session_state.selected_persona == persona['id'] else "persona-card"
                    
                    st.markdown(f"""
                    <div class="{card_class}">
                        <strong>{persona['id']}</strong><br>
                        <span style="background: #2196f3; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em;">
                            {persona['response_language']}
                        </span><br>
                        <small>ID: {persona['participant_id']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Select", key=f"select_{persona['id']}", use_container_width=True):
                        st.session_state.selected_persona = persona['id']
                        st.success(f"Selected: {persona['id']}")
                        
                    if st.button(f"View Details", key=f"details_{persona['id']}", use_container_width=True):
                        with st.spinner("Loading persona details..."):
                            details = get_persona_details(persona['id'])
                            if details:
                                st.json(details)
        else:
            st.warning("No personas found. Make sure the database is populated.")
    
    # Page 2: Run Session
    elif page == "🎯 Run Session":
        st.header("Configure Red Teaming Session")
        
        # Check if persona is selected
        if not st.session_state.selected_persona:
            st.warning("Please select a persona from the 'Browse Personas' page first.")
            st.stop()
        
        st.info(f"Selected Persona: **{st.session_state.selected_persona}**")
        
        # Session configuration
        col1, col2 = st.columns(2)
        
        with col1:
            num_goals = st.slider(
                "Number of Goals",
                min_value=1,
                max_value=10,
                value=3,
                help="Number of goals to generate for the session"
            )
            
            max_turns = st.slider(
                "Maximum Turns",
                min_value=1,
                max_value=20,
                value=5,
                help="Maximum number of conversation turns"
            )
        
        with col2:
            verbose = st.checkbox(
                "Verbose Output",
                value=True,
                help="Enable detailed output during session"
            )
            
            st.markdown("### Session Preview")
            st.json({
                "persona": st.session_state.selected_persona,
                "num_goals": num_goals,
                "max_turns": max_turns,
                "verbose": verbose
            })
        
        # Run session button
        if st.button("🚀 Run Red Teaming Session", type="primary", use_container_width=True):
            with st.spinner("Running red teaming session... This may take a few minutes."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate progress (since we can't get real progress from the API)
                for i in range(100):
                    progress_bar.progress(i + 1)
                    if i < 20:
                        status_text.text("Initializing session...")
                    elif i < 50:
                        status_text.text("Generating goals...")
                    elif i < 80:
                        status_text.text("Running conversations...")
                    else:
                        status_text.text("Finalizing results...")
                    time.sleep(0.05)
                
                # Actually run the session
                results = run_red_teaming_session(
                    st.session_state.selected_persona,
                    num_goals,
                    max_turns,
                    verbose
                )
                
                progress_bar.empty()
                status_text.empty()
                
                if results.get("success"):
                    st.session_state.session_results = results
                    st.success("Session completed! View results in the 'Session Results' tab.")
                    st.balloons()
                else:
                    st.error(f"Session failed: {results.get('error', 'Unknown error')}")
    
    # Page 3: Session Results
    elif page == "📊 Session Results":
        st.header("Session Results")
        
        if st.session_state.session_results:
            display_conversation_results(st.session_state.session_results)
            
            # Option to download results
            if st.button("💾 Download Results as JSON"):
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(st.session_state.session_results, indent=2),
                    file_name=f"red_teaming_results_{st.session_state.selected_persona}.json",
                    mime="application/json"
                )
        else:
            st.info("No session results yet. Run a session first!")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
        <p>GDC Persona Red Teaming Platform | Built with Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
