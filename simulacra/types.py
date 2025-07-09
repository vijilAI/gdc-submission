from dataclasses import dataclass
from typing import Dict, List, Any
import json


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
        return {"turns": [turn.__dict__ for turn in self.turns]}
    
    def to_list(self) -> list:
        """
        Convert the conversation to a list of dictionaries.
        
        :return: List of dictionaries representing each turn in the conversation.
        """
        return [turn.__dict__ for turn in self.turns]

@dataclass
class RedTeamerPersona:
    id: str
    name: str
    demographic_attributes: Dict[str, Any]
    expertise: Dict[str, Any]
    personality_traits: Dict[str, Any]
    testing_style: Dict[str, Any]
    background_narrative: str
    definition_of_trust: str
    goals: Dict[str, List[str]]
    
    @classmethod
    def from_json(cls, json_path: str) -> 'RedTeamerPersona':
        """
        Load a RedTeamerPersona from a JSON file.
        
        :param json_path: Path to the JSON file containing the persona data.
        :return: RedTeamerPersona instance with data from the JSON file.
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_template_vars(self) -> Dict[str, Any]:
        """
        Convert the persona to a dictionary of template variables.
        
        :return: Dictionary with flattened persona attributes for template substitution.
        """
        template_vars = {
            "name": self.name,
            "age": self.demographic_attributes["age"],
            "gender": self.demographic_attributes["gender"],
            "ethnicity": self.demographic_attributes["ethnicity"],
            "education": self.demographic_attributes["education"],
            "location": self.demographic_attributes["location"],
            "background_narrative": self.background_narrative,
            "primary_domain": self.expertise["primary_domain"],
            "secondary_domains": ", ".join(self.expertise["secondary_domains"]),
            "technical_level": self.expertise["technical_level"],
            "languages": ", ".join(self.expertise["languages"]),
            "openness": self.personality_traits["openness"],
            "conscientiousness": self.personality_traits["conscientiousness"],
            "extraversion": self.personality_traits["extraversion"],
            "agreeableness": self.personality_traits["agreeableness"],
            "neuroticism": self.personality_traits["neuroticism"],
            "preferred_approaches": ", ".join(self.testing_style["preferred_approaches"]),
            "vulnerability_focus": ", ".join(self.testing_style["vulnerability_focus"]),
            "definition_of_trust": self.definition_of_trust
        }
        return template_vars
