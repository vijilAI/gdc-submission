from dataclasses import dataclass
from typing import Dict, List, Any
import json

import uuid
import re
from langchain_core.output_parsers import JsonOutputParser

from .shared.creator import CustomReactAgent

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
        """
        Add a new turn to the conversation.
        
        :param role: The role of the speaker (e.g., 'user', 'assistant').
        :param id: The id of the speaker.
        :param content: The content of the turn.
        """
        self.turns.append(ConversationTurn(role=role, id=id, content=content))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation to a dictionary format.
        
        :return: Dictionary representation of the conversation.
        """
        return { "goal" : self.goal, "turns": [turn.__dict__ for turn in self.turns]}
    
    def to_list(self) -> list:
        """
        Convert the conversation to a list of dictionaries.
        
        :return: List of dictionaries representing each turn in the conversation.
        """
        return [turn.__dict__ for turn in self.turns]


@dataclass
class Persona:
    participant_id: str
    response_language : str
    demographic_info: Dict[str, Any]
    high_level_AI_view : str
    survey_responses: Dict[str, str]
    
    @classmethod
    def from_json(cls, json_path: str) -> 'Persona':
        """
        Load a Persona from a JSON file.
        
        :param json_path: Path to the JSON file containing the persona data.
        :return: Persona instance with data from the JSON file.
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def from_db(cls, persona_id: str) -> 'Persona':
        """
        Load a Persona from the database by ID.
        
        :param persona_id: The persona ID (filename without .json extension)
        :return: Persona instance with data from the database.
        """
        import sys
        import os
        
        # Add app/db to path for database imports
        db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'db')
        sys.path.append(os.path.abspath(db_path))
        
        try:
            from operations import persona_db
            persona_model = persona_db.get_persona_by_id(persona_id)
            
            if persona_model is None:
                raise ValueError(f"Persona with ID '{persona_id}' not found in database")
            
            # Convert database model to dictionary and create Persona instance
            persona_data = persona_model.to_dict()
            return cls(**persona_data)
            
        except ImportError as e:
            raise ImportError(f"Failed to import database operations: {e}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Persona':
        """
        Create a Persona from a dictionary.
        
        :param data: Dictionary containing persona data.
        :return: Persona instance with data from the dictionary.
        """
        return cls(**data)
    
    def to_template_vars(self) -> Dict[str, Any]:
        """
        Convert the persona to a dictionary of template variables.
        
        :return: Dictionary with flattened persona attributes for template substitution.
        """
        template_vars = {
            "age_bracket": self.demographic_info["age bracket"],
            "gender": self.demographic_info["gender"],
            'religion': self.demographic_info['religion'],
            'country' : self.demographic_info['self identified country'],
            'community_type' : self.demographic_info['community type'],
            'true_langauge_preferred' : self.demographic_info['preferred language'],
            "high_level_AI_view": self.high_level_AI_view,
            "participant_id": self.participant_id,
            "response_language": self.response_language,
            "survey_responses": json.dumps(self.survey_responses, indent=4)
        }
        return template_vars
    


class RedTeamingSession:
    def __init__(self, sut_agent: CustomReactAgent, redteamer_agent: CustomReactAgent):
        """
        Initialize a red teaming session between a system under test (SUT) agent and a red teamer agent.
        
        :param sut_agent: The system under test agent.
        :param redteamer_agent: The red teamer agent.
        """
        self.sut_agent: CustomReactAgent = sut_agent
        self.redteamer_agent: CustomReactAgent = redteamer_agent
        self.conversation_history: List[Conversation] = []
        
    async def run_conversation(self, goal: str, starting_prompt : str, goal_type: str = "", max_turns: int = 10, verbose: bool = False) -> Conversation:
        """
        Run a conversation between the red teamer agent and the system under test.
        
        :param max_turns: Maximum number of conversation turns.
        :param verbose: If True, prints out conversation messages as they occur.
        :return: The complete conversation.
        """
        conversation_id = f"{uuid.uuid4()}"
        conversation = Conversation(id=conversation_id, goal=goal, goal_type=goal_type, turns=[])

        
        messages = [{"role": "user", "content": starting_prompt}]  # Start with seed prompt
        conversation.add_turn(id = 'redteamer_agent', role = 'user', content = starting_prompt)
        json_parser = JsonOutputParser()
        
            

        # Run the conversation for the specified number of turns
        for turn in range(max_turns):
            # start with seed prompt
            sut_response = await self.sut_agent.chat_with_history(messages)
            sut_message = sut_response
            
            conversation.add_turn(
                    id='sut_agent',
                    role="assistant",
                    content=sut_message
                )
            messages.append({"role": "assistant", "content": sut_message})
            if verbose:
                print(f"Turn {turn}: \n{self.sut_agent}\n{sut_message}\n")

            
            redteamer_response = await self.redteamer_agent.chat_with_history(
                messages,
            )
            redteamer_message = redteamer_response
            conversation.add_turn(
                id='redteamer_agent',
                role="user",
                content=redteamer_message
            )
            messages.append({"role": "user", "content": redteamer_message})
                
            if verbose:
                print(f"Turn {turn}: redteamer \n{redteamer_message}\n")
                
            # Check if the red teamer has identified untrustworthy behavior
            try:
                json_match = re.search(r'({[\s\S]*"goal_achieved"[\s\S]*})', redteamer_message)
                if json_match:
                    json_str = json_match.group(1)
                    result = json_parser.parse(json_str)
                    if result.get("goal_achieved") == True:
                        print("stopping")
                        # Add the conversation to the history and return early
                        self.conversation_history.append(conversation)
                        return self
            except Exception:
                print("Can't parse")
                # Continue if we can't parse JSON or it doesn't have the expected format
                pass
            
            # Get response from the SUT agent
                    
        self.conversation_history.append(conversation)
