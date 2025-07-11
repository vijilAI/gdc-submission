import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, List, Any
import time
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer

# Configuration
API_BASE = "http://localhost:8000"

# Set page config
st.set_page_config(
    page_title="GDC Conversational Agent Testing",
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
    
    .stButton>button[kind="primary"] {
        background-color: #4CAF50;
        color: white;
        border-color: #4CAF50;
    }

    .stButton>button[kind="primary"]:hover {
        background-color: #45a049;
        color: white;
        border-color: #45a049;
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
    """Load all personas with full details from the API"""
    try:
        response = requests.get(f"{API_BASE}/personas/full")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load personas: HTTP {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return []


def run_agent_testing_session(
    persona_id: str, num_goals: int, max_turns: int,
    conversations_per_goal: int, verbose: bool
) -> Dict[str, Any]:
    """Run an agent testing session via the API."""
    payload = {
        "persona_fname": persona_id,
        "num_goals": num_goals,
        "max_turns": max_turns,
        "conversations_per_goal": conversations_per_goal,
        "verbose": verbose,
    }
    try:
        response = requests.post(
            f"{API_BASE}/run-virtual-user-testing", json=payload
        )
        if response.status_code == 200:
            return {"success": True, **response.json()}
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return {"success": False, "error": error_detail}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def run_multi_persona_testing_session(
    persona_ids: List[str], num_goals: int, max_turns: int,
    conversations_per_goal: int, verbose: bool
) -> Dict[str, Any]:
    """Run testing sessions for multiple personas via the API."""
    payload = {
        "persona_ids": persona_ids,
        "num_goals": num_goals,
        "max_turns": max_turns,
        "conversations_per_goal": conversations_per_goal,
        "verbose": verbose,
    }
    try:
        response = requests.post(
            f"{API_BASE}/run-multi-persona-testing", json=payload
        )
        if response.status_code == 200:
            return {"success": True, **response.json()}
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return {"success": False, "error": error_detail}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def get_batch_status(batch_id: str) -> Dict[str, Any]:
    """Get the status of a multi-persona testing batch."""
    try:
        response = requests.get(f"{API_BASE}/batch-status/{batch_id}")
        if response.status_code == 200:
            return {"success": True, **response.json()}
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return {"success": False, "error": error_detail}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def display_batch_status(batch_status: Dict[str, Any]):
    """Display the status of a multi-persona testing batch."""
    if not batch_status.get("success", False):
        st.error(f"Error getting batch status: {batch_status.get('error', 'Unknown error')}")
        return
    
    batch_data = batch_status
    st.subheader(f"Batch Status: {batch_data['batch_id']}")
    
    # Overall progress
    total = batch_data['total_personas']
    completed = batch_data['completed']
    failed = batch_data['failed']
    running = batch_data['running']
    pending = batch_data['pending']
    
    # Progress bar
    progress = completed / total if total > 0 else 0
    st.progress(progress, text=f"Overall Progress: {completed}/{total} personas completed")
    
    # Status summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Completed", completed, delta=None)
    with col2:
        st.metric("Running", running, delta=None)
    with col3:
        st.metric("Pending", pending, delta=None)
    with col4:
        st.metric("Failed", failed, delta=None)
    
    # Detailed status for each persona
    st.subheader("Individual Persona Status")
    for persona_status in batch_data['persona_statuses']:
        with st.expander(f"Persona: {persona_status['persona_id']} - {persona_status['status'].title()}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Status:** {persona_status['status']}")
                st.write(f"**Message:** {persona_status['message']}")
                if persona_status.get('error'):
                    st.error(f"Error: {persona_status['error']}")
                if persona_status.get('session_id'):
                    st.success(f"Session ID: {persona_status['session_id']}")
            with col2:
                if persona_status['status'] == 'running':
                    st.progress(persona_status['progress'] / 100)
                elif persona_status['status'] == 'completed':
                    st.success("✅ Complete")
                elif persona_status['status'] == 'failed':
                    st.error("❌ Failed")
                else:
                    st.info("⏳ Pending")

def load_sessions() -> List[Dict[str, Any]]:
    """Load session history from the API."""
    try:
        response = requests.get(f"{API_BASE}/sessions")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to load sessions: HTTP {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to API: {e}")
        return []


def display_pretty_persona(details: Dict[str, Any]):
    """Display persona details in a well-formatted way."""
    st.subheader(f"Persona ID: {details.get('id', 'N/A')}")

    st.markdown(f"""
    - **Participant ID:** `{details.get('participant_id', 'N/A')}`
    - **Language:** `{details.get('response_language', 'N/A')}`
    """)

    tab_titles = [
        "Demographics",
        "Survey Responses",
    ]
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        demographics = details.get('demographic_info', {})
        country = demographics.get('self identified country', 'N/A')
        st.markdown(f"""
        - **Age Bracket:** {demographics.get('age bracket', 'N/A')}
        - **Gender:** {demographics.get('gender', 'N/A')}
        - **Religion:** {demographics.get('religion', 'N/A')}
        - **Country of Residence:** {country}
        - **Community Type:** {demographics.get('community type', 'N/A')}
        - **Preferred Language:** {details.get('response_language', 'N/A')}
        """)

    with tabs[1]:
        survey_responses = details.get('survey_responses', {})
        if survey_responses:
            for question, answer in survey_responses.items():
                st.markdown(f"❓ {question}")
                st.markdown(f"> {answer}")
                st.markdown("---")
        else:
            st.info("No survey responses available.")
            

def display_conversation_results(results: Dict[str, Any]):
    """Display the conversation results in a formatted way"""
    session_id = results.get('session_id') or results.get('id')
    session_data = results.get("session_data", {})

    # For historical sessions, session_data might be a JSON string,
    # and might even be double-encoded.
    if isinstance(session_data, str):
        try:
            session_data = json.loads(session_data)
            # Handle cases where it might be double-encoded
            if isinstance(session_data, str):
                session_data = json.loads(session_data)
        except json.JSONDecodeError:
            st.error("Failed to parse session data.")
            session_data = {}

    if session_id:
        st.success(f"✅ Session `{session_id}` results:")
    elif results.get("success"):
        st.success("✅ Session completed successfully!")
    else:
        st.error(f"Session failed: {results.get('error', 'Unknown error')}")
        return

    # Create tabs for different goal types
    goal_types = list(session_data.keys())
    if goal_types:
        tab_titles = [
            f"🎯 {goal_type.replace('_', ' ').title()}"
            for goal_type in goal_types
        ]
        tabs = st.tabs(tab_titles)

        for i, goal_type in enumerate(goal_types):
            with tabs[i]:
                conversation_data = session_data[goal_type]

                # Handle both single conversation objects and lists
                conversations_to_display = []
                if isinstance(conversation_data, list):
                    conversations_to_display = conversation_data
                elif conversation_data is not None:
                    # Single conversation object
                    conversations_to_display = [conversation_data]

                if conversations_to_display:
                    # Display the goal only once at the top of the tab
                    first_conversation = conversations_to_display[0]
                    
                    # Parse the first conversation to get the goal
                    if isinstance(first_conversation, str):
                        try:
                            parsed_conv = json.loads(first_conversation)
                            goal = parsed_conv.get('goal', 'Unknown Goal')
                        except json.JSONDecodeError:
                            goal = 'Unknown Goal'
                    elif isinstance(first_conversation, dict):
                        goal = first_conversation.get('goal', 'Unknown Goal')
                    elif hasattr(first_conversation, 'goal'):
                        goal = getattr(first_conversation, 'goal', 'Unknown Goal')
                    else:
                        goal = 'Unknown Goal'
                    
                    # Display goal once at the top
                    st.info(f"**Goal:** {goal}")
                    st.markdown("---")

                    # Display each conversation in a collapsible expander
                    for j, conversation_item in enumerate(
                        conversations_to_display
                    ):
                        # Handle different data formats
                        conversation = None
                        if isinstance(conversation_item, str):
                            try:
                                conversation = json.loads(conversation_item)
                            except json.JSONDecodeError as e:
                                st.error(f"Could not parse conversation: {e}")
                                st.write(f"Raw: {conversation_item[:200]}...")
                                continue
                        elif isinstance(conversation_item, dict):
                            conversation = conversation_item
                        elif hasattr(conversation_item, 'goal') and \
                                hasattr(conversation_item, 'turns'):
                            # Handle Conversation objects directly
                            conversation = {
                                'goal': getattr(
                                    conversation_item, 'goal', None
                                ),
                                'turns': getattr(
                                    conversation_item, 'turns', []
                                ),
                                'id': getattr(conversation_item, 'id', None)
                            }
                        elif hasattr(conversation_item, '__dict__'):
                            # Handle other objects with attributes
                            conversation = conversation_item.__dict__
                        else:
                            conv_type = type(conversation_item)
                            st.error(f"Unknown format: {conv_type}")
                            continue

                        # Create collapsible section for each conversation
                        conv_title = f"Conversation {j + 1}"
                        if len(conversations_to_display) == 1:
                            # If only one conversation, expand by default
                            with st.expander(conv_title, expanded=True):
                                display_conversation_turns(conversation)
                        else:
                            # Multiple conversations, collapse by default
                            with st.expander(conv_title, expanded=False):
                                display_conversation_turns(conversation)

                else:
                    st.info(f"No conversations found for {goal_type}")
    else:
        st.info("No session data available to display.")


def display_conversation_turns(conversation):
    """Helper function to display conversation turns"""
    # Display turns
    turns = conversation.get('turns', [])
    if turns:
        for turn_item in turns:
            # The turn might be a string in older data
            if isinstance(turn_item, str):
                try:
                    turn = json.loads(turn_item)
                except json.JSONDecodeError:
                    st.warning("Could not parse turn.")
                    continue
            else:
                turn = turn_item

            role = turn.get('role', 'unknown')
            content = turn.get('content', '')
            turn_id = turn.get('id', '')

            # Style based on role
            if role.lower() == 'user':
                st.markdown(
                    f"**� Virtual User ({turn_id}):**"
                )
                st.markdown(f"> {content}")
            else:
                st.markdown(
                    f"**🤖 Agent ({turn_id}):**"
                )
                st.markdown(f"> {content}")

            st.markdown("---")
    else:
        st.info("No conversation turns found.")

    st.markdown("<br>", unsafe_allow_html=True)


def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 GDC Conversational Agent Testing Platform</h1>
        <h5>Interactive persona-based virtual user testing</h5>
    </div>
    """, unsafe_allow_html=True)

    # Check API health
    if not check_api_health():
        st.error(
            "❌ API server is not responding. "
            "Please start it with: `python app/api/run_api.py`"
        )
        st.stop()
    else:
        st.sidebar.success("✅ API server is running")

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page:",
        ["👥 Browse Personas", "🎯 Run Testing Session", "📊 Session Results", "🔬 Session Analysis"]
    )
    
    # Initialize session state
    if 'personas' not in st.session_state:
        st.session_state.personas = []
    if 'selected_persona' not in st.session_state:
        st.session_state.selected_persona = None
    if 'selected_personas' not in st.session_state:
        st.session_state.selected_personas = set()
    if 'session_results' not in st.session_state:
        st.session_state.session_results = None
    if 'sessions_history' not in st.session_state:
        st.session_state.sessions_history = None
    if 'viewed_session' not in st.session_state:
        st.session_state.viewed_session = None
    if 'multi_session_batch_id' not in st.session_state:
        st.session_state.multi_session_batch_id = None
    if 'multi_session_status' not in st.session_state:
        st.session_state.multi_session_status = None
    
    # Page 1: Browse Personas
    if page == "👥 Browse Personas":
        st.header("Available Personas")

        # Load personas on first visit
        if 'personas' not in st.session_state or not st.session_state.personas:
            with st.spinner("Loading personas..."):
                st.session_state.personas = load_personas()
        
        if st.session_state.personas:
            # Use the personas directly since they now include full details
            personas_full = st.session_state.personas

            # --- Filtering Logic ---
            if 'filters' not in st.session_state:
                st.session_state.filters = {}

            # Define the dialog function outside the button click
            # to ensure it's available.
            @st.dialog("Filters")
            def show_filter_dialog():
                """Shows a dialog for filtering personas."""
                st.subheader("Select Filters")

                all_personas = personas_full

                def get_unique_values(key, is_demographic=False):
                    values = set()
                    for p in all_personas:
                        if is_demographic:
                            value = p.get('demographic_info', {}).get(key)
                        else:
                            value = p.get(key)
                        if value:
                            values.add(value)
                    return sorted(list(values))

                # Use a temporary dict for selections to avoid modifying
                # session state directly.
                current_filters = st.session_state.get('filters', {}).copy()

                high_level_ai_view = st.multiselect(
                    "Sentiment on AI",
                    get_unique_values('high_level_AI_view'),
                    default=current_filters.get('high_level_ai_view', []),
                    help="Filter by participant's overall attitude toward AI"
                )
                age_bracket = st.multiselect(
                    "Age Bracket",
                    get_unique_values('age bracket', is_demographic=True),
                    default=current_filters.get('age_bracket', [])
                )
                gender = st.multiselect(
                    "Gender",
                    get_unique_values('gender', is_demographic=True),
                    default=current_filters.get('gender', [])
                )
                religion = st.multiselect(
                    "Religion",
                    get_unique_values('religion', is_demographic=True),
                    default=current_filters.get('religion', [])
                )
                country_of_residence = st.multiselect(
                    "Country",
                    get_unique_values(
                        'self identified country', is_demographic=True
                    ),
                    default=current_filters.get('country_of_residence', [])
                )
                community_type = st.multiselect(
                    "Community Type",
                    get_unique_values('community type', is_demographic=True),
                    default=current_filters.get('community_type', [])
                )
                response_language = st.multiselect(
                    "Language",
                    get_unique_values('response_language'),
                    default=current_filters.get('response_language', [])
                )

                # --- Live Filtering for Preview ---
                temp_filters = {
                    'high_level_ai_view': high_level_ai_view,
                    'age_bracket': age_bracket,
                    'gender': gender,
                    'religion': religion,
                    'country_of_residence': country_of_residence,
                    'community_type': community_type,
                    'response_language': response_language,
                }

                filtered_count = len(all_personas)
                if any(temp_filters.values()):
                    temp_filtered_personas = all_personas
                    for key, values in temp_filters.items():
                        if values:
                            direct_fields = [
                                'response_language', 'high_level_ai_view'
                            ]
                            if key in direct_fields:
                                # Map the filter key to the actual data key
                                if key == 'high_level_ai_view':
                                    temp_filtered_personas = [
                                        p for p in temp_filtered_personas
                                        if p.get('high_level_AI_view') in values
                                    ]
                                else:
                                    temp_filtered_personas = [
                                        p for p in temp_filtered_personas
                                        if p.get(key) in values
                                    ]
                            else:
                                demographic_key_map = {
                                    'age_bracket': 'age bracket',
                                    'gender': 'gender',
                                    'religion': 'religion',
                                    'country_of_residence':
                                        'self identified country',
                                    'community_type': 'community type'
                                }
                                demographic_key = demographic_key_map[key]
                                temp_filtered_personas = [
                                    p for p in temp_filtered_personas
                                    if p.get('demographic_info', {})
                                        .get(demographic_key) in values
                                ]
                    filtered_count = len(temp_filtered_personas)

                st.info(f"Matching personas: **{filtered_count}**")

                c1, c2 = st.columns([1, 1])
                if c1.button(
                    "Apply", use_container_width=True, type="primary"
                ):
                    st.session_state.filters = temp_filters
                    st.rerun()
                if c2.button("Clear Filters", use_container_width=True):
                    st.session_state.filters = {}
                    st.rerun()

            # Now show the buttons after dialog is defined
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(
                    "Browse, filter, and select virtual users for testing."
                )
            with col2:
                if st.button("🔍 Filter Personas", use_container_width=True):
                    show_filter_dialog()
            with col3:
                if st.button("🔄 Refresh Personas", use_container_width=True):
                    st.session_state.personas = load_personas()
                    st.rerun()

            def persona_matches(p):
                for key, selected_values in st.session_state.filters.items():
                    if not selected_values:
                        continue

                    value = None
                    demo_keys = [
                        'age_bracket', 'gender', 'religion', 'community_type'
                    ]
                    if key in demo_keys:
                        value = p.get('demographic_info', {}).get(
                            key.replace('_', ' ')
                        )
                    elif key == 'country_of_residence':
                        value = p.get('demographic_info', {}).get(
                            'self identified country'
                        )
                    elif key in ['response_language', 'high_level_ai_view']:
                        # Map the filter key to the actual data key
                        if key == 'high_level_ai_view':
                            value = p.get('high_level_AI_view')
                        else:
                            value = p.get(key)
                    else:
                        value = p.get(key)

                    if value not in selected_values:
                        return False
                return True

            filtered_personas = [
                p for p in personas_full if persona_matches(p)
            ]

            active_filters_count = sum(
                1 for v in st.session_state.filters.values() if v
            )
            if active_filters_count > 0:
                st.info(
                    f"Showing {len(filtered_personas)} of "
                    f"{len(personas_full)} personas "
                    f"({active_filters_count} filters active)"
                )
            else:
                st.success(f"Showing all {len(filtered_personas)} personas.")

            # --- Persona Grid Display ---
            cols = st.columns(3)

            @st.dialog("Persona Details")
            def show_details_dialog(persona):
                display_pretty_persona(persona)
                if st.button("Close"):
                    st.rerun()

            for i, persona in enumerate(filtered_personas):
                col = cols[i % 3]
                with col:
                    is_selected = st.session_state.selected_persona == persona['id']
                    is_multi_selected = persona['id'] in st.session_state.selected_personas
                    card_class = "persona-card"
                    st.markdown(f"""
                    <div class="{card_class}">
                        <strong>{persona['id']}</strong><br>
                        <span style="background: #2196f3; color: white;
                                     padding: 2px 6px; border-radius: 10px;
                                     font-size: 0.8em;">
                            {persona['response_language']}
                        </span><br>
                        <small>ID: {persona['participant_id']}</small>
                    </div>
                    """, unsafe_allow_html=True)

                    b_cols = st.columns(3)
                    
                    # Single select button
                    button_type = "primary" if is_selected else "secondary"
                    if b_cols[0].button(
                        "Select",
                        key=f"select_{persona['id']}",
                        use_container_width=True,
                        type=button_type
                    ):
                        st.session_state.selected_persona = persona['id']
                        st.rerun()

                    # Multi-select toggle button
                    multi_button_type = "primary" if is_multi_selected else "secondary"
                    multi_button_text = "✓" if is_multi_selected else "+"
                    if b_cols[1].button(
                        multi_button_text,
                        key=f"multi_select_{persona['id']}",
                        use_container_width=True,
                        type=multi_button_type,
                        help="Toggle multi-selection"
                    ):
                        if is_multi_selected:
                            st.session_state.selected_personas.discard(persona['id'])
                        else:
                            st.session_state.selected_personas.add(persona['id'])
                        st.rerun()

                    # Details button
                    if b_cols[2].button(
                        "Details",
                        key=f"details_{persona['id']}",
                        use_container_width=True
                    ):
                        show_details_dialog(persona)
            
            # Show multi-selection summary
            if st.session_state.selected_personas:
                st.info(f"Selected {len(st.session_state.selected_personas)} personas for batch testing: {', '.join(sorted(st.session_state.selected_personas))}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Clear Multi-Selection", use_container_width=True):
                        st.session_state.selected_personas.clear()
                        st.rerun()
                with col2:
                    if st.button("Select All Filtered", use_container_width=True):
                        st.session_state.selected_personas = {p['id'] for p in filtered_personas}
                        st.rerun()
        else:
            st.warning(
                "No personas found. Make sure the database is populated."
            )

    # Page 2: Run Testing Session
    elif page == "🎯 Run Testing Session":
        st.header("Configure Agent Testing Session")

        # Check if any persona is selected
        has_single_selection = st.session_state.selected_persona is not None
        has_multi_selection = len(st.session_state.selected_personas) > 0
        
        if not has_single_selection and not has_multi_selection:
            st.warning(
                "Please select one or more virtual users from the "
                "'Browse Personas' page first."
            )
            st.stop()

        # Session type selection
        session_type = st.radio(
            "Session Type:",
            options=["Single Persona", "Multi-Persona Batch"],
            index=0 if has_single_selection else 1
        )

        if session_type == "Single Persona":
            if not has_single_selection:
                st.warning("Please select a single virtual user first.")
                st.stop()
            
            st.info(
                f"Selected Virtual User: **{st.session_state.selected_persona}**"
            )
            
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
                    max_value=10,
                    value=5,
                    help="Maximum number of conversation turns"
                )
                
                conversations_per_goal = st.slider(
                    "Conversations per Goal",
                    min_value=1,
                    max_value=5,
                    value=1,
                    help="Number of conversations to run for each goal"
                )
            
            with col2:
                st.markdown("### Testing Session Preview")
                st.json({
                    "virtual_user": st.session_state.selected_persona,
                    "num_goals": num_goals,
                    "max_turns": max_turns,
                    "conversations_per_goal": conversations_per_goal,
                    "verbose": True
                })
            
            # Run session button
            if st.button(
                "🚀 Run Single Persona Session",
                type="primary",
                use_container_width=True
            ):
                with st.spinner(
                    "Running agent testing session... This may take a few minutes."
                ):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Simulate progress
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
                    results = run_agent_testing_session(
                        persona_id=st.session_state.selected_persona,
                        num_goals=num_goals,
                        max_turns=max_turns,
                        conversations_per_goal=conversations_per_goal,
                        verbose=True
                    )

                    progress_bar.empty()
                    status_text.empty()

                    if results.get("success"):
                        st.session_state.session_results = results
                        st.success(
                            "Session completed! View results in the "
                            "'Session Results' tab."
                        )
                        st.balloons()
                    else:
                        error_msg = results.get('error', 'Unknown error')
                        st.error(f"Session failed: {error_msg}")

        else:  # Multi-Persona Batch
            if not has_multi_selection:
                st.warning("Please select multiple virtual users first.")
                st.stop()
            
            selected_personas_list = sorted(list(st.session_state.selected_personas))
            st.info(
                f"Selected {len(selected_personas_list)} Virtual Users for Batch Testing"
            )
            
            with st.expander("Selected Personas", expanded=False):
                for persona_id in selected_personas_list:
                    st.write(f"• {persona_id}")
            
            # Session configuration
            col1, col2 = st.columns(2)
            
            with col1:
                num_goals = st.slider(
                    "Number of Goals",
                    min_value=1,
                    max_value=10,
                    value=3,
                    help="Number of goals to generate for each session"
                )
                
                max_turns = st.slider(
                    "Maximum Turns",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="Maximum number of conversation turns"
                )
                
                conversations_per_goal = st.slider(
                    "Conversations per Goal",
                    min_value=1,
                    max_value=5,
                    value=1,
                    help="Number of conversations to run for each goal"
                )
            
            with col2:
                st.markdown("### Batch Testing Preview")
                st.json({
                    "total_personas": len(selected_personas_list),
                    "personas": selected_personas_list[:3] + (["..."] if len(selected_personas_list) > 3 else []),
                    "num_goals": num_goals,
                    "max_turns": max_turns,
                    "conversations_per_goal": conversations_per_goal,
                    "verbose": True
                })
            
            # Run batch session button
            if st.button(
                f"🚀 Run Batch Session ({len(selected_personas_list)} Personas)",
                type="primary",
                use_container_width=True
            ):
                with st.spinner("Starting batch testing session..."):
                    results = run_multi_persona_testing_session(
                        persona_ids=selected_personas_list,
                        num_goals=num_goals,
                        max_turns=max_turns,
                        conversations_per_goal=conversations_per_goal,
                        verbose=True
                    )
                    
                    if results.get("success"):
                        st.session_state.multi_session_batch_id = results.get("batch_id")
                        st.success(
                            f"Batch session started! Batch ID: {results.get('batch_id')}"
                        )
                        st.info(
                            "Sessions are running in the background. "
                            "Check the 'Session Results' tab to monitor progress."
                        )
                        st.balloons()
                    else:
                        error_msg = results.get('error', 'Unknown error')
                        st.error(f"Failed to start batch session: {error_msg}")

        # Display active batch status if available
        if st.session_state.multi_session_batch_id:
            st.markdown("---")
            st.subheader("Active Batch Status")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"Batch ID: `{st.session_state.multi_session_batch_id}`")
            with col2:
                if st.button("🔄 Refresh Status", use_container_width=True):
                    st.rerun()
            
            # Get and display current status
            batch_status = get_batch_status(st.session_state.multi_session_batch_id)
            if batch_status.get("success"):
                display_batch_status(batch_status)
                
                # Check if batch is complete
                if batch_status.get("overall_status") in ["completed", "failed", "partially_completed"]:
                    if st.button("Clear Batch Status", use_container_width=True):
                        st.session_state.multi_session_batch_id = None
                        st.rerun()
            else:
                st.error(f"Error getting batch status: {batch_status.get('error', 'Unknown error')}")
                if st.button("Clear Invalid Batch", use_container_width=True):
                    st.session_state.multi_session_batch_id = None
                    st.rerun()

    # Page 3: Session Results
    elif page == "📊 Session Results":
        st.header("Session Results")

        # Display historical sessions
        st.subheader("Session History")
        if st.button("🔄 Refresh History"):
            st.session_state.sessions_history = load_sessions()
            st.session_state.viewed_session = None
            st.rerun()

        if st.session_state.sessions_history is None:
            with st.spinner("Loading session history..."):
                st.session_state.sessions_history = load_sessions()

        sessions = st.session_state.sessions_history
        if sessions:
            df = pd.DataFrame(sessions)
            df_display = df[['id', 'persona_id', 'created_at']].copy()
            df_display['created_at'] = pd.to_datetime(
                df_display['created_at']
            ).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Make the dataframe clickable
            event = st.dataframe(
                df_display,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row"
            )

            # Handle row selection
            if event.selection and event.selection.rows:
                selected_row_idx = event.selection.rows[0]
                selected_session = sessions[selected_row_idx]
                st.session_state.viewed_session = selected_session

        else:
            st.info("No historical sessions found.")

        # Display details of the viewed session
        if st.session_state.viewed_session:
            st.markdown("---")
            session_id = st.session_state.viewed_session['id']
            
            # Header with export button
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"Details for Session: `{session_id}`")
            with col2:
                # Export session button
                session_json = json.dumps(
                    st.session_state.viewed_session, indent=2
                )
                st.download_button(
                    label="📥 Export Session",
                    data=session_json,
                    file_name=f"session_{session_id}.json",
                    mime="application/json",
                    use_container_width=True,
                    help="Download session details as JSON"
                )
            
            display_conversation_results(st.session_state.viewed_session)
    elif page == "🔬 Session Analysis":
        st.header("Session Analysis")
        st.info(
            "Examine how different demographic factors influence the types of conversations!. "
        )
        st.subheader("Session History")
        if st.button("🔄 Refresh History"):
            st.session_state.sessions_history = load_sessions()
            st.session_state.viewed_session = None
            st.rerun()

        if st.session_state.sessions_history is None:
            with st.spinner("Loading session history..."):
                st.session_state.sessions_history = load_sessions()

        sessions = st.session_state.sessions_history
        if sessions:
            # Now need to load personas to display demographic info
            df = pd.DataFrame(sessions)
            if 'personas' not in st.session_state or not st.session_state.personas:
                with st.spinner("Loading personas..."):
                    st.session_state.personas = load_personas()
            
            if st.session_state.personas:
                # Use the personas directly since they now include full details
                personas_full = st.session_state.personas

            else:
                personas_full = st.session_state.get('personas_full', [])
            personas_df = pd.DataFrame(personas_full)
            if 'demographic_info' in personas_df.columns:
                # Flatten the 'demographic_info' column into separate columns
                demographic_df = pd.json_normalize(personas_df['demographic_info'])

                # Merge the normalized demographic data back into the personas DataFrame
                personas_df = pd.concat([personas_df, demographic_df], axis=1)

                # Display the updated DataFrame
                # st.write(personas_df)

            merged_df = pd.merge(df, personas_df, left_on='persona_id', right_on='id', how='left')

            # Step 2: Allow user to select demographic attributes for pivoting
            st.subheader("Demographic Analysis")
            demographic_key_map2 = {
                                'Age Range': 'age bracket',
                                'Gender': 'gender',
                                'Religion': 'religion',
                                'Country of Residence':'self identified country',
                                'Community Type': 'community type', 
                                'Langauge' : 'response_language',
                                'View of AI' : 'high_level_AI_view',
                                }
            options = [None] + list(demographic_key_map2.keys())
            attribute_selected = st.selectbox("Select Demographic Attribute", options=options)

            text_to_analysze = st.selectbox("Select Type of Text", options = [None, 'goals', 'conversations'])
            
            if attribute_selected and text_to_analysze:
                # Map the selected attribute to the actual column name
                attribute = demographic_key_map2.get(attribute_selected, attribute_selected)
                unique_values = merged_df[attribute].dropna().unique()
                unique_values = sorted(unique_values)


                output_goals = {}
                output_all_text = {}
                output_all = {}

                # Generate and display a word cloud for each unique value
                for value in unique_values:
                    
                    # Filter data for the current value
                    filtered_data = merged_df[merged_df[attribute] == value]
                    
                    # Combine text data for the word cloud
                    # text_data = " ".join(filtered_data['persona_id'].dropna().astype(str))  # Replace 'persona_id' with relevant text column
                    
                    text_data = ""
                    goal_text = ""
                    for session_filtered in filtered_data['session_data'].dropna():
                        for goal_name, goal_info in session_filtered.items():
                            for conversations in goal_info:
                                goal = conversations.get('goal', '')
                                all_turns = conversations.get('turns', [])
                                my_str = "\n".join([f"{x['role']} : {x['content']}" for x in all_turns])
                                text_data += f"Goal: {goal}\n{my_str}\n\n"
                            goal_text += f"{goal} \n\n"
                    output_all_text[value] = text_data
                    output_goals[value] = goal_text

                document_list = []

                if text_to_analysze == 'goals':
                    document_list = list(output_goals.values())
                elif text_to_analysze == 'conversations':
                    document_list = list(output_all_text.values())

                vectorizer = TfidfVectorizer(stop_words='english')
                tfidf_matrix = vectorizer.fit_transform(document_list)
                feature_names = vectorizer.get_feature_names_out()


                def generate_wordcloud_for_document(doc_index):
                    # Get the TF-IDF vector for this document
                    tfidf_vector = tfidf_matrix[doc_index]
                    word_scores = {
                        feature_names[i]: tfidf_vector[0, i]
                        for i in tfidf_vector.nonzero()[1]
                    }
                        
                        # Generate word cloud from TF-IDF scores
                    wordcloud = WordCloud(width=800, height=400, background_color='white')
                    wordcloud.generate_from_frequencies(word_scores)
                    return(wordcloud)

                fig, ax = plt.subplots(figsize=(10, 5))
                for i, value in enumerate(unique_values):
                    st.markdown(f"### {attribute_selected}: {value}")
                    wordcloud = generate_wordcloud_for_document(i)
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')  # Remove axes for better visualization
                    # ax.set_title(f"{attribute_selected.capitalize()}: {value}", fontsize=16)
                    st.pyplot(fig)


    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888;'>"
        "Virtual User Testing Platform | Built with Streamlit"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
