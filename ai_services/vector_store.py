import asyncio
import logging
from typing import Any

from config import settings
from db.collections import JOBS

logger = logging.getLogger(__name__)
_MODEL_NAME = settings.EMBEDDING_MODEL
_COLLECTION_NAME = settings.CHROMA_COLLECTION_NAME
_model = None
_chroma_client = None
_client = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def get_chroma_client():
    global _chroma_client, _client
    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.Client()
        _client = _chroma_client
    return _chroma_client


def _get_collection():
    global _collection
    if _collection is None:
        _collection = get_chroma_client().get_or_create_collection(name=_COLLECTION_NAME)
    return _collection


async def build_chroma_collection(db: Any) -> None:
    cursor = db[JOBS].find(
        {"jd_embedding": {"$exists": True, "$ne": None}},
        {"_id": 1, "title": 1, "jd_embedding": 1},
    )
    ids: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, str]] = []
    async for job in cursor:
        job_id = str(job["_id"])
        ids.append(job_id)
        embeddings.append(job["jd_embedding"])
        metadatas.append({"job_id": job_id, "title": job.get("title", "")})
    if ids:
        _get_collection().upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
    print(f"[VectorStore] Rebuilt with {len(ids)} jobs")  # noqa: T201


async def upsert_job_embedding(db: Any, job_id: str, jd_text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _get_model().encode, jd_text)
    embedding: list[float] = raw.tolist()
    _get_collection().upsert(
        ids=[job_id],
        embeddings=[embedding],
        metadatas=[{"job_id": job_id, "title": ""}],
    )
    from bson import ObjectId

    await db[JOBS].update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"jd_embedding": embedding, "embedding_model": _MODEL_NAME}},
    )
    return embedding


async def delete_job_embedding(job_id: str) -> None:
    try:
        _get_collection().delete(ids=[job_id])
    except Exception:
        pass


async def query_similar_chunks(
    job_id: str, query_text: str, n_results: int = 5
) -> list[dict]:
    try:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _get_model().encode, query_text)
        results = _get_collection().query(
            query_embeddings=[raw.tolist()],
            n_results=n_results,
            include=["metadatas", "distances"],
        )
        output: list[dict] = []
        for meta, dist in zip(
            results.get("metadatas", [[]])[0], results.get("distances", [[]])[0]
        ):
            output.append(
                {
                    "job_id": meta.get("job_id", ""),
                    "title": meta.get("title", ""),
                    "distance": float(dist),
                }
            )
        return output
    except Exception as exc:
        logger.warning("[VectorStore] query_similar_chunks failed: %s", exc)
        return []


def get_embedding_for_text(text: str) -> list[float]:
    return _get_model().encode(text).tolist()


from ai_services.candidate_embeddings import (  # noqa: E402
    build_candidate_collection,
    build_candidate_profile_text,
    get_candidate_collection,
    rank_candidates_for_job,
    upsert_candidate_embedding,
)
