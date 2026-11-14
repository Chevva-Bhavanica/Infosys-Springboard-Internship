
import json
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

DB_PATH = DATA_DIR / "historical_bugs.db"
INDEX_PATH = DATA_DIR / "bug_chunks.faiss"
METADATA_PATH = DATA_DIR / "bug_metadata.json"

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def load_model():
    return SentenceTransformer(MODEL_NAME)


@lru_cache(maxsize=1)
def load_index():
    if not INDEX_PATH.exists():
        raise FileNotFoundError("FAISS index not found.")

    index = faiss.read_index(str(INDEX_PATH))

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    if index.ntotal != len(metadata):
        raise ValueError("FAISS index and metadata mismatch.")

    return index, metadata


def find_similar_bugs(query, top_k=5):

    if not query or not query.strip():
        return []

    index, metadata = load_index()
    model = load_model()

    query_vector = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    query_vector = np.asarray(
        query_vector,
        dtype=np.float32
    )

    search_count = min(index.ntotal, max(50, top_k * 10))

    scores, indices = index.search(
        query_vector,
        search_count
    )

    unique_bugs = {}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        for score, idx in zip(scores[0], indices[0]):

            if idx < 0:
                continue

            item = metadata[int(idx)]
            bug_id = str(item["bug_id"])

            # Keep only the highest-scoring chunk per bug.
            if bug_id in unique_bugs:
                continue

            row = conn.execute(
                """
                SELECT bug_id, summary, description,
                       project, component, severity,
                       status, issue_url
                FROM historical_bugs
                WHERE bug_id = ?
                LIMIT 1
                """,
                (bug_id,)
            ).fetchone()

            if row is None:
                continue

            unique_bugs[bug_id] = {
                "historical_bug_id": bug_id,
                "summary": row["summary"] or "",
                "description": row["description"] or "",
                "project": row["project"] or "",
                "component": row["component"] or "",
                "severity": row["severity"] or "",
                "status": row["status"] or "",
                "issue_url": row["issue_url"] or "",
                "matched_chunk_type": item.get("chunk_type", ""),
                "similarity_score": round(float(score), 4)
            }

            if len(unique_bugs) >= top_k:
                break

    finally:
        conn.close()

    return list(unique_bugs.values())
