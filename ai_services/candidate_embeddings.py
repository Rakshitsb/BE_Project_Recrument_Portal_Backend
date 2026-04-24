import asyncio
import json
import logging
import math
from typing import Any

from bson import ObjectId

from db.collections import CANDIDATE_PROFILES, JOBS

logger = logging.getLogger(__name__)


def get_candidate_collection():
    from ai_services.vector_store import get_chroma_client

    return get_chroma_client().get_or_create_collection("candidate_profiles")


def _education_summary(education: Any) -> str:
    if isinstance(education, str):
        return education
    if isinstance(education, list):
        parts: list[str] = []
        for item in education[:3]:
            if isinstance(item, dict):
                parts.append(", ".join(str(item.get(k, "")).strip() for k in ("degree", "field", "institution") if item.get(k)))
            elif item:
                parts.append(str(item).strip())
        return "; ".join(part for part in parts if part)
    if isinstance(education, dict):
        return ", ".join(str(value).strip() for value in education.values() if value)
    return ""


def _past_roles(experience: Any) -> str:
    if not isinstance(experience, list):
        return ""
    roles: list[str] = []
    for item in experience[:3]:
        if not isinstance(item, dict):
            continue
        company = str(item.get("company") or item.get("company_name") or "").strip()
        role = str(item.get("role") or item.get("title") or "").strip()
        label = " at ".join(part for part in (role, company) if part)
        if label:
            roles.append(label)
    return "; ".join(roles)


def build_candidate_profile_text(candidate: dict) -> str:
    skills = ", ".join(skill.strip() for skill in candidate.get("skills", []) if skill)
    parts = [
        f"Skills: {skills}",
        f"Experience: {candidate.get('experience_years') or 0} years",
        f"Bio: {str(candidate.get('bio') or '').strip()}",
        f"Education: {_education_summary(candidate.get('education'))}",
        f"Past roles: {_past_roles(candidate.get('experience'))}",
    ]
    return "\n".join(parts).strip()


async def upsert_candidate_embedding(db: Any, candidate_id: str) -> list[float]:
    candidate = await db[CANDIDATE_PROFILES].find_one({"user_id": candidate_id})
    if not candidate:
        return []
    from ai_services.vector_store import _MODEL_NAME, get_embedding_for_text

    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, get_embedding_for_text, build_candidate_profile_text(candidate))
    get_candidate_collection().upsert(
        ids=[candidate_id],
        embeddings=[embedding],
        metadatas=[{"candidate_id": candidate_id, "name": candidate.get("full_name", "")}],
    )
    await db[CANDIDATE_PROFILES].update_one(
        {"user_id": candidate_id},
        {"$set": {"profile_embedding": embedding, "embedding_model": _MODEL_NAME}},
    )
    return embedding


async def build_candidate_collection(db: Any) -> None:
    collection = get_candidate_collection()
    cursor = db[CANDIDATE_PROFILES].find(
        {"profile_embedding": {"$exists": True, "$ne": None}},
        {"user_id": 1, "full_name": 1, "profile_embedding": 1},
    )
    count = 0
    async for profile in cursor:
        candidate_id = str(profile.get("user_id", ""))
        embedding = profile.get("profile_embedding")
        if not candidate_id or not embedding:
            continue
        collection.upsert(
            ids=[candidate_id],
            embeddings=[embedding],
            metadatas=[{"candidate_id": candidate_id, "name": profile.get("full_name", "")}],
        )
        count += 1
    print(f"[VectorStore] Candidate profiles index rebuilt with {count} profiles")  # noqa: T201


def _job_query_text(job: dict) -> str:
    jd_parsed = job.get("jd_parsed") or {}
    keywords = jd_parsed.get("keywords") if isinstance(jd_parsed, dict) else None
    extras = ", ".join(str(item).strip() for item in keywords if item) if isinstance(keywords, list) and keywords else ""
    if not extras and jd_parsed:
        try:
            extras = json.dumps(jd_parsed, ensure_ascii=False, sort_keys=True)
        except TypeError:
            extras = ""
    return f"{job.get('title', '')}. {job.get('description', '')}. Required skills: {', '.join(job.get('required_skills') or [])}. {extras}".strip()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if not norm_a or not norm_b:
        return 0.0
    return max(0.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)))


async def rank_candidates_for_job(db: Any, job_id: str, candidate_ids: list[str]) -> list[dict[str, float | int | str]]:
    if not candidate_ids:
        return []
    job = await db[JOBS].find_one({"_id": ObjectId(job_id)})
    if not job:
        return [{"candidate_id": cid, "similarity_score": 0.0, "match_percentage": 0} for cid in candidate_ids]
    from ai_services.vector_store import get_embedding_for_text

    loop = asyncio.get_event_loop()
    query_embedding = await loop.run_in_executor(None, get_embedding_for_text, _job_query_text(job))
    profiles = [doc async for doc in db[CANDIDATE_PROFILES].find({"user_id": {"$in": candidate_ids}})]
    by_id = {str(profile.get("user_id", "")): profile for profile in profiles}
    for candidate_id in candidate_ids:
        if not by_id.get(candidate_id, {}).get("profile_embedding"):
            try:
                embedding = await upsert_candidate_embedding(db, candidate_id)
                if by_id.get(candidate_id):
                    by_id[candidate_id]["profile_embedding"] = embedding
            except Exception as exc:
                logger.warning("[VectorStore] candidate embedding refresh failed for %s: %s", candidate_id, exc)
    try:
        results = get_candidate_collection().query(
            query_embeddings=[query_embedding],
            n_results=len(candidate_ids),
            where={"candidate_id": {"$in": candidate_ids}},
            include=["metadatas", "distances"],
        )
        ranked = [
            {"candidate_id": meta.get("candidate_id", ""), "similarity_score": round(max(0.0, min(1.0, 1 / (1 + float(distance)))), 4)}
            for meta, distance in zip(results.get("metadatas", [[]])[0], results.get("distances", [[]])[0])
        ]
    except Exception as exc:
        logger.warning("[VectorStore] Chroma query failed for job %s: %s", job_id, exc)
        ranked = []
    if not ranked:
        ranked = [
            {"candidate_id": candidate_id, "similarity_score": round(_cosine_similarity(query_embedding, by_id.get(candidate_id, {}).get("profile_embedding") or []), 4)}
            for candidate_id in candidate_ids
        ]
    ranked_by_id = {item["candidate_id"]: item for item in ranked if item["candidate_id"]}
    output = []
    for candidate_id in candidate_ids:
        similarity = float(ranked_by_id.get(candidate_id, {}).get("similarity_score", 0.0))
        output.append({"candidate_id": candidate_id, "similarity_score": similarity, "match_percentage": round(similarity * 100)})
    output.sort(key=lambda item: float(item["similarity_score"]), reverse=True)
    return output
