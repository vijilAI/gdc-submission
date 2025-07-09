import streamlit as st
import pandas as pd
import json
import re
from typing import List, Dict, Any
from dataclasses import dataclass

# Try to import the classes, if it fails define them locally
try:
    from simulacra.types import Conversation, ConversationTurn
except ImportError:
    try:
        from .types import Conversation, ConversationTurn
    except ImportError:
        # Define the classes directly in this file as a fallback
        @dataclass
        class ConversationTurn:
            id: str
            role: str
            content: str

        @dataclass
        class Conversation:
            id: str
            goal: str
            turns: List[ConversationTurn]
            goal_type: str = ""
            
            def add_turn(self, role: str, id: str, content: str):
                """Add a new turn to the conversation."""
                self.turns.append(ConversationTurn(role=role, id=id, content=content))

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    Load conversations from a JSONL file
    """
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data

def convert_to_conversation_objects(raw_data: List[Dict[str, Any]]) -> List[Conversation]:
    """
    Convert raw JSON data to Conversation objects
    """
    conversations = []
    for item in raw_data:
        turns = []
        for turn_data in item.get('turns', []):
            turns.append(ConversationTurn(
                id=turn_data.get('id', ''),
                role=turn_data.get('role', ''),
                content=turn_data.get('content', '')
            ))
        
        conversation = Conversation(
            id=item.get('id', ''),
            goal=item.get('goal', ''),
            goal_type=item.get('goal_type', ''),
            turns=turns
        )
        conversations.append(conversation)
    return conversations

def extract_goal_achievement(conversation: Conversation) -> bool:
    """
    Extract whether the goal was achieved from the conversation
    """
    # Look for JSON with goal_achieved in the last user turn
    for turn in reversed(conversation.turns):
        if turn.role == "user":
            json_match = re.search(r'({[\s\S]*"goal_achieved"[\s\S]*})', turn.content)
            if json_match:
                try:
                    json_str = json_match.group(1)
                    result = json.loads(json_str)
                    return result.get("goal_achieved", False)
                except:
                    pass
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

def contains_json(text: str) -> tuple[bool, dict]:
    """
    Check if the text contains a valid JSON object and extract it
    """
    # Look for JSON-like patterns
    json_pattern = re.compile(r'({[\s\S]*})')
    match = json_pattern.search(text)
    
    if match:
        json_str = match.group(1)
        try:
            # Try to parse as JSON
            json_data = json.loads(json_str)
            return True, json_data
        except json.JSONDecodeError:
            pass
    
    return False, {}

def create_conversation_df(conversations: List[Conversation]) -> pd.DataFrame:
    """
    Create a DataFrame with conversation metadata
    """
    data = []
    for conv in conversations:
        user_turns = sum(1 for turn in conv.turns if turn.role == "user")
        assistant_turns = sum(1 for turn in conv.turns if turn.role == "assistant")
        goal_achieved = extract_goal_achievement(conv)
        
        data.append({
            "id": conv.id,
            "goal": conv.goal,
            "goal_type": conv.goal_type,
            "total_turns": len(conv.turns),
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "goal_achieved": goal_achieved
        })
    
    return pd.DataFrame(data)

def main():
    st.set_page_config(page_title="Conversation History Dashboard", layout="wide")
    
    st.title("Simulacra Dashboard")
    
    # File uploader for JSONL files
    uploaded_file = st.file_uploader("Upload Conversation History (JSONL)", type=["jsonl"])
    
    if uploaded_file is not None:
        # Save the file temporarily
        temp_path = f"/tmp/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Load data
        try:
            raw_data = load_jsonl(temp_path)
            conversations = convert_to_conversation_objects(raw_data)
            
            if not conversations:
                st.error("No conversations found in the file.")
                return
            
            # Create DataFrame for analysis
            conv_df = create_conversation_df(conversations)
            
            # Dashboard layout - updated column ratio to make left panel half the width of the right panel
            col_left, col_right = st.columns([1, 2])
            
            with col_left:
                # Overview section
                st.subheader("Conversation Overview")
                
                # Goal type filter without the "Filters" header
                all_goal_types = sorted(conv_df['goal_type'].unique().tolist())
                # Reorder goal types to put "bad_faith" first if it exists
                if "bad_faith" in all_goal_types:
                    all_goal_types.remove("bad_faith")
                    all_goal_types.insert(0, "bad_faith")
                goal_types = ["All"] + all_goal_types
                selected_goal_type = st.selectbox("Filter by Goal Type", goal_types)
                
                # Filter data based on goal type selection
                goal_filtered_df = conv_df
                if selected_goal_type != "All":
                    goal_filtered_df = conv_df[conv_df['goal_type'] == selected_goal_type]
                
                # Replace metrics with a bulleted list for summary stats
                total_convs = len(goal_filtered_df)
                goal_achieved_count = goal_filtered_df['goal_achieved'].sum()
                achievement_percentage = (goal_achieved_count/total_convs)*100 if total_convs > 0 else 0
                avg_turns = goal_filtered_df['total_turns'].mean() if total_convs > 0 else 0
                
                st.markdown(
                    f"""
                    <ul style='font-size: 18px;'>
                        <li><strong>Total Conversations:</strong> {total_convs}</li>
                        <li><strong>Goals Achieved:</strong> {goal_achieved_count} ({achievement_percentage:.1f}%)</li>
                        <li><strong>Average Turns:</strong> {avg_turns:.1f}</li>
                    </ul>
                    """,
                    unsafe_allow_html=True
                )
                
                # Conversation list section
                st.subheader("Conversations")
                
                # Move goal achievement filter here
                achievement_options = ["All", "Yes", "No"]
                selected_achievement = st.selectbox("Filter by Goal Achievement", achievement_options)
                
                # Apply both filters for the conversation list
                filtered_df = goal_filtered_df
                if selected_achievement != "All":
                    goal_achieved = True if selected_achievement == "Yes" else False
                    filtered_df = filtered_df[filtered_df['goal_achieved'] == goal_achieved]
                
                # Create a container for scrollable list
                conversation_list = st.container()
                
                with conversation_list:
                    for idx, row in filtered_df.iterrows():
                        # Change color for success from green to light purple
                        success_color = "#E6E6FA" if row['goal_achieved'] else "#FADBD8"  # Light purple if achieved, light red if not
                        display_name = f"Conversation {idx+1}"
                        
                        # Create a clickable item for each conversation
                        if st.button(
                            f"{display_name}",
                            key=f"conv_{row['id']}",
                            help=f"Goal: {row['goal']}\nGoal Type: {row['goal_type']}\nAchieved: {'Yes' if row['goal_achieved'] else 'No'}",
                            use_container_width=True,
                            type="primary" if row['goal_achieved'] else "secondary"
                        ):
                            # Store the selected conversation ID in session state
                            st.session_state.selected_conv_id = row['id']
                    
                    # Add some spacing
                    st.write("")

            with col_right:
                # Conversation details view
                st.subheader("Conversation Details")
                
                # Check if we have a selected conversation in session state
                selected_conv_id = st.session_state.get('selected_conv_id', None)
                
                # If not, select the first conversation in the filtered list (if any)
                if selected_conv_id is None and not filtered_df.empty:
                    selected_conv_id = filtered_df.iloc[0]['id']
                    st.session_state.selected_conv_id = selected_conv_id
                
                if selected_conv_id:
                    selected_conv = next((c for c in conversations if c.id == selected_conv_id), None)
                    if selected_conv:
                        # Add some visual separation with a colored box
                        achievement_status = extract_goal_achievement(selected_conv)
                        status_color = "#D5F5E3" if achievement_status else "#FADBD8"
                        
                        # Display conversation metadata
                        st.markdown(f"<div style='background-color:{status_color}; padding:10px; border-radius:5px;'>"
                                    f"<strong>Goal:</strong> {selected_conv.goal}<br>"
                                    f"<strong>Goal Type:</strong> {selected_conv.goal_type}<br>"
                                    f"<strong>Goal Achieved:</strong> {'Yes' if achievement_status else 'No'}"
                                    f"</div>", unsafe_allow_html=True)
                        
                        # Display conversation turns
                        st.write("### Conversation")
                        for i, turn in enumerate(selected_conv.turns):
                            if turn.role == "user":
                                st.markdown(f"**User ({turn.id}):**")
                                
                                # Check if content contains JSON and render appropriately
                                is_json, json_data = contains_json(turn.content)
                                if is_json and isinstance(json_data, dict):
                                    # First render the text as a div for context
                                    st.markdown(
                                        f"<div style='background-color:#f0f2f6; padding:10px; border-radius:5px; "
                                        f"border-left:4px solid #6c757d; margin-bottom:5px;'>{turn.content}</div>", 
                                        unsafe_allow_html=True
                                    )
                                    # Then display the extracted JSON in a more readable format
                                    with st.expander("View JSON data", expanded=False):
                                        st.json(json_data)
                                else:
                                    # Render user text as div with styling
                                    st.markdown(
                                        f"<div style='background-color:#f0f2f6; padding:10px; border-radius:5px; "
                                        f"border-left:4px solid #6c757d; margin-bottom:10px;'>{turn.content}</div>", 
                                        unsafe_allow_html=True
                                    )
                            else:
                                st.markdown(f"**Assistant ({turn.id}):**")
                                
                                # First check if it's an XML code block
                                is_xml, xml_content = is_xml_code_block(turn.content)
                                
                                if is_xml:
                                    # Process the XML content
                                    processed_content = process_html_headings(xml_content)
                                    
                                    # Render as HTML with XML styling
                                    st.markdown(
                                        f"<div style='background-color:#e8f4f8; padding:10px; border-radius:5px; "
                                        f"border-left:4px solid #17a2b8; margin-bottom:10px;'>{processed_content}</div>",
                                        unsafe_allow_html=True
                                    )
                                elif is_html(turn.content):
                                    # Process headings to bold text for regular HTML
                                    processed_content = process_html_headings(turn.content)
                                    
                                    # Render as HTML if it contains HTML/XML tags
                                    st.markdown(
                                        f"<div style='background-color:#e8f4f8; padding:10px; border-radius:5px; "
                                        f"border-left:4px solid #17a2b8; margin-bottom:10px;'>{processed_content}</div>",
                                        unsafe_allow_html=True
                                    )
                                else:
                                    # Render as markdown if no HTML detected
                                    st.markdown(
                                        f"<div style='background-color:#e8f4f8; padding:10px; border-radius:5px; "
                                        f"border-left:4px solid #17a2b8; margin-bottom:10px;'>{turn.content}</div>",
                                        unsafe_allow_html=True
                                    )
                            
                            # if i < len(selected_conv.turns) - 1:
                            #     st.markdown("---")
                else:
                    st.info("Select a conversation from the list on the left to view details.")
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
    else:
        # Initialize session state for conversation selection
        if 'selected_conv_id' not in st.session_state:
            st.session_state.selected_conv_id = None
            
        # Display instructions when no file is uploaded - update column ratio here too
        col_left, col_right = st.columns([1, 2])
        with col_left:
            st.info("Please upload a JSONL file containing conversation histories.")
        with col_right:
            st.info("Conversation details will appear here after you select a conversation.")

if __name__ == "__main__":
    # Attempt to handle import errors more gracefully
    try:
        main()
    except ImportError as e:
        st.error(f"Import error: {str(e)}")
        st.error("Make sure you're running the dashboard from the simulacra directory.")
        st.info("Try running: cd /home/smajumdar/vijil/poc_projects/simulacra && streamlit run dashboard.py")
