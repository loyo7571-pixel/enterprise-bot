import streamlit as st
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

@st.cache_resource
def load_model():
   model= HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
   vectordb=Chroma(persist_directory="dev", embedding_function=model)
   return vectordb

if "messages" not in st.session_state:
   st.session_state.messages=[]

for msg in st.session_state.messages:
   with st.chat_message(msg["role"]):
      st.markdown(msg["content"])

user_query=st.chat_input("ask smtg about your data")

if user_query:
   with st.chat_message("user"):
      st.markdown(user_query)

   st.session_state.messages.append({"role":"user", "content":user_query})

   vectordb=load_model()
   retriever=vectordb.as_retriever(search_kwargs={"k":2})

   prompt=ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Answer the question using ONLY this context:\n{context}\n\nIf the answer is not in the context, say 'I don't know based on the provided documents.'"),
            ("human", "{question}")
    ])

   model=ChatGroq(model="openai/gpt-oss-20b")

   rag_chain= ( 
      {"context":retriever, "question":RunnablePassthrough()}
      | prompt
      | model
      | StrOutputParser()
    )

   with st.spinner("Thinking..."):
      ai_response=rag_chain.invoke(user_query)
   with st.chat_message("assistant"):
       st.markdown(ai_response)
   st.session_state.messages.append({"role": "assistant", "content": ai_response})
