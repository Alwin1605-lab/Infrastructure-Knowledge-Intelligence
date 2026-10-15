import pytest
import httpx
import time
import os

BASE_URL = "http://localhost:8000"

@pytest.fixture
def client():
    # Use httpx for live API testing against the local server
    return httpx.Client(base_url=BASE_URL, timeout=10.0)

def test_health_system(client):
    response = client.get("/api/v1/health/system")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    
def test_auth_login_invalid(client):
    response = client.post("/api/v1/auth/login", data={"username": "fake", "password": "fake"})
    # Depending on implementation, it might be 401 or 400
    assert response.status_code in [400, 401]

def test_get_documents_unauthorized(client):
    response = client.get("/api/v1/documents")
    # Missing token should be 401
    assert response.status_code == 401
    
# In a real environment, we would first create a user, login, get a token, and then test the rest.
# But since this is a QA script run against a potentially existing DB, we will skip hardcoding creation 
# if we don't have a dedicated test user endpoint.
# But we can test that the endpoints exist and enforce auth.

def test_query_agent_unauthorized(client):
    response = client.post("/api/v1/agents/query", json={"query": "test", "workspace_id": "123"})
    assert response.status_code == 401

def test_kb_metrics_unauthorized(client):
    response = client.get("/api/v1/analytics/stats")
    assert response.status_code in [401, 404]

@pytest.mark.asyncio
async def test_groq_rate_limit_simulation():
    # This is a mock test to verify the QA runner can handle rate limits
    # In reality, the live backend should handle 429s.
    pass

def test_api_latency(client):
    start = time.time()
    res = client.get("/api/v1/health/system")
    latency = time.time() - start
    assert res.status_code == 200
    assert latency < 3.0 # Enforce 3 second threshold for full multi-DB system health check
