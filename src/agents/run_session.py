from agents.base_types import Persona, Conversation, ConversationTurn, RedTeamingSession
from agents.shared.creator import CustomReactAgent

from string import Template
import os
import yaml
# from dotenv import load_dotenv

# load_dotenv(".env")

import json
from langchain_core.output_parsers import JsonOutputParser


async def run_session_from_config(persona_config, target_agent_config, goal_generator_config=None, redteamer_config=None, num_goals = 1, verbose = False, max_turns = 1, use_db=True):
    """
    Main function to run the red teaming session.
    
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
        
    if redteamer_config is None:
        redteamer_config = os.path.join(
            src_dir, 'configs', 'tester.yaml'
        )
    elif not os.path.isabs(redteamer_config):
        redteamer_config = os.path.join(src_dir, redteamer_config)

    goal_generator_dict = load_yaml(goal_generator_config)
    agent_config_dict = load_yaml(target_agent_config)
    redteamer_config_dict = load_yaml(redteamer_config)

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

    goal_dict = generate_goal(goal_generator_dict, var_template, agent_config_dict, num_goals)
    if goal_dict is None:
        print("Failed to generate goals. Exiting session.")
        return {}
    
    good_faith_goal = goal_dict['good_faith'][0]  # Example: Get the first good faith goal
    bad_faith_goal = goal_dict['bad_faith'][0]  # Example: Get the first bad faith goal
    goals = {'good_faith' : good_faith_goal, 'bad_faith' : bad_faith_goal}
    result_dict = {}
    for (goal_type, goal) in goals.items():
        seed_prompt = generate_seed_prompt(redteamer_config_dict, var_template, agent_config_dict, goal)
        if seed_prompt is None:
            print("Error generating seed prompt. Skipping.")
            continue

        sut_agent = create_agent(agent_config_dict, thread_id="3")
        red_teamer_agent = create_red_teamer_agent(redteamer_config_dict, var_template, goal, thread_id="4")

        red_teaming_session = RedTeamingSession(
            sut_agent=sut_agent,
            redteamer_agent=red_teamer_agent,
        )

        await red_teaming_session.run_conversation(goal, seed_prompt, max_turns=max_turns, verbose = verbose)
        result_dict[goal_type] = red_teaming_session.conversation_history
    return result_dict


def load_yaml(config_path):
    """
    Load a YAML configuration file.
    """
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def generate_goal(goal_generator_dict, var_template, agent_config_dict, num_goals):
    """
    Generate a goal using the goal generator agent.
    """
    user_prompt_template = Template(goal_generator_dict['templates']['user_prompt'])
    sys_prompt_template = Template(goal_generator_dict['templates']['system_prompt'])

    sys_prompt = sys_prompt_template.substitute({'num_goals': num_goals})
    user_prompt = user_prompt_template.substitute(**var_template)

    goal_generator_agent = CustomReactAgent(
        sys_prompt=sys_prompt,
        base_url='https://api.together.xyz/v1',
        api_key=os.getenv('TOGETHER_API_KEY'),
        model_name=goal_generator_dict['llm']['model'],
        temperature=goal_generator_dict['llm']['params']['temperature'],
        thread_id=1
    )

    goal_list_text = goal_generator_agent.chat(user_prompt)
    try:
        goals_dict = JsonOutputParser().parse(goal_list_text)['goals']
    except Exception as e:
        print(f"Error parsing goal list: {e}")
        print(f"Goal list text: {goal_list_text}")
        return None
    return goals_dict
    # return goals_dict['bad_faith'][1]


def generate_seed_prompt(redteamer_config_dict, var_template, agent_config_dict, goal):
    """
    Generate a seed prompt using the redteamer agent.
    """
    sysprompt_redteamer_seed = Template(redteamer_config_dict['templates']['role_and_task_prompt']).substitute(var_template) + '\n\n' + redteamer_config_dict['templates']['job_description_prompt']
    userprompt_redteamer_seed = Template(redteamer_config_dict['templates']['user_prompt']).substitute(agent_sys_prompt=agent_config_dict['templates']['system_prompt'], goal=goal)

    seed_prompt_agent = CustomReactAgent(
        sys_prompt=sysprompt_redteamer_seed,
        base_url='https://api.together.xyz/v1',
        api_key=os.getenv('TOGETHER_API_KEY'),
        model_name=redteamer_config_dict['llm']['model'],
        temperature=redteamer_config_dict['llm']['params']['temperature'],
        thread_id=2
    )

    seed_prmopt_chat = seed_prompt_agent.chat(userprompt_redteamer_seed)
    try:
        seed_prompt = JsonOutputParser().parse(seed_prmopt_chat)['seed_prompt']
    except Exception as e:
        print(f"Error parsing seed prompt: {e}")
        print(f"Seed prompt chat: {seed_prmopt_chat}")
        return None
    return seed_prompt

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


def create_red_teamer_agent(redteamer_config_dict, var_template, goal, thread_id):
    """
    Create a CustomReactAgent for the redteamer agent.
    """
    red_teaming_agent_sys_prompt = Template(redteamer_config_dict['templates']['role_and_task_prompt']).substitute(var_template) + '\n\n' + Template(redteamer_config_dict['templates']['target_goal']).substitute({'goal': goal})

    return CustomReactAgent(
        sys_prompt=red_teaming_agent_sys_prompt,
        base_url='https://api.together.xyz/v1',
        api_key=os.getenv('TOGETHER_API_KEY'),
        model_name=redteamer_config_dict['llm']['model'],
        temperature=redteamer_config_dict['llm']['params']['temperature'],
        thread_id=thread_id
    )