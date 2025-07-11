from agents.base_types import (
    Persona, VirtualUserSession
)
from agents.shared.creator import CustomReactAgent

from string import Template
import os
import yaml
import time
# from dotenv import load_dotenv
import asyncio

# load_dotenv(".env")

from langchain_core.output_parsers import JsonOutputParser


async def run_session_from_config(
    persona_config, target_agent_config, goal_generator_config=None,
    user_config=None, num_goals=1, verbose=False, max_turns=1,
    conversations_per_goal=1, use_db=True, progress_callback=None
):
    """
    Main function to run the virtual user testing session.
    
    :param persona_config: Either a path to JSON file or persona ID for database lookup
    :param use_db: If True, treat persona_config as persona ID for database lookup
    """
    # Get the src directory for resolving config paths
    src_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Set default configs with absolute paths
    if goal_generator_config is None:
        goal_generator_config = os.path.join(
            src_dir, 'configs', 'goal_generator.yaml'
        )
    elif not os.path.isabs(goal_generator_config):
        goal_generator_config = os.path.join(src_dir, goal_generator_config)
        
    if user_config is None:
        user_config = os.path.join(
            src_dir, 'configs', 'tester.yaml'
        )
    elif not os.path.isabs(user_config):
        user_config = os.path.join(src_dir, user_config)

    goal_generator_dict = load_yaml(goal_generator_config)
    agent_config_dict = load_yaml(target_agent_config)
    user_config_dict = load_yaml(user_config)

    # Progress: 35% - loaded configs
    if progress_callback:
        progress_callback("Loaded configurations", 35)

    # Load persona from database or JSON file
    if use_db:
        # Handle different types of persona_config
        if isinstance(persona_config, dict):
            # persona_config is already a persona dictionary
            persona = Persona.from_dict(persona_config)
        elif isinstance(persona_config, str):
            # Extract persona ID from file path if necessary
            if persona_config.endswith('.json'):
                persona_id = os.path.basename(persona_config).replace('.json', '')
            else:
                persona_id = persona_config
            persona = Persona.from_db(persona_id)
        else:
            raise ValueError(f"Invalid persona_config type: {type(persona_config)}")
    else:
        if isinstance(persona_config, str):
            persona = Persona.from_json(persona_config)
        else:
            raise ValueError("When use_db=False, persona_config must be a file path string")
    
    var_template = persona.to_template_vars()
    var_template['agent_sys_prompt'] = agent_config_dict['templates']['system_prompt']

    # Progress: 40% - loaded persona
    if progress_callback:
        progress_callback("Loaded persona data", 40)

    goal_dict = generate_goal(goal_generator_dict, var_template, agent_config_dict, num_goals, progress_callback)
    if goal_dict is None:
        print("Failed to generate goals. Exiting session.")
        return {}
    
    # Use the simplified goal structure - just a list of realistic goals
    goals_list = goal_dict.get('goals', [])
    if not goals_list:
        print("No goals generated. Exiting session.")
        return {}
    
    # Create a result dict to store conversations for each goal
    result_dict = {}
    
    # Progress: 60% - starting conversations
    if progress_callback:
        progress_callback("Starting conversations", 60)
    
    # async task to run conversations for each goal
    async def run_goal_conversations(goal, goal_idx, conv_idx):
        seed_prompt = generate_seed_prompt(
            user_config_dict, var_template, agent_config_dict, goal, progress_callback
        )
        if seed_prompt is None:
            print(f"Error generating seed prompt for goal {goal_idx+1}, "
                  f"conversation {conv_idx+1}. Skipping.")
            return
        
        # Use unique thread IDs for each conversation
        thread_suffix = f"{goal_idx}_{conv_idx}"
        sut_agent = create_agent(
            agent_config_dict, thread_id=f"sut_{thread_suffix}"
        )
        virtual_user_agent = create_virtual_user_agent(
            user_config_dict, var_template, goal,
            thread_id=f"virtual_user_{thread_suffix}"
        )

        testing_session = VirtualUserSession(
            sut_agent=sut_agent,
            virtual_user_agent=virtual_user_agent,
        )

        conversation = await testing_session.run_conversation(
            goal, seed_prompt, max_turns=max_turns, verbose=verbose
        )
        return {"goal": goal, "goal_idx": goal_idx, "conversation": conversation}
    tasks = [
        run_goal_conversations(goal, i, conv_idx)
        for i, goal in enumerate(goals_list)
        for conv_idx in range(conversations_per_goal)
    ]
    
    # Progress: 70% - running conversations
    if progress_callback:
        progress_callback("Running conversations", 70)
    
    conversation_list = await asyncio.gather(*tasks)
    
    # Progress: 85% - processing results
    if progress_callback:
        progress_callback("Processing conversation results", 85)
    
    # store conversations in result_dict
    for conv in conversation_list:
        if conv is not None:
            goal_idx = conv['goal_idx']
            conversation = conv['conversation']
            if f"goal_{goal_idx+1}" not in result_dict:
                result_dict[f"goal_{goal_idx+1}"] = []
            result_dict[f"goal_{goal_idx+1}"].append(conversation)
    return result_dict


