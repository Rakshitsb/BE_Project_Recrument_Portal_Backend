"""
Vector Store — ChromaDB In-Memory + MongoDB Source of Truth
============================================================
Architecture pattern:
  - MongoDB (jobs collection) is the PERSISTENT source of truth.
    When HR finalises a JD, two fields are written to the document:
      • jd_embedding   : list[float]   — 384-dim all-MiniLM-L6-v2 vector
      • embedding_model: str           — "all-MiniLM-L6-v2"

  - ChromaDB runs PURELY IN-MEMORY (chromadb.Client(), no persist_directory).
    At server startup, build_chroma_collection() re-hydrates the in-memory
    index from the already-persisted MongoDB vectors.  This means Render free-
    tier redeploys lose nothing — MongoDB Atlas keeps the raw floats safe.

  - No new MongoDB collection is needed; only the existing jobs collection is
    updated.

New dependencies (collected by Prompt 9 into requirements.txt):
  chromadb, sentence-transformers, torch (cpu)
"""

import asyncio
import logging
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from db.collections import JOBS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons — loaded ONCE, reused across all requests.
# SentenceTransformer initialisation is expensive (~1-2 s); never do it per-
# request.
# ---------------------------------------------------------------------------
_MODEL_NAME: str = "all-MiniLM-L6-v2"
_COLLECTION_NAME: str = "job_jds"

_model: SentenceTransformer = SentenceTransformer(_MODEL_NAME)
_chroma_client: chromadb.Client = chromadb.Client()          # pure in-memory
_collection: chromadb.Collection = _chroma_client.get_or_create_collection(
    name=_COLLECTION_NAME
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def build_chroma_collection(db: Any) -> None:
    """Re-hydrate the in-memory ChromaDB collection from MongoDB at startup.

    Queries every job document that already has a persisted jd_embedding and
    upserts it into the in-memory collection.  Safe to call multiple times
    (ChromaDB upsert is idempotent).

    Args:
        db: Motor async database instance (passed from the FastAPI lifespan).
    """
    cursor = db[JOBS].find(
        {"jd_embedding": {"$exists": True, "$ne": None}},
        {"_id": 1, "title": 1, "jd_embedding": 1},
    )

    ids: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict] = []

    async for job in cursor:
        job_id = str(job["_id"])
        ids.append(job_id)
        embeddings.append(job["jd_embedding"])
        metadatas.append({"job_id": job_id, "title": job.get("title", "")})

    if ids:
        _collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    print(f"[VectorStore] Rebuilt with {len(ids)} jobs")  # noqa: T201


async def upsert_job_embedding(db: Any, job_id: str, jd_text: str) -> list[float]:
    """Generate an embedding for jd_text, persist to MongoDB, and upsert into ChromaDB.

    The CPU-bound model.encode() call is offloaded to a thread-pool executor
    so it does not block the asyncio event loop.

    Args:
        db:       Motor async database instance.
        job_id:   String representation of the job's MongoDB ObjectId.
        jd_text:  Raw text of the job description to embed.

    Returns:
        The generated embedding as a plain list[float].
    """
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _model.encode, jd_text)
    embedding: list[float] = raw.tolist()

    # Upsert into in-memory ChromaDB
    _collection.upsert(
        ids=[job_id],
        embeddings=[embedding],
        metadatas=[{"job_id": job_id, "title": ""}],
    )

    # Persist back to MongoDB jobs collection
    from bson import ObjectId

    await db[JOBS].update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"jd_embedding": embedding, "embedding_model": _MODEL_NAME}},
    )

    return embedding


async def delete_job_embedding(job_id: str) -> None:
    """Remove a job from the in-memory ChromaDB collection.

    Does NOT touch MongoDB — job document deletion is the responsibility of the
    jobs module.  Silently ignores missing ids.

    Args:
        job_id: String representation of the job's MongoDB ObjectId.
    """
    try:
        _collection.delete(ids=[job_id])
    except Exception:  # noqa: BLE001
        pass


async def query_similar_chunks(
    job_id: str, query_text: str, n_results: int = 5
) -> list[dict]:
    """Search ChromaDB for the n_results nearest-neighbour job descriptions.

    Used by the RAG chatbot (Prompt 3) to build retrieval context.

    Args:
        job_id:     The requesting job's id (reserved for future filtering).
        query_text: Free-text query to embed and search against.
        n_results:  Number of nearest neighbours to return.

    Returns:
        List of dicts: [{"job_id": str, "title": str, "distance": float}]
        Returns an empty list if the collection is empty or the query fails.
    """
    try:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _model.encode, query_text)
        query_embedding: list[float] = raw.tolist()

        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "distances"],
        )

        output: list[dict] = []
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for meta, dist in zip(metadatas, distances):
            output.append(
                {
                    "job_id": meta.get("job_id", ""),
                    "title": meta.get("title", ""),
                    "distance": float(dist),
                }
            )
        return output
    except Exception as exc:  # noqa: BLE001
        logger.warning("[VectorStore] query_similar_chunks failed: %s", exc)
        return []


def get_embedding_for_text(text: str) -> list[float]:
    """Synchronous helper — encode a text string to a list[float] embedding.

    Used by the SBERT skill matcher (Prompt 8).  Runs on the calling thread;
    call from a thread-pool executor if invoked from async context.

    Args:
        text: Input text to embed.

    Returns:
        384-dimensional embedding as list[float].
    """
    return _model.encode(text).tolist()
