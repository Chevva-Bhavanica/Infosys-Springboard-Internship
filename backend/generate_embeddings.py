
import sqlite3
import json
import os
import numpy as np
import faiss

from sentence_transformers import SentenceTransformer

# Configuration
DB_PATH = "data/processed/historical_bugs.db"
OUTPUT_DIR = "data/processed"

INDEX_PATH = os.path.join(OUTPUT_DIR, "bug_chunks.faiss")
METADATA_PATH = os.path.join(OUTPUT_DIR, "bug_metadata.json")

MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 32


def generate_embeddings():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT chunk_id, bug_id, source, project,
               component, chunk_type, chunk_text
        FROM bug_chunks
        ORDER BY bug_id, chunk_type, chunk_id
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No chunks found!")
        return

    print("Total chunks:", len(rows))

    # Extract text and metadata
    texts = []
    metadata = []

    for row in rows:

        chunk_id, bug_id, source, project, component, chunk_type, chunk_text = row

        if not chunk_text or not chunk_text.strip():
            continue

        texts.append(chunk_text)

        metadata.append({
            "chunk_id": chunk_id,
            "bug_id": bug_id,
            "source": source,
            "project": project,
            "component": component,
            "chunk_type": chunk_type,
            "chunk_text": chunk_text
        })

    if not texts:
        print("No valid text chunks found!")
        return

    # Load embedding model
    print("\nLoading Sentence Transformer model...")

    model = SentenceTransformer(MODEL_NAME)

    print("Model loaded successfully.")

    # Generate embeddings
    print("\nGenerating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    print("\nEmbedding generation completed.")
    print("Embedding shape:", embeddings.shape)

    # Create FAISS index
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    # Save FAISS index
    faiss.write_index(index, INDEX_PATH)

    # Save corresponding metadata
    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n================================")
    print("EMBEDDING GENERATION COMPLETED")
    print("================================")

    print("Model:", MODEL_NAME)
    print("Total embeddings:", index.ntotal)
    print("Vector dimensions:", dimension)
    print("FAISS index:", INDEX_PATH)
    print("Metadata:", METADATA_PATH)

    print("================================")


if __name__ == "__main__":
    generate_embeddings()
