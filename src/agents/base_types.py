from dataclasses import dataclass
from typing import Dict, List, Any
import json
import uuid

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
        return {
            "goal": self.goal,
            "turns": [turn.__dict__ for turn in self.turns]
        }
    
    def to_list(self) -> list:
        """
        Convert the conversation to a list of dictionaries.
        
        :return: List of dictionaries representing each turn in the
                 conversation.
        """
        return [turn.__dict__ for turn in self.turns]


@dataclass
class Persona:
    participant_id: str
    response_language: str
    demographic_info: Dict[str, Any]
    high_level_AI_view: str
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
        db_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'app', 'db'
        )
        sys.path.append(os.path.abspath(db_path))
        
        try:
            from operations import persona_db
            persona_model = persona_db.get_persona_by_id(persona_id)
            
            if persona_model is None:
                raise ValueError(
                    f"Persona with ID '{persona_id}' not found in database"
                )
            
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
        Convert Persona to a dictionary of variables for template substitution.
        
        :return: Dictionary with flattened persona attributes for template
                 substitution.
        """
        
        return {
            'gender': self.demographic_info['gender'],
            'age_bracket': self.demographic_info['age bracket'],
            'religion': self.demographic_info['religion'],
            'country': self.demographic_info['self identified country'],
            'community_type': self.demographic_info['community type'],
            'true_langauge_preferred': (
                self.demographic_info['preferred language']
            ),
            'response_language': self.response_language,
            'high_level_AI_view': self.high_level_AI_view,
            'survey_responses': self.survey_responses
        }


@dataclass
class VirtualUserTestingSession:
    """
    A class to manage a conversation session between a system under test (SUT)
    agent and a virtual user agent.
    """

    def __init__(
        self, sut_agent: CustomReactAgent, virtual_user_agent: CustomReactAgent
    ):
        """
        Initialize a virtual user testing session between a system under
        test (SUT) agent and a virtual user agent.
        
        :param sut_agent: The agent being tested.
        :param virtual_user_agent: The virtual user agent performing the
            testing.
        """
        self.sut_agent = sut_agent
        self.virtual_user_agent = virtual_user_agent
        self.conversation_history = None

    async def run_conversation(
        self, goal: str, starting_prompt: str, max_turns: int = 10,
        verbose: bool = False
    ) -> Conversation:
        """
        Run a conversation between the SUT and virtual user agents.
        
        :param goal: The goal of the conversation.
        :param starting_prompt: The initial prompt to start the conversation.
        :param max_turns: The maximum number of turns in the conversation.
        :param verbose: If True, print the conversation turns.
        :return: The conversation history.
        """
        conversation = Conversation(
            id=str(uuid.uuid4()),
            goal=goal,
            turns=[]
        )
        
        # Add the seed prompt as the first turn
        virtual_user_thread_id = (
            self.virtual_user_agent.thread_config["configurable"]["thread_id"]
        )
        conversation.add_turn(
            role='user',
            id=virtual_user_thread_id,
            content=starting_prompt
        )
        
        current_prompt = starting_prompt
        
        for i in range(max_turns):
            # Virtual user's turn
            if verbose:
                print(f"Turn {i+1} - User: {current_prompt[:20]}...")
            
            sut_response = await self.sut_agent.chat_async(current_prompt)
            # sut_response = self.sut_agent.chat(current_prompt)
            conversation.add_turn(
                role='assistant',
                id=self.sut_agent.thread_config["configurable"]["thread_id"],
                content=sut_response
            )
            
            # SUT's turn
            if verbose:
                print(f"Turn {i+1} - Assistant: {sut_response[:20]}...")

            # virtual_user_response = self.virtual_user_agent.chat(sut_response)
            virtual_user_response = await self.virtual_user_agent.chat_async(
                sut_response
            )
            virtual_user_thread_id = (
                self.virtual_user_agent
                .thread_config["configurable"]["thread_id"]
            )
            conversation.add_turn(
                role='user',
                id=virtual_user_thread_id,
                content=virtual_user_response
            )
            
            current_prompt = virtual_user_response
            
        self.conversation_history = conversation
        return self.conversation_history
