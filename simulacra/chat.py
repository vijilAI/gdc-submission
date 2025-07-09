import streamlit as st
import json
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import re

# Add the project root directory to sys.path if needed
sys.path.append(os.path.dirname(os.getcwd()))

# Import the necessary modules from simulacra
try:
    from simulacra.agent_v2 import ConversationAgent, RedTeamerAgent, RedTeamingSession
    from simulacra.types import RedTeamerPersona, Conversation
except ImportError:
    st.error("Failed to import simulacra modules. Make sure you're running this from the correct directory.")
    st.stop()

# Initialize session state variables if they don't exist
if 'persona' not in st.session_state:
    st.session_state.persona = None
if 'sut_agent' not in st.session_state:
    st.session_state.sut_agent = None
if 'redteamer_agent' not in st.session_state:
    st.session_state.redteamer_agent = None
if 'session' not in st.session_state:
    st.session_state.session = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_conversation' not in st.session_state:
    st.session_state.current_conversation = None
if 'conversation_output' not in st.session_state:
    st.session_state.conversation_output = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
# Add new session state variables to preserve selections
if 'selected_goal_type' not in st.session_state:
    st.session_state.selected_goal_type = None
if 'selected_goal' not in st.session_state:
    st.session_state.selected_goal = None
if 'max_turns' not in st.session_state:
    st.session_state.max_turns = 5

def load_personas():
    """Load all personas from the personas directory"""
    personas_dir = Path("personas")
    personas = []
    
    if personas_dir.exists() and personas_dir.is_dir():
        for file_path in personas_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    personas.append({
                        "id": data.get("id", "unknown"),
                        "name": data.get("name", file_path.stem),
                        "file_path": str(file_path)
                    })
            except Exception as e:
                st.error(f"Error loading persona from {file_path}: {str(e)}")
    
    return personas

def format_persona_details(persona):
    """Format persona details for display in a simplified way"""
    if not persona:
        return ""
        
    # Demographics section
    demographics = "**Demographics**\n\n"
    for k, v in persona.demographic_attributes.items():
        # Prettify keys: remove underscores, title case
        pretty_key = k.replace('_', ' ').title()
        demographics += f"- **{pretty_key}**: {v}\n"
    
    # Expertise section
    expertise = "\n**Expertise**\n\n"
    for k, v in persona.expertise.items():
        # Prettify keys: remove underscores, title case
        pretty_key = k.replace('_', ' ').title()
        if isinstance(v, list):
            expertise += f"- **{pretty_key}**: {', '.join(v)}\n"
        else:
            expertise += f"- **{pretty_key}**: {v}\n"
    
    # Background narrative section
    background = f"\n**Background**\n\n{persona.background_narrative}\n"
    
    # Definition of trust section
    trust_def = f"\n**Definition of Trust**\n\n{persona.definition_of_trust}\n"
    
    # Testing style section (moved to end)
    testing_style = "\n**Testing Style**\n\n"
    for k, v in persona.testing_style.items():
        # Prettify keys: remove underscores, title case
        pretty_key = k.replace('_', ' ').title()
        if isinstance(v, list):
            testing_style += f"- **{pretty_key}**: {', '.join(v)}\n"
        else:
            testing_style += f"- **{pretty_key}**: {v}\n"
    
    # Combine all sections - personality_traits section removed
    combined_details = demographics + expertise + background + trust_def + testing_style
    
    return combined_details

def init_agents():
    """Initialize the system under test agent"""
    try:
        # Initialize the SUT agent (assuming a default config path)
        st.session_state.sut_agent = ConversationAgent(config_path="configs/nora.yaml")
        return True
    except Exception as e:
        st.error(f"Error initializing agents: {str(e)}")
        return False

def init_red_teamer(persona_path):
    """Initialize the red teamer agent with the selected persona"""
    try:
        # Load the persona
        persona = RedTeamerPersona.from_json(persona_path)
        st.session_state.persona = persona
        
        # Initialize the red teamer agent
        st.session_state.redteamer_agent = RedTeamerAgent(persona_path=persona_path)
        
        # Initialize the red teaming session
        st.session_state.session = RedTeamingSession(
            sut_agent=st.session_state.sut_agent,
            redteamer_agent=st.session_state.redteamer_agent
        )
        
        # Reset goal selections when a new persona is loaded
        # but don't reset conversation output or history
        st.session_state.selected_goal_type = None
        st.session_state.selected_goal = None
        
        # Clear the current conversation when changing personas
        st.session_state.current_conversation = None
        
        return True
    except Exception as e:
        st.error(f"Error initializing red teamer: {str(e)}")
        return False

