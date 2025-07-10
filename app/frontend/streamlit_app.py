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
    """Fetch full details for a single persona."""
    try:
        response = requests.get(f"{API_BASE}/personas/{persona_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(
                f"Failed to get details for persona {persona_id}: "
                f"HTTP {response.status_code}"
            )
            return {}
    except requests.exceptions.RequestException as e:
        st.error(f"API connection error: {e}")
        return {}


def run_red_teaming_session(
    persona_id: str, num_goals: int, max_turns: int, verbose: bool
) -> Dict[str, Any]:
    """Run a red teaming session via the API."""
    payload = {
        "persona_fname": persona_id,
        "num_goals": num_goals,
        "max_turns": max_turns,
        "verbose": verbose,
    }
    try:
        response = requests.post(
            f"{API_BASE}/run-red-teaming-session", json=payload
        )
        if response.status_code == 200:
            return {"success": True, **response.json()}
        else:
            error_detail = response.json().get('detail', 'Unknown error')
            return {"success": False, "error": error_detail}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


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
                conversations = session_data[goal_type]

                if isinstance(conversations, list) and conversations:
                    for j, conversation_item in enumerate(conversations):
                        st.subheader(f"Conversation {j + 1}")

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

                        # Display goal
                        goal = conversation.get('goal')
                        if goal:
                            st.info(f"**Goal:** {goal}")

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
                                        f"**🔴 Red Teamer ({turn_id}):**"
                                    )
                                    st.markdown(f"> {content}")
                                else:
                                    st.markdown(
                                        f"**🤖 Assistant ({turn_id}):**"
                                    )
                                    st.markdown(f"> {content}")

                                st.markdown("---")

                        st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.info(f"No conversations found for {goal_type}")
    else:
        st.info("No session data available to display.")


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
        ["👥 Browse Personas", "🎯 Run Session", "📊 Session Results"]
    )
    
    # Initialize session state
    if 'personas' not in st.session_state:
        st.session_state.personas = []
    if 'selected_persona' not in st.session_state:
        st.session_state.selected_persona = None
    if 'session_results' not in st.session_state:
        st.session_state.session_results = None
    if 'sessions_history' not in st.session_state:
        st.session_state.sessions_history = None
    if 'viewed_session' not in st.session_state:
        st.session_state.viewed_session = None
    
    # Page 1: Browse Personas
    if page == "👥 Browse Personas":
        st.header("Available Personas")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(
                "Browse, filter, and select personas for red teaming sessions."
            )
        with col2:
            if st.button("🔄 Refresh Personas", use_container_width=True):
                st.session_state.personas = load_personas()
                # Clear detailed cache on refresh
                if 'personas_full' in st.session_state:
                    del st.session_state['personas_full']
        
        # Load personas on first visit
        if 'personas' not in st.session_state or not st.session_state.personas:
            with st.spinner("Loading personas..."):
                st.session_state.personas = load_personas()
        
        if st.session_state.personas:
            # Fetch full details for filtering if not already cached
            if 'personas_full' not in st.session_state:
                with st.spinner("Fetching details for all personas..."):
                    personas_full = [
                        get_persona_details(p['id'])
                        for p in st.session_state.personas if p
                    ]
                    st.session_state.personas_full = [
                        p for p in personas_full if p
                    ]

            personas_full = st.session_state.get('personas_full', [])

            # --- Filtering Logic ---
            if 'filters' not in st.session_state:
                st.session_state.filters = {}

            # Define the dialog function outside the button click
            # to ensure it's available.
            @st.dialog("Filter by Demographics")
            def show_filter_dialog():
                """Shows a dialog for filtering personas."""
                st.subheader("Apply Demographic Filters")

                all_personas = st.session_state.get('personas_full', [])

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
                            if key == 'response_language':
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

            if st.button("🔍 Filter Personas", use_container_width=True):
                show_filter_dialog()

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
                    card_class = (
                        "selected-persona"
                        if st.session_state.selected_persona == persona['id']
                        else "persona-card"
                    )
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

                    b_cols = st.columns(2)
                    if b_cols[0].button(
                        "Select",
                        key=f"select_{persona['id']}",
                        use_container_width=True
                    ):
                        st.session_state.selected_persona = persona['id']
                        st.success(f"Selected: {persona['id']}")

                    if b_cols[1].button(
                        "Details",
                        key=f"details_{persona['id']}",
                        use_container_width=True
                    ):
                        show_details_dialog(persona)
        else:
            st.warning(
                "No personas found. Make sure the database is populated."
            )

    # Page 2: Run Session
    elif page == "🎯 Run Session":
        st.header("Configure Red Teaming Session")

        # Check if persona is selected
        if not st.session_state.selected_persona:
            st.warning(
                "Please select a persona from the "
                "'Browse Personas' page first."
            )
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
                max_value=10,
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
        if st.button(
            "🚀 Run Red Teaming Session",
            type="primary",
            use_container_width=True
        ):
            with st.spinner(
                "Running red teaming session... This may take a few minutes."
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
                    st.success(
                        "Session completed! View results in the "
                        "'Session Results' tab."
                    )
                    st.balloons()
                else:
                    error_msg = results.get('error', 'Unknown error')
                    st.error(f"Session failed: {error_msg}")

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
                session_json = json.dumps(st.session_state.viewed_session, indent=2)
                st.download_button(
                    label="📥 Export Session",
                    data=session_json,
                    file_name=f"session_{session_id}.json",
                    mime="application/json",
                    use_container_width=True,
                    help="Download session details as JSON"
                )
            
            display_conversation_results(st.session_state.viewed_session)

    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #888;'>"
        "GDC Persona Red Teaming Platform | Built with Streamlit"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
