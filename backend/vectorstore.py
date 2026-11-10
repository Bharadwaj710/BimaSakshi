"""
Vector Store Implementation for BimaSakshi (Phase 2)
----------------------------------------------------
In-memory ChromaDB vector store using EphemeralClient to ingest and retrieve
authentic policy clauses from Star Health Premier Insurance Policy.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

logger = logging.getLogger("bimasakshi.vectorstore")

# Paths
BACKEND_DIR = Path(__file__).resolve().parent
DATA_PATH = BACKEND_DIR / "data" / "policy_clauses.md"

COLLECTION_NAME = "bimasakshi_policy_clauses"

# Global module state for in-memory ChromaDB
_client: Optional[ClientAPI] = None
_collection: Optional[Collection] = None
_embedding_fn: Optional[Any] = None


def get_embedding_function() -> Any:
    """
    Returns ChromaDB's default ONNX-based embedding function (all-MiniLM-L6-v2, 384 dim).
    Loads from local cache without downloading large external models.
    """
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return _embedding_fn


def parse_policy_clauses_file(file_path: Path = DATA_PATH) -> List[Dict[str, Any]]:
    """
    Parses policy clauses from data/policy_clauses.md.
    Extracts structured clause records containing authentic policy excerpts and metadata.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Policy clauses data file not found at: {file_path}")

    content = file_path.read_text(encoding="utf-8")

    # Extract the embedded machine-readable data block
    start_tag = "<!-- MACHINE_READABLE_DATA_START"
    end_tag = "MACHINE_READABLE_DATA_END -->"

    if start_tag in content and end_tag in content:
        start_idx = content.index(start_tag) + len(start_tag)
        end_idx = content.index(end_tag)
        json_str = content[start_idx:end_idx].strip()
        clauses: List[Dict[str, Any]] = json.loads(json_str)
        return clauses

    raise ValueError(f"Could not locate structured clause data in {file_path}")


def initialize_vector_store() -> Collection:
    """
    Initializes ChromaDB EphemeralClient, creates/resets the collection,
    and indexes the authentic policy clauses idempotently.
    Must be called during application startup.
    """
    global _client, _collection

    logger.info("Initializing in-memory ChromaDB EphemeralClient...")
    _client = chromadb.EphemeralClient()
    emb_fn = get_embedding_function()

    # Create or get collection with cosine/l2 distance
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=emb_fn,
        metadata={"description": "Star Health Premier Insurance Policy Clauses"},
    )

    clauses = parse_policy_clauses_file()

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for clause in clauses:
        clause_id = clause["clause_id"]
        # Rich document representation for high-fidelity semantic similarity
        doc_text = (
            f"Clause ID: {clause['clause_id']}\n"
            f"Title: {clause['clause_title']}\n"
            f"Section: {clause['section_code']}\n"
            f"Explanation: {clause['explanation']}\n\n"
            f"Exact Policy Excerpt:\n{clause['exact_excerpt']}"
        )

        metadata = {
            "clause_id": clause["clause_id"],
            "insurer": clause["insurer"],
            "product_name": clause["product_name"],
            "uin": clause["uin"],
            "document_version": clause["document_version"],
            "section_code": clause["section_code"],
            "page_number": clause["page_number"],
            "pdf_url": clause["pdf_url"],
            "clause_title": clause["clause_title"],
            "explanation": clause["explanation"],
        }

        ids.append(clause_id)
        documents.append(doc_text)
        metadatas.append(metadata)

    # Idempotent upsert: existing IDs are replaced, new ones added
    _collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info(
        f"Indexed {len(ids)} policy clauses into collection '{COLLECTION_NAME}'."
    )
    return _collection


def get_collection() -> Collection:
    """Returns the current collection, initializing it if necessary."""
    global _collection
    if _collection is None:
        _collection = initialize_vector_store()
    return _collection


def get_collection_status() -> Dict[str, Any]:
    """Returns metadata and document count of the policy vector store."""
    col = get_collection()
    count = col.count()

    # Read base policy metadata from the first clause
    clauses = parse_policy_clauses_file()
    sample = clauses[0] if clauses else {}

    return {
        "collection_name": COLLECTION_NAME,
        "indexed_documents_count": count,
        "policy_name": sample.get("product_name", "Star Health Premier Insurance Policy"),
        "insurer": sample.get("insurer", "Star Health and Allied Insurance Company Limited"),
        "uin": sample.get("uin", "SHAHLIP22226V012122"),
        "document_version": sample.get("document_version", "POL / SHP / V.6 / 2023"),
    }


def retrieve_policy_clauses(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Performs semantic retrieval against the in-memory policy clause collection.
    
    Args:
        query: User search query or question.
        top_k: Number of relevant clauses to retrieve (1 to 10).
        
    Returns:
        List of matching clause dictionaries with metadata, excerpt, and distance score.
    """
    if not query or not query.strip():
        return []

    query = query.strip()
    top_k = max(1, min(10, top_k))

    col = get_collection()
    count = col.count()
    if count == 0:
        return []

    n_results = min(top_k, count)
    results = col.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: List[Dict[str, Any]] = []
    if not results or not results["ids"] or not results["ids"][0]:
        return retrieved

    ids = results["ids"][0]
    docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
    metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
    distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

    for cid, doc, meta, dist in zip(ids, docs, metas, distances):
        retrieved.append({
            "clause_id": cid,
            "clause_title": meta.get("clause_title", ""),
            "retrieved_text": doc,
            "source_page": str(meta.get("page_number", "")),
            "distance": round(float(dist), 4),
            "policy_info": {
                "insurer": meta.get("insurer", ""),
                "product_name": meta.get("product_name", ""),
                "uin": meta.get("uin", ""),
                "document_version": meta.get("document_version", ""),
                "section_code": meta.get("section_code", ""),
                "pdf_url": meta.get("pdf_url", ""),
            },
        })

    return retrieved


def retrieve_policy_clauses_multi(queries: List[str], top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Performs multi-query semantic retrieval across multiple decomposed intent queries.
    Deduplicates results by clause_id and retains the minimum (best) distance score.
    Returns results sorted by distance ascending.
    """
    if not queries:
        return []

    valid_queries = [q.strip() for q in queries if q and q.strip()]
    if not valid_queries:
        return []

    best_matches: Dict[str, Dict[str, Any]] = {}

    for q in valid_queries:
        matches = retrieve_policy_clauses(query=q, top_k=top_k)
        for m in matches:
            cid = m["clause_id"]
            if cid not in best_matches or m["distance"] < best_matches[cid]["distance"]:
                best_matches[cid] = m

    sorted_matches = sorted(best_matches.values(), key=lambda x: x["distance"])
    return sorted_matches[:top_k]

