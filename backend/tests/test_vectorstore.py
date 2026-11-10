"""
Unit Tests for ChromaDB Vector Store (Phase 2)
"""

import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from vectorstore import (
    initialize_vector_store,
    get_collection_status,
    retrieve_policy_clauses,
    parse_policy_clauses_file,
)


def test_parse_policy_clauses_file():
    clauses = parse_policy_clauses_file()
    assert len(clauses) >= 4
    clause_ids = [c["clause_id"] for c in clauses]
    assert "STAR-PREMIER-ROOM-001" in clause_ids
    assert "STAR-PREMIER-WAIT-002" in clause_ids
    assert "STAR-PREMIER-PED-001" in clause_ids
    assert "STAR-PREMIER-MODERN-014" in clause_ids


def test_initialize_vector_store_and_count():
    col = initialize_vector_store()
    assert col.count() >= 4

    status = get_collection_status()
    assert status["collection_name"] == "bimasakshi_policy_clauses"
    assert status["indexed_documents_count"] >= 4
    assert status["insurer"] == "Star Health and Allied Insurance Company Limited"
    assert status["uin"] == "SHAHLIP22226V012122"
    assert status["document_version"] == "POL / SHP / V.6 / 2023"


def test_idempotent_indexing():
    # Calling initialize_vector_store again should not duplicate documents
    col1 = initialize_vector_store()
    assert col1.count() >= 4
    col2 = initialize_vector_store()
    assert col2.count() == col1.count()


def test_retrieve_room_rent_clause():
    query = "What is the room rent limit and when does proportionate deduction apply?"
    results = retrieve_policy_clauses(query, top_k=1)
    assert len(results) == 1
    top = results[0]
    assert top["clause_id"] == "STAR-PREMIER-ROOM-001"
    assert "Room Rent" in top["clause_title"]
    assert top["source_page"] == "3"
    assert "proportionate" in top["retrieved_text"].lower()


def test_retrieve_kidney_calculi_clause():
    query = "What is the waiting period for kidney calculi treatment?"
    results = retrieve_policy_clauses(query, top_k=1)
    assert len(results) == 1
    top = results[0]
    assert top["clause_id"] == "STAR-PREMIER-WAIT-002"
    assert "Code - Excl 02" in top["clause_title"]
    assert top["source_page"] == "6"
    assert "kidney calculi" in top["retrieved_text"].lower()


def test_retrieve_ped_clause():
    query = "What is the waiting period for pre-existing diseases?"
    results = retrieve_policy_clauses(query, top_k=1)
    assert len(results) == 1
    top = results[0]
    assert top["clause_id"] == "STAR-PREMIER-PED-001"
    assert "Code - Excl 01" in top["clause_title"]
    assert top["source_page"] == "6"
    assert "pre-existing" in top["retrieved_text"].lower()


def test_empty_or_whitespace_query():
    assert retrieve_policy_clauses("") == []
    assert retrieve_policy_clauses("   ") == []

