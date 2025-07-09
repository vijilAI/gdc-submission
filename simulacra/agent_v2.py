import json
from typing import List, Optional
from string import Template
import uuid
import re
from dataclasses import asdict
from tqdm.asyncio import tqdm_asyncio
from langchain_core.output_parsers import JsonOutputParser

from vijil_core.llm.vijil_llm_client import CompletionParams
from vijil_objects.agents.harness_creation_agent.base import VijilLLMAgent
from .types import RedTeamerPersona, Conversation


class ConversationAgent(VijilLLMAgent):
    id: str = "chat-agent"
    name: str = "Chat Agent"
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
            
    async def chat_completions(self, messages: list[dict], sys_prompt: Optional[str] = None):
        """
        Generate a chat completion response based on the provided messages.
        
        :param messages: List of messages to be processed.
        :return: The response from the chat completion.
        """
        return await self.client.chat_completions(
            [{"role": "system", "content": sys_prompt or self.sys_prompt}] + messages,
            params=self.completion_params
        )
        
class RedTeamerAgent(ConversationAgent):
    CONFIG_PATH = "configs/redteamer_noocean.yaml"
    def __init__(self, persona_path: str, config_path: str = None):
        if config_path is None:
            config_path = self.CONFIG_PATH
        super().__init__(config_path=config_path)
        
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
        
    async def run_conversation(self, goal: str, goal_type: str = "", max_turns: int = 10, verbose: bool = False) -> Conversation:
        """
        Run a conversation between the red teamer agent and the system under test.
        
        :param max_turns: Maximum number of conversation turns.
        :param verbose: If True, prints out conversation messages as they occur.
        :return: The complete conversation.
        """
        conversation_id = f"{self.sut_agent.id}_vs_{self.redteamer_agent.persona.id}_{uuid.uuid4()}"
        conversation = Conversation(id=conversation_id, goal=goal, goal_type=goal_type, turns=[])
        
        messages = [{"role": "assistant", "content": ""}]  # Start with an empty assistant message
        json_parser = JsonOutputParser()
        
        # Run the conversation for the specified number of turns
        for turn in range(max_turns):
            # First turn starts with the red teamer agent
            redteamer_response = await self.redteamer_agent.chat_completions(
                messages=messages,
                sys_prompt=f"{self.redteamer_agent.sys_prompt}{goal}"
            )
            redteamer_message = redteamer_response.generations[0].content
            conversation.add_turn(
                id=self.redteamer_agent.persona.id,
                role="user",
                content=redteamer_message
            )
            messages.append({"role": "user", "content": redteamer_message})
            
            if verbose:
                print(f"Turn {turn}: {self.redteamer_agent.persona.name}\n{redteamer_message}\n")
            
            # Check if the red teamer has identified untrustworthy behavior
            try:
                json_match = re.search(r'({[\s\S]*"goal_achieved"[\s\S]*})', redteamer_message)
                if json_match:
                    json_str = json_match.group(1)
                    result = json_parser.parse(json_str)
                    if result.get("goal_achieved") == True:
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
                id=self.sut_agent.id,
                role="assistant",
                content=sut_message
            )
            messages.append({"role": "assistant", "content": sut_message})
            
            if verbose:
                print(f"Turn {turn}: \n{self.sut_agent.name}\n{sut_message}\n")
        
        # Add a final redteamer assessment of the last SUT response only if the last turn was from the assistant
        if conversation.turns and conversation.turns[-1].role == "assistant":
            final_redteamer_response = await self.redteamer_agent.chat_completions(messages)
            final_redteamer_message = final_redteamer_response.generations[0].content
            conversation.add_turn(
                id=self.redteamer_agent.persona.id,
                role="user",
                content=final_redteamer_message
            )
            
            # Check the final redteamer message for untrustworthy behavior
            try:
                json_match = re.search(r'({[\s\S]*"goal_achieved"[\s\S]*})', final_redteamer_message)
                if json_match:
                    json_str = json_match.group(1)
                    json_parser.parse(json_str)  # Just parse to validate, no need to check result
            except Exception:
                pass
            
        self.conversation_history.append(conversation)
        print(messages)
        
    async def run_session(self, iters: int = 10, max_turns: int = 10) -> List[Conversation]:
        """
        Run multiple red teaming conversations, picking one goal for a specified iterations.
        
        :param iters: Number of iterations one goal is run.
        :param max_turns: Maximum number of turns per session.
        :return: List of completed conversations.
        """
        
        tasks = [
            self.run_conversation(goal=goal, goal_type=goal_type, max_turns=max_turns)
            for goal_type in self.redteamer_agent.persona.goals
            for goal in self.redteamer_agent.persona.goals[goal_type]
            for _ in range(iters)
        ]
        await tqdm_asyncio.gather(*tasks)
    
    def export_conversation_history(self, output_path: str = None, format: str = "jsonl") -> List[dict]:
        """
        Export the conversation history to a file and return it as a list of dictionaries.
        
        :param output_path: Optional path to save the conversation history.
        :param format: Format to use for export ("json" or "jsonl"). Default is "json".
        :return: List of conversation dictionaries.
        """
        # Write to a file if output_path is provided
        if output_path:
            # Create directory if it doesn't exist
            import os
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            if format.lower() == "jsonl":
                with open(output_path, 'w') as f:
                    for conv in self.conversation_history:
                        f.write(json.dumps(asdict(conv)) + '\n')
            else:  # Default to standard JSON
                with open(output_path, 'w') as f:
                    json.dump(
                        [asdict(conv) for conv in self.conversation_history],
                        f, indent=2
                    )
