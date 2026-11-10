"""
API Integration Tests for FastAPI Backend (Phase 2)
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "BimaSakshi Backend"
    assert data["status"] == "ok"
    assert data["vector_store_initialized"] is True


def test_policy_status_endpoint(client):
    response = client.get("/api/policy/status")
    assert response.status_code == 200
    data = response.json()
    assert data["collection_name"] == "bimasakshi_policy_clauses"
    assert data["indexed_documents_count"] >= 3
    assert data["policy_name"] == "Star Health Premier Insurance Policy"
    assert data["insurer"] == "Star Health and Allied Insurance Company Limited"
    assert data["uin"] == "SHAHLIP22226V012122"
    assert data["document_version"] == "POL / SHP / V.6 / 2023"


def test_policy_search_room_rent(client):
    payload = {
        "query": "What is the room rent limit and when does proportionate deduction apply?",
        "top_k": 3,
    }
    response = client.post("/api/policy/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_retrieved"] == 3
    assert len(data["results"]) == 3
    
    top = data["results"][0]
    assert top["clause_id"] == "STAR-PREMIER-ROOM-001"
    assert top["source_page"] == "3"
    assert top["policy_info"]["uin"] == "SHAHLIP22226V012122"
    assert top["distance"] >= 0.0


def test_policy_search_kidney_calculi(client):
    payload = {
        "query": "What is the waiting period for kidney calculi treatment?",
        "top_k": 1,
    }
    response = client.post("/api/policy/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_retrieved"] == 1
    top = data["results"][0]
    assert top["clause_id"] == "STAR-PREMIER-WAIT-002"
    assert top["source_page"] == "6"


def test_policy_search_ped(client):
    payload = {
        "query": "What is the waiting period for pre-existing diseases?",
        "top_k": 1,
    }
    response = client.post("/api/policy/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_retrieved"] == 1
    top = data["results"][0]
    assert top["clause_id"] == "STAR-PREMIER-PED-001"
    assert top["source_page"] == "6"


def test_policy_search_empty_query(client):
    # Empty string
    response = client.post("/api/policy/search", json={"query": ""})
    assert response.status_code == 422

    # Whitespace only
    response = client.post("/api/policy/search", json={"query": "     "})
    assert response.status_code == 422


def test_policy_search_invalid_top_k(client):
    # top_k < 1
    response = client.post("/api/policy/search", json={"query": "test query", "top_k": 0})
    assert response.status_code == 422

    # top_k > 10
    response = client.post("/api/policy/search", json={"query": "test query", "top_k": 50})
    assert response.status_code == 422

