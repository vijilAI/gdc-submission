# Copyright 2025 Vijil, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# The vijil trademark is owned by Vijil Inc.

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from agents.shared.types import State
from langgraph.prebuilt import create_react_agent
from typing import Optional
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
    
    # async version of chat
    async def chat_async(self, prompt: str):
        query_msg = {"messages": [("user", prompt)]}
        responses = []
        async for chunk in self.graph.astream(query_msg, config=self.thread_config, stream_mode="values"):
            msg = chunk["messages"][-1]
            responses.append(msg)
        return responses[-1].content

