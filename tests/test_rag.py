import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import your FastAPI app and database base
from main import app
from database import Base, get_db
import models

# 1. Create an in-memory SQLite DB for testing (so we don't touch Postgres)
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Override the get_db dependency to use the test DB
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 3. Create the TestClient
client = TestClient(app)

# 4. Setup the database before tests run
@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# --- THE TESTS ---

def test_register_user():
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}

def test_login_and_ask():
    # 1. Register the user first
    client.post("/register", json={"email": "test@example.com", "password": "password123"})
    
    # 2. Login to get the token
    login_response = client.post(
        "/login",
        data={"username": "test@example.com", "password": "password123"} # OAuth2 uses form data
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 3. Ask a question using the token
    headers = {"Authorization": f"Bearer {token}"}
    ask_response = client.post(
        "/ask",
        json={"question": "What is the vacation policy?"},
        headers=headers
    )
    
    # Note: Because we are using real Groq API, this might take a few seconds.
    assert ask_response.status_code == 200
    assert "answer" in ask_response.json()

def test_unauthorized_access():
    # Try to ask a question without a token
    response = client.post("/ask", json={"question": "Hack the mainframe"})
    assert response.status_code == 401 # Unauthorized