def load_yaml(config_path):
    """
    Load a YAML configuration file safely.
    """
    import os
    
    # Define the safe root directory
    src_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Remove any potential path traversal sequences
    normalized_path = os.path.normpath(config_path).replace('..', '')
    
    # If it's a relative path, make it relative to src_dir
    if not os.path.isabs(normalized_path):
        normalized_path = os.path.join(src_dir, normalized_path)
    
    normalized_path = os.path.abspath(normalized_path)
    
    # Ensure the path is within the expected directory
    if not normalized_path.startswith(os.path.abspath(src_dir)):
        raise ValueError(f"Unsafe path detected: {config_path}")
    
    # Additional check: ensure the path exists and is a file
    if not os.path.exists(normalized_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    if not os.path.isfile(normalized_path):
        raise ValueError(f"Path is not a file: {config_path}")
    
    with open(normalized_path, "r") as f:
        return yaml.safe_load(f)


def generate_goal(goal_generator_dict, var_template, agent_config_dict, num_goals, progress_callback=None):
    """
    Generate a goal using the goal generator agent with retry logic.
    """
    # Get retry configuration
    retry_config = goal_generator_dict.get('retries', {}).get('goal_generation', {})
    max_attempts = retry_config.get('max_attempts', 3)
    backoff_seconds = retry_config.get('backoff_seconds', 2)
    timeout_seconds = retry_config.get('timeout_seconds', 30)
    
    user_prompt_template = Template(goal_generator_dict['templates']['user_prompt'])
    sys_prompt_template = Template(goal_generator_dict['templates']['system_prompt'])

    sys_prompt = sys_prompt_template.substitute({'num_goals': num_goals})
    user_prompt = user_prompt_template.substitute(**var_template)

    for attempt in range(max_attempts):
        try:
            goal_generator_agent = CustomReactAgent(
                sys_prompt=sys_prompt,
                base_url='https://api.together.xyz/v1',
                api_key=os.getenv('TOGETHER_API_KEY'),
                model_name=goal_generator_dict['llm']['model'],
                temperature=goal_generator_dict['llm']['params']['temperature'],
                thread_id=1
            )

            goal_list_text = goal_generator_agent.chat(user_prompt)
            
            # Parse the output
            goals_dict = JsonOutputParser().parse(goal_list_text)
            
            # Validate that we got the expected structure
            if 'goals' in goals_dict and isinstance(goals_dict['goals'], list):
                print(f"Successfully generated {len(goals_dict['goals'])} goals on attempt {attempt + 1}")
                # Update progress callback
                if progress_callback:
                    progress_callback(f"Generated {len(goals_dict['goals'])} goals", 50)
                return goals_dict
            else:
                raise ValueError("Invalid goals structure returned")
                
        except Exception as e:
            print(f"Goal generation attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                print(f"Retrying in {backoff_seconds} seconds...")
                time.sleep(backoff_seconds)
                # Exponential backoff
                backoff_seconds *= 2
            else:
                print("All goal generation attempts failed")
                return None
    
    return None


def generate_seed_prompt(user_config_dict, var_template, agent_config_dict, goal, progress_callback=None):
    """
    Generate a seed prompt using the redteamer agent with retry logic.
    """
    # Get retry configuration
    retry_config = user_config_dict.get('retries', {}).get('seed_prompt_generation', {})
    max_attempts = retry_config.get('max_attempts', 3)
    backoff_seconds = retry_config.get('backoff_seconds', 1)
    timeout_seconds = retry_config.get('timeout_seconds', 20)
    
    # Prepare prompts
    role_task_template = user_config_dict['templates']['role_and_task_prompt']
    job_desc_template = user_config_dict['templates']['job_description_prompt']
    user_prompt_template = user_config_dict['templates']['user_prompt']
    
    sysprompt_redteamer_seed = Template(role_task_template).substitute(var_template) + '\n\n' + job_desc_template
    userprompt_redteamer_seed = Template(user_prompt_template).substitute(
        agent_sys_prompt=agent_config_dict['templates']['system_prompt'], 
        goal=goal
    )

    for attempt in range(max_attempts):
        try:
            seed_prompt_agent = CustomReactAgent(
                sys_prompt=sysprompt_redteamer_seed,
                base_url='https://api.together.xyz/v1',
                api_key=os.getenv('TOGETHER_API_KEY'),
                model_name=user_config_dict['llm']['model'],
                temperature=user_config_dict['llm']['params']['temperature'],
                thread_id=2
            )

            seed_prompt_chat = seed_prompt_agent.chat(userprompt_redteamer_seed)
            
            # Parse the output
            parsed_result = JsonOutputParser().parse(seed_prompt_chat)
            
            if 'seed_prompt' in parsed_result:
                seed_prompt = parsed_result['seed_prompt']
                print(f"Successfully generated seed prompt on attempt {attempt + 1}")
                # Update progress callback
                if progress_callback:
                    progress_callback("Generated seed prompt", 65)
                return seed_prompt
            else:
                raise ValueError("No 'seed_prompt' key in response")
                
        except Exception as e:
            print(f"Seed prompt generation attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                print(f"Retrying in {backoff_seconds} seconds...")
                time.sleep(backoff_seconds)
                # Exponential backoff
                backoff_seconds *= 2
            else:
                print("All seed prompt generation attempts failed")
                return None
    
    return None

def create_agent(agent_config_dict, thread_id):
    """
    Create a CustomReactAgent for the SUT agent.
    """
    return CustomReactAgent(
        sys_prompt=agent_config_dict['templates']['system_prompt'],
        base_url='https://api.together.xyz/v1',
        api_key=os.getenv('TOGETHER_API_KEY'),
        model_name=agent_config_dict['llm']['model'],
        temperature=agent_config_dict['llm']['params']['temperature'],
        thread_id=thread_id
    )


def create_virtual_user_agent(
    virtual_user_config_dict, var_template, goal, thread_id
):
    """
    Create a CustomReactAgent for the virtual user agent.
    """
    virtual_user_agent_sys_prompt = (
        Template(virtual_user_config_dict['templates']['role_and_task_prompt'])
        .substitute(var_template) + '\n\n' +
        Template(virtual_user_config_dict['templates']['target_goal'])
        .substitute({'goal': goal})
    )

    return CustomReactAgent(
        sys_prompt=virtual_user_agent_sys_prompt,
        base_url='https://api.together.xyz/v1',
        api_key=os.getenv('TOGETHER_API_KEY'),
        model_name=virtual_user_config_dict['llm']['model'],
        temperature=virtual_user_config_dict['llm']['params']['temperature'],
        thread_id=thread_id
    )