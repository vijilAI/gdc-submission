from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from agents.shared.types import State
from langgraph.prebuilt import create_react_agent
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class CustomReactAgent():
    def __init__(self,
                 sys_prompt: str,
                 base_url : Optional[str] = None, 
                 api_key: Optional[str] = None,
                 model_name : Optional[str] = None,
                 temperature: float = 0.0,
                 tool_list: Optional[list] = None,
                 thread_id: str="1"):
    
        # Create the base model client
        self.model = ChatOpenAI(base_url=base_url,
                        api_key=api_key,
                        model=model_name,
                        temperature=temperature)
        
        if tool_list:
            self.model = self.model.bind_tools(tool_list)

        self.sys_prompt = sys_prompt

        memory = MemorySaver()

        self.thread_config = {"configurable": {"thread_id": thread_id}}
        if tool_list:
            self.graph = create_react_agent(self.model, tools=tool_list, checkpointer=memory, state_modifier=self.sys_prompt)
        else:
            def chatbot(state: State):
                return {"messages": [self.model.invoke(state["messages"])]}
            
            # If there are no tools, create a single node graph with a system prompt
            graph_builder = StateGraph(State)
            graph_builder.add_node("chatbot", chatbot)
            graph_builder.add_edge(START, "chatbot")
            graph_builder.add_edge("chatbot", END)
            self.graph = graph_builder.compile(checkpointer=memory)
            self.graph.update_state(self.thread_config, {"messages": [SystemMessage(content=self.sys_prompt)]})
    
    # Use this if you want an entire list of messages from the agent, including all the tool calls
    def get_messages(self, prompt: str):
        query_msg = {"messages": [("user", prompt)]}
        responses = []
        for chunk in self.graph.stream(query_msg, config=self.thread_config, stream_mode="values"):
            msg = chunk["messages"][-1]
            responses.append(msg)
        return responses
    
    # Use this if you just want the final text output
    def chat(self, prompt: str):
        responses = self.get_messages(prompt)
        return responses[-1].content
    
    async def chat_async(self, prompt: str) -> str:
        """
        Asynchronously pass a prompt to the agent and get the response.
        
        :param prompt: The prompt to send to the agent.
        :return: The response from the agent.
        """
        # Update the graph's state with the provided prompt
        self.graph.update_state(self.thread_config, {"messages": [SystemMessage(content=self.sys_prompt), {"role": "user", "content": prompt}]})

        # Generate a response based on the updated state
        responses = []
        async for chunk in self.graph.astream({"messages": [{"role": "user", "content": prompt}]}, config=self.thread_config, stream_mode="values"):
            msg = chunk["messages"][-1]
            responses.append(msg)

        # Return the final response content
        return responses[-1].content

    def chat_with_messages(self, message: Dict[str, Any]) -> str:
        """
        Pass a message to the agent and get the response.
        
        :param message: The message to send to the agent.
        :return: The response from the agent.
        """
        responses = []
        for chunk in self.graph.stream(message, config=self.thread_config, stream_mode="values"):
            msg = chunk["messages"][-1]
            responses.append(msg)
        return responses

    async def chat_with_history(self, messages: List[Dict[str, str]]) -> str:
        """
        Pass a full message history to the agent and get the response.
        
        :param messages: A list of messages representing the conversation history.
                         Each message should be a dictionary with keys like "role" and "content".
                         Example: [{"role": "system", "content": "System prompt"}, {"role": "user", "content": "Hello"}]
        :return: The response from the agent.
        """
        # Update the graph's state with the provided message history
        full_messages = [{"role": "system", "content": self.sys_prompt}] + messages
        
        # Update the graph's state with the full message history
        self.graph.update_state(self.thread_config, {"messages": full_messages})
        
        # Generate a response based on the updated state
        responses = []
        for chunk in self.graph.stream({"messages": full_messages}, config=self.thread_config, stream_mode="values"):
            msg = chunk["messages"][-1]
            responses.append(msg)
        
        # Return the final response content
        return responses[-1].content