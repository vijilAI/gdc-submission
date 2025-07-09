import json
from typing import List, Dict, Optional
from string import Template
import uuid
import re
import asyncio
from tqdm.asyncio import tqdm
from langchain_core.output_parsers import JsonOutputParser

from vijil_core.llm.vijil_llm_client import CompletionParams
from vijil_objects.agents.harness_creation_agent.base import VijilLLMAgent
from .types import RedTeamerPersona, Conversation


class ConversationAgent(VijilLLMAgent):
    name: str = "chat-agent"
    description: str = None
    version: str = "1.0.0"
    
    def __init__(self, config_path: str):
        self.CONFIG_PATH = config_path
        super().__init__()
        
        # set completion parameters
        if "params" in self.agent_config["llm"]:
            self.completion_params = CompletionParams(**self.agent_config["llm"]["params"])
        else:
            # default completion parameters
            self.completion_params = CompletionParams(
                temperature=0,
                top_p=1.0,
                max_completion_tokens=4096,
            )
            
        self.sys_prompt = self.agent_config["templates"]["system_prompt"]
        
        # add metadata if present in the agent config
        if "metadata" in self.agent_config:
            for attr in self.agent_config["metadata"]:
                setattr(self, attr, self.agent_config["metadata"][attr])
        else:
            self.name = self.name + str(uuid.uuid4())
            
    async def chat_completions(self, messages: list[dict]):
        """
        Generate a chat completion response based on the provided messages.
        
        :param messages: List of messages to be processed.
        :return: The response from the chat completion.
        """
        return await self.client.chat_completions(
            [{"role": "system", "content": self.sys_prompt}] + messages,
            params=self.completion_params
        )
        
class RedTeamerAgent(ConversationAgent):
    CONFIG_PATH = "configs/redteamer.yaml"
    def __init__(self, persona_path: str):
        super().__init__(config_path=self.CONFIG_PATH)
        
        # Load the persona from the JSON file
        self.persona = RedTeamerPersona.from_json(persona_path)
        
        # Apply the persona to the system prompt using string.Template
        template = Template(self.agent_config["templates"]["system_prompt"])
        self.sys_prompt = template.substitute(**self.persona.to_template_vars())
        
        # set completion parameters for red teaming
        if "params" not in self.agent_config["llm"]:
            self.completion_params = CompletionParams(
                temperature=0.7, # set higher for more creative responses
                top_p=1.0,
                max_completion_tokens=512, # limit to avoid long responses
            )
            

class RedTeamingSession:
    def __init__(self, sut_agent: ConversationAgent, redteamer_agent: RedTeamerAgent):
        """
        Initialize a red teaming session between a system under test (SUT) agent and a red teamer agent.
        
        :param sut_agent: The system under test agent.
        :param redteamer_agent: The red teamer agent.
        """
        self.sut_agent: ConversationAgent = sut_agent
        self.redteamer_agent: RedTeamerAgent = redteamer_agent
        self.conversation_history: List[Conversation] = []
        
    async def run_conversation(self, max_turns: int = 10, verbose: bool = False) -> Conversation:
        """
        Run a conversation between the red teamer agent and the system under test.
        
        :param max_turns: Maximum number of conversation turns.
        :param verbose: If True, prints out conversation messages as they occur.
        :return: The complete conversation.
        """
        conversation_id = f"session_{len(self.conversation_history) + 1}"
        conversation = Conversation(id=conversation_id, turns=[])
        
        messages = [{"role": "assistant", "content": ""}]  # Start with an empty assistant message
        json_parser = JsonOutputParser()
        
        # Run the conversation for the specified number of turns
        for turn in range(max_turns):
            # First turn starts with the red teamer agent
            redteamer_response = await self.redteamer_agent.chat_completions(messages)
            redteamer_message = redteamer_response.generations[0].content
            conversation.add_turn(
                role="user",
                name=self.redteamer_agent.persona.name,
                content=redteamer_message
            )
            messages.append({"role": "user", "content": redteamer_message})
            
            if verbose:
                print(f"Turn {turn}: {self.redteamer_agent.persona.name}\n{redteamer_message}\n")
            
            # Check if the red teamer has identified untrustworthy behavior
            try:
                json_match = re.search(r'({[\s\S]*"untrustworthy_behavior"[\s\S]*})', redteamer_message)
                if json_match:
                    json_str = json_match.group(1)
                    result = json_parser.parse(json_str)
                    if result.get("untrustworthy_behavior") == True:
                        # Add the conversation to the history and return early
                        self.conversation_history.append(conversation)
                        return self
            except Exception:
                # Continue if we can't parse JSON or it doesn't have the expected format
                pass
            
            # Get response from the SUT agent
            sut_response = await self.sut_agent.chat_completions(messages)
            sut_message = sut_response.generations[0].content
            conversation.add_turn(
                role="assistant",
                name=self.sut_agent.name,
                content=sut_message
            )
            messages.append({"role": "assistant", "content": sut_message})
            
            if verbose:
                print(f"Turn {turn}: \n{self.sut_agent.name}\n{sut_message}\n")
        
        # Add a final redteamer assessment of the last SUT response
        final_redteamer_response = await self.redteamer_agent.chat_completions(messages)
        final_redteamer_message = final_redteamer_response.generations[0].content
        conversation.add_turn(
            role="user",
            name=self.redteamer_agent.persona.name,
            content=final_redteamer_message
        )
        
        # Check the final redteamer message for untrustworthy behavior
        try:
            json_match = re.search(r'({[\s\S]*"untrustworthy_behavior"[\s\S]*})', final_redteamer_message)
            if json_match:
                json_str = json_match.group(1)
                json_parser.parse(json_str)  # Just parse to validate, no need to check result
        except Exception:
            pass
            
        # Add the conversation to the history
        self.conversation_history.append(conversation)
        return self
        
    def export_conversation_history(self, output_path: str = None, format: str = "jsonl") -> List[dict]:
        """
        Export the conversation history to a file and return it as a list of dictionaries.
        
        :param output_path: Optional path to save the conversation history.
        :param format: Format to use for export ("json" or "jsonl"). Default is "json".
        :return: List of conversation dictionaries.
        """
        conversations = []
        
        for conversation in self.conversation_history:
            conv_dict = {
                "id": conversation.id,
                "turns": [
                    {
                        "role": turn.role,
                        "name": turn.name,
                        "content": turn.content
                    }
                    for turn in conversation.turns
                ]
            }
            conversations.append(conv_dict)
            
        # Write to a file if output_path is provided
        if output_path:
            if format.lower() == "jsonl":
                with open(output_path, 'w') as f:
                    for conv in conversations:
                        f.write(json.dumps(conv) + '\n')
            else:  # Default to standard JSON
                with open(output_path, 'w') as f:
                    json.dump(conversations, f, indent=2)
