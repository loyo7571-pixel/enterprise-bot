import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from main import app

# Create the test client
client = TestClient(app)

def test_health_check():
    """Test that the health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_root_docs():
    """Test that the root /docs endpoint is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200

def test_unauthorized_access():
    """Test that /ask requires authentication."""
    response = client.post("/ask", json={"question": "Hack the mainframe"})
    assert response.status_code == 401