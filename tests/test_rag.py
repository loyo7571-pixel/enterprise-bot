import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import app and database dependencies
from main import app
from database import Base, get_db

# 1. Create an IN-MEMORY SQLite database (it lives in RAM, not on disk)
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Override the database dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 3. Create the TestClient
client = TestClient(app)

# 4. Setup and teardown the DB for every test
@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# --- TESTS ---

def test_register_user():
    response = client.post("/register", json={"email": "test@example.com", "password": "password123"})
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}

def test_login_and_ask():
    client.post("/register", json={"email": "test@example.com", "password": "password123"})
    
    login_response = client.post("/login", data={"username": "test@example.com", "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    ask_response = client.post("/ask", json={"question": "What is the vacation policy?"}, headers=headers)
    
    assert ask_response.status_code == 200
    assert "answer" in ask_response.json()

def test_unauthorized_access():
    response = client.post("/ask", json={"question": "Hack the mainframe"})
    assert response.status_code == 401