def is_xml_code_block(text: str) -> tuple[bool, str]:
    """
    Check if the text is enclosed in ```xml ``` code blocks and extract the content
    """
    xml_pattern = re.compile(r'```xml\s*([\s\S]*?)\s*```', re.MULTILINE)
    match = xml_pattern.search(text)
    
    if match:
        xml_content = match.group(1)
        return True, xml_content
    
    return False, ""

def is_html(text: str) -> bool:
    """
    Check if the text contains HTML/XML tags
    """
    # More comprehensive pattern to detect HTML/XML tags
    html_pattern = re.compile(r'<(?:!DOCTYPE|html|body|head|div|p|span|h\d|ul|ol|li|table|tr|td|th|a|img|br|hr|input|form|button|script|style|link|meta)[^>]*>|<\/[a-z][a-z0-9]*>', re.IGNORECASE)
    return bool(html_pattern.search(text))

def process_html_headings(html_content: str) -> str:
    """
    Process HTML headings to render them as bold text
    """
    # Replace heading tags with bold text
    heading_pattern = re.compile(r'<h[1-6][^>]*>(.*?)<\/h[1-6]>', re.IGNORECASE | re.DOTALL)
    
    def replace_heading(match):
        heading_text = match.group(1)
        # Remove any nested tags inside the heading
        heading_text = re.sub(r'<[^>]*>', '', heading_text)
        return f"<strong>{heading_text}</strong>"
    
    return heading_pattern.sub(replace_heading, html_content)

# Replace the existing detect_xml_code_block function with the new implementation
def detect_xml_code_block(text):
    """Detect if the text contains an XML code block and process it if found"""
    # First check if it's an XML code block
    is_xml, xml_content = is_xml_code_block(text)
    
    if is_xml:
        # Process the XML content
        processed_content = process_html_headings(xml_content)
        return True, processed_content
    elif is_html(text):
        # Process headings to bold text for regular HTML
        processed_content = process_html_headings(text)
        return True, processed_content
    
    return False, text

async def run_conversation_with_output(goal, goal_type, max_turns=5):
    """Run a conversation and capture the output"""
    # Set running state
    st.session_state.is_running = True
    
    # Create a placeholder for displaying the current conversation
    conversation_placeholder = st.empty()
    status_placeholder = st.empty()
    
    try:
        # Initialize conversation
        conversation_id = f"{st.session_state.sut_agent.id}_vs_{st.session_state.redteamer_agent.persona.id}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        conversation = Conversation(id=conversation_id, goal=goal, goal_type=goal_type, turns=[])
        st.session_state.current_conversation = conversation
        
        # Display initial conversation status
        status_placeholder.info(f"Starting conversation... Goal: {goal}")
        
        messages = [{"role": "assistant", "content": ""}]  # Start with an empty assistant message
        
        # Run the conversation for the specified number of turns
        for turn in range(max_turns):
            # Update status
            status_placeholder.info(f"Turn {turn+1}/{max_turns} - Red teamer is generating a response...")
            
            # First turn starts with the red teamer agent
            redteamer_response = await st.session_state.redteamer_agent.chat_completions(
                messages=messages,
                sys_prompt=f"{st.session_state.redteamer_agent.sys_prompt}{goal}"
            )
            
            # Process the red teamer response
            redteamer_message = redteamer_response.generations[0].content
            conversation.add_turn(
                id=st.session_state.redteamer_agent.persona.id,
                role="user",
                content=redteamer_message
            )
            messages.append({"role": "user", "content": redteamer_message})
            
            # Update the current conversation display
            display_conversation(conversation_placeholder, conversation)
            
            # Check if the red teamer has identified untrustworthy behavior
            try:
                json_match = re.search(r'({[\s\S]*"goal_achieved"[\s\S]*})', redteamer_message)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    if result.get("goal_achieved") == True:
                        status_placeholder.success("Goal achieved! Ending conversation.")
                        # Store the conversation and return early to stop the conversation
                        if hasattr(st.session_state.session, 'conversation_history'):
                            st.session_state.session.conversation_history.append(conversation)
                        st.session_state.conversation_history.append(conversation)
                        return
            except Exception as e:
                status_placeholder.warning(f"Error parsing goal achievement: {str(e)}")
            
            # Update status
            status_placeholder.info(f"Turn {turn+1}/{max_turns} - System is generating a response...")
            
            # Get response from the SUT agent
            sut_response = await st.session_state.sut_agent.chat_completions(messages)
            
            sut_message = sut_response.generations[0].content
            
            # Check if the SUT response contains XML code blocks and process if needed
            # This is only for display purposes, the original message is still stored in the conversation
            is_xml, processed_message = detect_xml_code_block(sut_message)
            
            conversation.add_turn(
                id=st.session_state.sut_agent.id,
                role="assistant",
                content=sut_message  # Store the original message
            )
            messages.append({"role": "assistant", "content": sut_message})
            
            # Update the current conversation display
            display_conversation(conversation_placeholder, conversation)
        
        # Add a final redteamer assessment of the last SUT response only if the last turn was from the assistant
        if conversation.turns and conversation.turns[-1].role == "assistant":
            status_placeholder.info("Getting final assessment from red teamer...")
            
            final_redteamer_response = await st.session_state.redteamer_agent.chat_completions(messages)
            
            final_redteamer_message = final_redteamer_response.generations[0].content
            conversation.add_turn(
                id=st.session_state.redteamer_agent.persona.id,
                role="user",
                content=final_redteamer_message
            )
            
            # Update the current conversation display one last time
            display_conversation(conversation_placeholder, conversation)
            
            # Check if the final assessment indicates goal achievement
            try:
                json_match = re.search(r'({[\s\S]*"goal_achieved"[\s\S]*})', final_redteamer_message)
                if json_match:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    if result.get("goal_achieved") == True:
                        status_placeholder.success("Goal achieved in final assessment!")
            except Exception as e:
                status_placeholder.warning(f"Error parsing final goal achievement: {str(e)}")
        
        # Store the conversation
        if hasattr(st.session_state.session, 'conversation_history'):
            st.session_state.session.conversation_history.append(conversation)
        st.session_state.conversation_history.append(conversation)
        
        status_placeholder.success("Conversation completed! Conversation saved in session history!")
        
    except Exception as e:
        status_placeholder.error(f"Error during conversation: {str(e)}")
    
    finally:
        # Reset running state
        st.session_state.is_running = False

