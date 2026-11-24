import hashlib
import logging
import os
import sqlite3
import threading
from pathlib import Path

import faiss
import numpy as np

from backend.core import config

logger = logging.getLogger(__name__)

DB_DIR = config.DB_DIR
SQLITE_PATH = DB_DIR / 'overcut.sqlite'
FAISS_PATH = DB_DIR / 'overcut.index'


def artifact_hash(image_path: str, metadata: str = "") -> str:
    """Stable content hash used to deduplicate persisted artifacts."""
    digest = hashlib.sha256()
    try:
        with open(image_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        digest.update(str(image_path).encode("utf-8"))
    digest.update(b"\0")
    digest.update(metadata.encode("utf-8"))
    return digest.hexdigest()


class VectorDB:
    def __init__(self, vector_dim: int = 512, db_dir: Path | None = None):
        self.vector_dim = vector_dim
        # Serializes every FAISS + SQLite operation. FAISS reads are not safe
        # while another thread is adding vectors, so search shares this lock.
        self._lock = threading.RLock()

        base_dir = Path(db_dir) if db_dir is not None else None
        self._sqlite_path = base_dir / 'overcut.sqlite' if base_dir else SQLITE_PATH
        self._faiss_path = base_dir / 'overcut.index' if base_dir else FAISS_PATH
        if base_dir:
            base_dir.mkdir(parents=True, exist_ok=True)

        if self._faiss_path.exists():
            logger.info("Loading existing FAISS index from %s", self._faiss_path)
            self.index = faiss.read_index(str(self._faiss_path))
        else:
            logger.info("Initializing new FAISS IndexFlatIP...")
            self.index = faiss.IndexFlatIP(self.vector_dim)

        self._init_sqlite_schema()

    # ── SQLite plumbing ─────────────────────────────────────────────
    def _get_conn(self) -> sqlite3.Connection:
        """Returns a new SQLite connection for the calling thread."""
        return sqlite3.connect(str(self._sqlite_path), timeout=10)

    def _init_sqlite_schema(self):
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS visual_artifacts (
                    id INTEGER PRIMARY KEY,
                    faiss_id INTEGER UNIQUE,
                    session_id TEXT,
                    driver TEXT,
                    image_path TEXT,
                    metadata TEXT,
                    content_hash TEXT
                )
            ''')
            columns = {row[1] for row in conn.execute('PRAGMA table_info(visual_artifacts)')}
            if 'content_hash' not in columns:
                conn.execute('ALTER TABLE visual_artifacts ADD COLUMN content_hash TEXT')
            conn.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_visual_artifacts_hash
                ON visual_artifacts(content_hash)
                WHERE content_hash IS NOT NULL
            ''')
            conn.commit()

    # ── Mutations ───────────────────────────────────────────────────
    def add_embedding(
        self,
        embedding: np.ndarray,
        session_id: str,
        driver: str,
        image_path: str,
        metadata: str,
        content_hash: str | None = None,
    ) -> int:
        """Adds an embedding to FAISS and its metadata to SQLite.

        If ``content_hash`` matches an existing artifact the insert is skipped
        and the existing FAISS id is returned, making ingestion idempotent.
        The in-memory index is not written to disk here; call ``flush()``.
        """
        embedding = np.ascontiguousarray(embedding, dtype=np.float32)
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)

        with self._lock:
            if content_hash:
                with self._get_conn() as conn:
                    row = conn.execute(
                        'SELECT faiss_id FROM visual_artifacts WHERE content_hash = ?',
                        (content_hash,),
                    ).fetchone()
                if row:
                    logger.info("Artifact already indexed (hash %s); skipping", content_hash[:12])
                    return int(row[0])

            faiss_id = self.index.ntotal
            self.index.add(embedding)

            with self._get_conn() as conn:
                conn.execute('''
                    INSERT INTO visual_artifacts
                        (faiss_id, session_id, driver, image_path, metadata, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (faiss_id, session_id, driver, image_path, metadata, content_hash))
                conn.commit()

        logger.info("Added embedding to FAISS (id=%s) and SQLite.", faiss_id)
        return faiss_id

    def flush(self):
        """Atomically persists the in-memory FAISS index to disk."""
        with self._lock:
            tmp_path = self._faiss_path.with_suffix(".index.tmp")
            faiss.write_index(self.index, str(tmp_path))
            os.replace(tmp_path, self._faiss_path)
            logger.info(
                "FAISS index flushed to %s (%s vectors).",
                self._faiss_path,
                self.index.ntotal,
            )

    # ── Reads ───────────────────────────────────────────────────────
    @property
    def count(self) -> int:
        return int(self.index.ntotal)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 3,
        exclude_ids: set[int] | None = None,
        exclude_hashes: set[str] | None = None,
    ):
        """Returns the ``top_k`` most similar artifacts, excluding self-matches."""
        query_embedding = np.ascontiguousarray(query_embedding, dtype=np.float32)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        excluded_ids = exclude_ids or set()
        excluded_hashes = exclude_hashes or set()
        wanted = max(1, top_k)

        with self._lock:
            if self.index.ntotal == 0:
                logger.warning("FAISS index is empty; no precedents available.")
                return []

            # Over-fetch so exclusions (e.g. the query artifact itself) and
            # duplicate legacy rows do not shrink the result set below top_k.
            k = min(
                self.index.ntotal,
                max(wanted * 4, wanted + len(excluded_ids) + len(excluded_hashes)),
            )
            distances, indices = self.index.search(query_embedding, k)

            results = []
            seen = set()
            with self._get_conn() as conn:
                for position, faiss_id in enumerate(indices[0]):
                    if faiss_id == -1 or int(faiss_id) in excluded_ids:
                        continue
                    row = conn.execute(
                        '''SELECT session_id, driver, image_path, metadata, content_hash
                           FROM visual_artifacts WHERE faiss_id = ?''',
                        (int(faiss_id),),
                    ).fetchone()
                    if not row:
                        continue
                    if row[4] and row[4] in excluded_hashes:
                        continue
                    # Collapse duplicate artifacts persisted before content-hash
                    # dedupe existed (identical session/driver/metadata rows).
                    dedupe_key = row[4] or (row[0], row[1], row[3])
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    results.append({
                        "faiss_id": int(faiss_id),
                        "score": float(distances[0][position]),
                        "session_id": row[0],
                        "driver": row[1],
                        "image_path": row[2],
                        "metadata": row[3],
                    })
                    if len(results) >= wanted:
                        break

        return results
