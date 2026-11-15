import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import timedelta
from groq import Groq
from fastapi import UploadFile, File
import shutil
import uuid

# Internal imports
from database import engine, get_db
import models
import auth
import semantic_cache

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

# 1. Create DB Tables on startup (if they don't exist)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Enterprise AI API")

# 2. Global cache for RAG chain (Lazy loading)
print("Loading global embedding model...")
GLOBAL_EMBEDDINGS = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_rag_chain(user_id: int):
        print("Loading RAG chain...")
        vectordb = Chroma(persist_directory="dev", embedding_function=GLOBAL_EMBEDDINGS)
        retriever = vectordb.as_retriever(search_kwargs={
            "k": 2,
            "filter": {"user_id": user_id}
            })
        model = ChatGroq(model="openai/gpt-oss-20b", temperature=0.1)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. Answer using ONLY this context:\n{context}\n\nIf the answer is not in the context, say 'I don't know based on the provided documents.'"),
            ("human", "{question}")
        ])
        chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt | model | StrOutputParser()
        )
        return chain

# --- PYDANTIC SCHEMAS ---
class UserCreate(BaseModel):
    email: str
    password: str

class QuestionRequest(BaseModel):
    question: str

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/register", status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password and save
    hashed_pw = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm expects 'username' but we use it as 'email'
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT Token
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- PROTECTED ENDPOINTS ---

@app.post("/ask")
def ask_question(
    request: QuestionRequest, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user) # <--- PROTECTED!
):
    try:
        cached_response = semantic_cache.get_cached_answer(request.question)
        if cached_response:
            return {"question": request.question, "answer": cached_response, "source": "semantic_cache"}
        
         # 1. Get the answer from RAG
        chain = get_rag_chain(current_user.id)
        answer = chain.invoke(request.question)

        semantic_cache.set_cached_answer(request.question, answer)

        # 2. Save to ChatHistory in Postgres
        new_chat = models.ChatHistory(
            question=request.question, 
            answer=answer, 
            user_id=current_user.id
        )
        db.add(new_chat)
        db.commit()
        
        return {"question": request.question, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user) # <--- PROTECTED!
):
    # Fetch all chats for this specific user
    chats = db.query(models.ChatHistory).filter(models.ChatHistory.user_id == current_user.id).all()
    return {"history": chats}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/tokens-left")
def get_tokens_left():
    try:
        # Initialize the raw Groq client
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Make a tiny 1-token request to read the headers
        response = client.chat.completions.with_raw_response.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1
        )
        
        # Extract the headers
        headers = response.headers
        
        return {
            "remaining_requests_today": headers.get("x-ratelimit-remaining-requests"),
            "remaining_tokens_minute": headers.get("x-ratelimit-remaining-tokens"),
            "limit_tokens_minute": headers.get("x-ratelimit-limit-tokens")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # 1. Save the uploaded file to a temporary location
        file_location = f"./tmp_{uuid.uuid4()}_{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Load the document based on file type
        if file.filename.endswith(".pdf"):
            loader = PyPDFLoader(file_location)
        else:
            loader = TextLoader(file_location)
            
        docs = loader.load()
        
        # 3. Split the text into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(docs)
        
        # 4. Add to ChromaDB (this uses the existing collection)
        # We need to load the embedding model and the vectorstore again
        vectorstore = Chroma(persist_directory="dev", embedding_function=GLOBAL_EMBEDDINGS)

        for chunk in chunks:
            chunk.metadata["user_id"] = current_user.id
        # Add chunks to the DB
        vectorstore.add_documents(chunks)
        
        # 5. Clean up the temporary file
        os.remove(file_location)
        
        return {"message": f"Successfully uploaded and ingested {file.filename} with {len(chunks)} chunks."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear")
def clear_user_data(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # 1. Clear Postgres Chat History for this user
        db.query(models.ChatHistory).filter(models.ChatHistory.user_id == current_user.id).delete()
        db.commit()

        # 2. Clear THIS USER'S data from ChromaDB
        # We have to query and delete by the metadata user_id
        vectordb = Chroma(persist_directory="dev", embedding_function=GLOBAL_EMBEDDINGS)
        # Delete where metadata user_id == current_user.id
        vectordb._collection.delete(where={"user_id": current_user.id})

        return {"message": "Your data has been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))