def display_conversation(placeholder, conversation):
    """Display the conversation in a formatted way"""
    with placeholder.container():
        for turn in conversation.turns:
            if turn.role == "user":
                st.markdown(f"**{turn.id}**")
                st.markdown(f"<div style='background-color:#f0f2f6; padding:10px; border-radius:5px; border-left:4px solid #6c757d; margin-bottom:10px;'>{turn.content}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{turn.id}**")
                
                # Check if the assistant's response contains XML code blocks or HTML
                is_xml_or_html, processed_content = detect_xml_code_block(turn.content)
                
                # Display the content with appropriate styling
                st.markdown(f"<div style='background-color:#e8f4f8; padding:10px; border-radius:5px; border-left:4px solid #17a2b8; margin-bottom:10px;'>{processed_content}</div>", unsafe_allow_html=True)
            
def save_conversation_history():
    """Save the conversation history to a file"""
    try:
        if not st.session_state.conversation_history:
            st.warning("No conversations to save.")
            return False
        
        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"redteaming_session_{timestamp}.jsonl"
        
        # Convert conversations to dictionaries and save as JSONL
        with open(filename, 'w') as f:
            for conv in st.session_state.conversation_history:
                from dataclasses import asdict
                f.write(json.dumps(asdict(conv)) + '\n')
        
        return filename
    except Exception as e:
        st.error(f"Error saving conversation history: {str(e)}")
        return False

