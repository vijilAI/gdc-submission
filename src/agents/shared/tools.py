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

'''
Shared tools
'''

import os
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field
from typing import Type
from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_community.llms import OpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

# Step 1: Load markdown files and split them into chunks
def load_markdown_files(directory):
    docs = []
    for root, dirs, filenames in os.walk(directory):
        for file_name in filenames:
            if file_name.endswith('.md') or file_name.endswith(".txt"):
                file_path = os.path.join(root, file_name)
                loader = TextLoader(file_path, encoding='utf-8')
                docs.extend(loader.load())
    return docs

# Step 2: Create vector store (using FAISS)
def create_vector_store(documents):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    texts = text_splitter.split_documents(documents)
    
    # Embeddings
    embeddings = OpenAIEmbeddings()
    
    # Create FAISS index
    vector_store = FAISS.from_documents(texts, embeddings)
    return vector_store


class MarkdownRetriever():

    def __init__(self, retriever : VectorStoreRetriever):
        self.retriever = retriever

    def query(self, query):
        results = self.retriever.invoke(query)
        return [result.page_content for result in results]
    
    # def _run(self, query):
    #     return self.__call(query)

    # async def _arun(self, query):
    #     """Asynchronous version of retrieving markdown documents."""
    #     return self._call(query)


# Step 4: Main function to initialize everything
def initialize_markdown_retriever(folder_path : str, k : int):
    # Load markdown documents
    documents = load_markdown_files(folder_path)
    
    # Create vector store
    vector_store = create_vector_store(documents)
    
    # Create retriever from vector store
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})
    
    # Initialize the LangChain tool
    markdown_retriever = MarkdownRetriever(retriever=retriever)
    
    return markdown_retriever

def create_search_tool():
    tool = TavilySearchResults(max_results=5)
    return tool
