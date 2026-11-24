import pytest
import numpy as np
import os
import faiss
import backend.vector_store.db as db_module

@pytest.fixture(autouse=True)
def isolated_dbs(tmp_path, monkeypatch):
    """
    Setup logic to ensure we test with a fresh database in a temporary directory
    and don't permanently corrupt the primary local databases.
    """
    temp_sqlite = tmp_path / 'test_overcut.sqlite'
    temp_faiss = tmp_path / 'test_overcut.index'
    
    monkeypatch.setattr(db_module, 'SQLITE_PATH', temp_sqlite)
    monkeypatch.setattr(db_module, 'FAISS_PATH', temp_faiss)
    
    yield

def test_faiss_sqlite_integration():
    """
    Task 4.4: Integration test calculating Recall for the vector search.
    Ensures that when we insert vectors, searching for a slightly noisy version
    of a vector correctly retrieves the original structural match from SQLite.
    """
    db = db_module.VectorDB(vector_dim=512)
    
    # 1. Generate 50 random normalized baseline vectors (simulating historical anomalies)
    np.random.seed(42)
    baseline_vectors = np.random.rand(50, 512).astype(np.float32)
    faiss.normalize_L2(baseline_vectors)
    
    # 2. Insert them into the hybrid FAISS/SQLite database
    for i in range(50):
        db.add_embedding(
            embedding=baseline_vectors[i],
            session_id=f"session_{i}",
            driver="VER" if i % 2 == 0 else "HAM",
            image_path=f"/fake/path/{i}.png",
            metadata=f"Metadata {i}"
        )
        
    assert db.index.ntotal == 50
    
    # 3. Simulate a new, incoming query that is extremely similar to vector #15
    # (e.g., a lockup anomaly that visually resembles historical lockup #15)
    target_vector = baseline_vectors[15].copy()
    
    # Add a tiny amount of noise
    noise = np.random.normal(0, 0.01, 512).astype(np.float32)
    query_vector = target_vector + noise
    faiss.normalize_L2(query_vector.reshape(1, -1))
    
    # 4. Search
    results = db.search(query_vector, top_k=3)
    
    # 5. Verify Recall@3
    assert len(results) == 3
    
    # Check if the target vector (ID 15) is within the Top 3 retrieved results
    retrieved_ids = [res['faiss_id'] for res in results]
    assert 15 in retrieved_ids, "Recall@3 failed: The mathematically similar structural precedent was not retrieved."
    
    # Validate SQLite rehydration is intact
    top_result = results[0]
    assert top_result['session_id'].startswith("session_")
    assert top_result['image_path'].startswith("/fake/path/")
    assert "score" in top_result


def test_search_collapses_legacy_duplicate_artifacts():
    """Rows persisted before content-hash dedupe existed must not fill every slot."""
    db = db_module.VectorDB(vector_dim=512)
    np.random.seed(7)
    vectors = np.random.rand(6, 512).astype(np.float32)
    faiss.normalize_L2(vectors)

    for _ in range(3):
        db.add_embedding(vectors[0], "2025_monaco_Q", "Lewis Hamilton", "/fake/dup.png", "slice 15.0s-25.0s")
    db.add_embedding(vectors[5], "2024_monza_R", "Charles Leclerc", "/fake/other.png", "slice 40.0s-48.0s")

    results = db.search(vectors[0], top_k=3)

    assert len(results) == 2
    assert {r['session_id'] for r in results} == {"2025_monaco_Q", "2024_monza_R"}
