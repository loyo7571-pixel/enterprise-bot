from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

def test_retriever():
    embeddings=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordb=Chroma(persist_directory="dev", embedding_function=embeddings)
    retriever=vectordb.as_retriever(search_kwargs={"k":2})
    results=retriever.invoke("what is vacation policy")

    assert len(results) == 2
    assert results[0].page_content is not None

def test_prompt():
    prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Answer the question using ONLY this context:\n{context}\n\nIf the answer is not in the context, say 'I don't know based on the provided documents.'"),
    ("human", "{question}")    
    ])
    assert "context" in prompt.input_variables
    assert "question" in prompt.input_variables
    formatted = prompt.format(context="Test context", question="Test question")
    assert "I don't know based on the provided documents" in formatted