def main():
    st.set_page_config(page_title="Simulacra Chat", layout="wide")
    
    st.title("Simulacra Chat")
    st.markdown("Load a persona, view their details, and run red teaming sessions with it.")
    
    # Initialize the SUT agent if not already done
    if not st.session_state.sut_agent:
        with st.spinner("Initializing system under test agent..."):
            init_agents()
    
    # Create a two-column layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("Personas")
        
        # Load and display personas
        personas = load_personas()
        
        if not personas:
            st.warning("No personas found in the 'personas' directory.")
        else:
            # Create a selectbox for persona selection
            persona_options = {f"{p['name']} ({p['id']})": p['file_path'] for p in personas}
            
            # Get previously selected persona if any
            previous_selection = None
            if st.session_state.persona:
                for display_name, path in persona_options.items():
                    if path == getattr(st.session_state.persona, "_file_path", None):
                        previous_selection = display_name
                        break
            
            # Create selectbox with auto-loading
            selected_persona = st.selectbox(
                "Select a persona",
                list(persona_options.keys()),
                index=list(persona_options.keys()).index(previous_selection) if previous_selection else 0
            )
            
            # Auto-load the selected persona if it's different from the current one
            selected_path = persona_options[selected_persona]
            current_path = getattr(st.session_state.persona, "_file_path", None)
            
            if selected_path != current_path:
                with st.spinner(f"Loading persona: {selected_persona}"):
                    if init_red_teamer(selected_path):
                        # st.success(f"Loaded persona: {selected_persona}")
                        # Store the file path for future comparison
                        st.session_state.persona._file_path = selected_path
                    else:
                        st.error("Failed to load persona.")
        
        # Display persona details if loaded (simplified format)
        if st.session_state.persona:
            # st.header("Persona Details")
            
            # Use the new simplified format (no expandable sections)
            persona_details = format_persona_details(st.session_state.persona)
            st.markdown(persona_details)
    
    with col2:
        # Create a row with the header and save button side by side
        header_col, save_button_col = st.columns([4, 1])
        
        with header_col:
            st.header("Red Teaming Conversation")
            
        # Move Save History button next to the header
        with save_button_col:
            st.write("")  # Add some spacing to align with header
            if st.session_state.conversation_history:
                if st.button("💾 Save History", use_container_width=True, help="Save all conversations to a JSONL file"):
                    filename = save_conversation_history()
                    if filename:
                        st.success(f"Saved to {filename}")
        
        # Display the current persona if loaded
        if st.session_state.persona:
            st.markdown(f"##### Persona: {st.session_state.persona.name}")
            
            # Create a box with two columns for controls and buttons
            controls_container = st.container()
            with controls_container:
                # Use the container's full width but place elements inside it
                controls_col, buttons_col = st.columns([3, 2])
                
                with controls_col:
                    # Goal selection controls
                    if hasattr(st.session_state.persona, "goals") and st.session_state.persona.goals:
                        goal_type_options = list(st.session_state.persona.goals.keys())
                        
                        # Reorder goal types to put "bad_faith" first
                        if "bad_faith" in goal_type_options:
                            goal_type_options.remove("bad_faith")
                            goal_type_options.insert(0, "bad_faith")
                        
                        # Goal type selection
                        selected_goal_type = st.selectbox(
                            "Select goal type", 
                            goal_type_options,
                            key="goal_type_selectbox"
                        )
                        
                        # Update the session state
                        st.session_state.selected_goal_type = selected_goal_type
                        
                        if selected_goal_type:
                            # Goal selection
                            goal_options = st.session_state.persona.goals[selected_goal_type]
                            selected_goal = st.selectbox(
                                "Select goal", 
                                goal_options,
                                key="goal_selectbox"
                            )
                            
                            # Update the session state
                            st.session_state.selected_goal = selected_goal
                            
                            # Max turns slider
                            max_turns = st.slider(
                                "Maximum conversation turns", 
                                1, 10, 
                                st.session_state.max_turns,
                                key="max_turns_slider"
                            )
                            
                            # Update the session state
                            st.session_state.max_turns = max_turns
                
                with buttons_col:
                    # Add some vertical spacing to align with the controls
                    st.write("")
                    st.write("")
                    
                    # Execute button for red teaming
                    if not st.session_state.is_running and st.session_state.selected_goal:
                        if st.button("Execute Red Teaming", use_container_width=True):
                            # Set flag to indicate we want to start a new conversation
                            st.session_state.start_new_conversation = True
                            st.rerun()
                        
            # Current Conversation section - always show this section
            st.subheader("Current Conversation")
            
            # Check if we should start a new conversation
            if st.session_state.get('start_new_conversation', False) and not st.session_state.is_running:
                # Reset the flag
                st.session_state.start_new_conversation = False
                # Run the conversation within the Current Conversation section
                asyncio.run(run_conversation_with_output(
                    st.session_state.selected_goal, 
                    st.session_state.selected_goal_type, 
                    st.session_state.max_turns
                ))
            elif not st.session_state.is_running and st.session_state.current_conversation:
                # Display the existing conversation
                display_conversation(st.empty(), st.session_state.current_conversation)
            else:
                # Show a message when no conversation is available
                st.info("Select a goal and click 'Execute Red Teaming' to start a conversation.")
        else:
            st.info("Please load a persona to start a red teaming session.")

# Initialize additional session state for controlling conversation execution
if 'start_new_conversation' not in st.session_state:
    st.session_state.start_new_conversation = False

if __name__ == "__main__":
    # Make sure dotenv is loaded if needed
    try:
        from dotenv import load_dotenv
        load_dotenv("../.env")
    except ImportError:
        st.warning("dotenv not installed. Environment variables may not be loaded properly.")
    
    main()
