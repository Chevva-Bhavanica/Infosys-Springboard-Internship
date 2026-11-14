
import os
import json
import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

DB_PATH = "data/processed/historical_bugs.db"
INDEX_PATH = "data/processed/bug_chunks.faiss"
METADATA_PATH = "data/processed/bug_metadata.json"

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5


def search_similar_bugs(query):
    if not query.strip():
        print("Please enter a bug description.")
        return

    # Load the embedding model
    print("\nLoading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    # Load FAISS index
    if not os.path.exists(INDEX_PATH):
        print("FAISS index not found. Run generate_embeddings.py first.")
        return

    index = faiss.read_index(INDEX_PATH)

    # Load metadata
    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    if index.ntotal != len(metadata):
        print("Error: FAISS index and metadata counts do not match.")
        return

    # Generate query embedding
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    query_embedding = np.asarray(query_embedding, dtype=np.float32)

    # Search similar chunks
    scores, indices = index.search(query_embedding, TOP_K)

    print("\n" + "=" * 60)
    print("SIMILAR HISTORICAL BUGS")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for rank, (score, idx) in enumerate(
        zip(scores[0], indices[0]), start=1
    ):
        if idx < 0:
            continue

        item = metadata[idx]

        cursor.execute(
            """
            SELECT bug_id, summary, description
            FROM historical_bugs
            WHERE bug_id = ?
            LIMIT 1
            """,
            (item["bug_id"],)
        )

        bug = cursor.fetchone()

        print(f"\nResult #{rank}")
        print("-" * 60)
        print("Bug ID:", item["bug_id"])
        print("Project:", item.get("project"))
        print("Component:", item.get("component"))
        print("Chunk type:", item.get("chunk_type"))
        print("Similarity score:", round(float(score), 4))

        if bug:
            print("Summary:", bug[1])
            print("Description:", (bug[2] or "")[:500])

        print("\nMatching text:")
        print((item.get("chunk_text") or "")[:700])

    conn.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("INTELLIGENT BUG DIAGNOSIS PLATFORM")
    print("Semantic Historical Bug Search")

    while True:
        query = input(
            "\nEnter a new bug description (or type exit): "
        ).strip()

        if query.lower() == "exit":
            print("Search ended.")
            break

        search_similar_bugs(query)
