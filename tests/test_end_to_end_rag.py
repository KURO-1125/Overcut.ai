from pathlib import Path

import pytest

from backend.ai.diagnostics_service import DiagnosticsService
from backend.ai.schema import AnomalySeverity
from backend.vector_store.db import VectorDB, artifact_hash
from backend.vector_store.engine import VectorEngine

BASELINE_IMAGE = "data/generated_roi/baseline_baku_lockup_44.png"
BASELINE_META = "2021 Baku GP Driver 44 front left tire lockup braking into turn 1"


@pytest.fixture(scope="module")
def engine():
    return VectorEngine(device="cpu")


@pytest.fixture()
def seeded_db(tmp_path, engine):
    db = VectorDB(db_dir=tmp_path)
    embedding = engine.embed_artifact(BASELINE_IMAGE, BASELINE_META)
    db.add_embedding(
        embedding=embedding,
        session_id="2021_Baku_GP",
        driver="44",
        image_path=BASELINE_IMAGE,
        metadata=BASELINE_META,
        content_hash=artifact_hash(BASELINE_IMAGE, BASELINE_META),
    )
    return db


def test_retrieval_never_returns_the_query_artifact(tmp_path, engine):
    """Regression: the analyzed artifact must not be its own top-1 precedent."""
    image = Path(BASELINE_IMAGE)
    assert image.exists(), "Baseline crop image must exist"

    db = VectorDB(db_dir=tmp_path)
    query_meta = BASELINE_META + " (live query)"
    query_embedding = engine.embed_artifact(str(image), query_meta)
    query_hash = artifact_hash(str(image), query_meta)

    # Simulate the old pipeline order: persist first, then search.
    db.add_embedding(
        embedding=query_embedding,
        session_id="live_session",
        driver="44",
        image_path=str(image),
        metadata=query_meta,
        content_hash=query_hash,
    )

    assert db.search(query_embedding, top_k=3, exclude_hashes={query_hash}) == []
    all_results = db.search(query_embedding, top_k=3)
    assert len(all_results) == 1
    assert all_results[0]["session_id"] == "live_session"

    # Persisting the same content twice is idempotent.
    duplicate_id = db.add_embedding(
        embedding=query_embedding,
        session_id="duplicate",
        driver="44",
        image_path=str(image),
        metadata=query_meta,
        content_hash=query_hash,
    )
    assert duplicate_id == all_results[0]["faiss_id"]
    assert db.count == 1


def test_end_to_end_vector_search_and_diagnostics(seeded_db, engine):
    image_path = BASELINE_IMAGE
    assert Path(image_path).exists(), "Baseline crop image must exist"

    query_meta = BASELINE_META + " telemetry slice 60s-75s"
    query_emb = engine.embed_artifact(image_path, query_meta)
    assert query_emb.shape == (1, 512)

    results = seeded_db.search(query_emb, top_k=3, exclude_hashes={artifact_hash(image_path, query_meta)})
    assert len(results) == 1, "FAISS should return the seeded historical precedent"

    top_match = results[0]
    assert top_match["session_id"] == "2021_Baku_GP"
    assert top_match["score"] > 0.80

    telemetry_summary = {
        "driver": "44",
        "min_speed": 105.0,
        "max_speed": 312.0,
        "max_brake": 100,
        "min_throttle": 0,
        "duration_seconds": 2.2,
    }

    report = DiagnosticsService().analyze_anomaly(
        image_path=image_path,
        telemetry_summary=telemetry_summary,
        historical_matches=results,
        domain="MOTORSPORT_F1",
    )

    assert report.domain == "MOTORSPORT_F1"
    assert report.severity == AnomalySeverity.HIGH
    assert report.confidence_score >= 0.85
    assert len(report.historical_precedents) == 1
    assert report.historical_precedents[0].session_id == "2021_Baku_GP"
