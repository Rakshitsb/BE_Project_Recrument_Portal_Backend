from bson import ObjectId
from fastapi import HTTPException, status

from ai_services.skill_matcher import match_candidate_to_job
from ai_services.ranking_insights import generate_candidate_match_insight
from applications.schemas import RankedCandidatesResponse
from config import settings
from db.collections import APPLICATIONS, CANDIDATE_PROFILES, JOBS


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ID format")


def _effective_match_percentage(
    *,
    similarity_score: float,
    fallback_score: float,
    matched_skills: list[str],
    missing_skills: list[str],
) -> tuple[float, int]:
    effective_similarity = similarity_score
    match_percentage = round(similarity_score * 100)

    if effective_similarity <= 0.0 and fallback_score > 0.0:
        effective_similarity = round(float(fallback_score), 4)
        match_percentage = round(effective_similarity * 100)

    # If the job has explicit required skills and the candidate matches none of them,
    # return 0% to avoid presenting semantic similarity as direct skill fit.
    if not matched_skills and missing_skills:
        match_percentage = 0

    return effective_similarity, match_percentage


async def get_ranked_candidates(db, job_id: str, hr_id: str) -> dict:
    job = await db[JOBS].find_one({"_id": _oid(job_id)})
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if job.get("hr_id") != hr_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    applications = [doc async for doc in db[APPLICATIONS].find({"job_id": job_id})]
    if not applications:
        return RankedCandidatesResponse(
            job_id=job_id,
            job_title=job.get("title", ""),
            total_applicants=0,
            ranked_candidates=[],
            scoring_method="embedding" if settings.ENABLE_EMBEDDING_SCORING else "keyword_overlap",
            note=(
                "Ranked by semantic similarity between candidate profile and job description"
                if settings.ENABLE_EMBEDDING_SCORING
                else "Ranked by required skill overlap and experience match"
            ),
        ).model_dump()

    candidate_ids = [doc["candidate_id"] for doc in applications if doc.get("candidate_id")]
    if settings.ENABLE_EMBEDDING_SCORING:
        from ai_services.vector_store import rank_candidates_for_job

        similarity_results = await rank_candidates_for_job(db, job_id, candidate_ids)
    else:
        similarity_results = [
            {"candidate_id": candidate_id, "similarity_score": 0.0, "match_percentage": 0}
            for candidate_id in candidate_ids
        ]
    application_map = {doc["candidate_id"]: doc for doc in applications}
    ranked_candidates: list[dict] = []

    for item in similarity_results:
        candidate_id = str(item["candidate_id"])
        candidate = await db[CANDIDATE_PROFILES].find_one({"user_id": candidate_id}) or {}
        breakdown = match_candidate_to_job(candidate, job)
        application = application_map.get(candidate_id, {})
        similarity_score, match_percentage = _effective_match_percentage(
            similarity_score=float(item["similarity_score"]),
            fallback_score=float(breakdown["score"]),
            matched_skills=breakdown["matched_skills"],
            missing_skills=breakdown["missing_skills"],
        )
        analysis_note = await generate_candidate_match_insight(
            candidate=candidate,
            job=job,
            match_percentage=match_percentage,
            matched_skills=breakdown["matched_skills"],
            missing_skills=breakdown["missing_skills"],
            experience_gap=breakdown["experience_gap"],
        )
        ranked_candidates.append(
            {
                "candidate_id": candidate_id,
                "candidate_name": candidate.get("full_name", ""),
                "match_percentage": match_percentage,
                "similarity_score": similarity_score,
                "matched_skills": breakdown["matched_skills"],
                "missing_skills": breakdown["missing_skills"],
                "experience_gap": breakdown["experience_gap"],
                "scoring_method": breakdown["scoring_method"],
                "analysis_note": analysis_note,
                "application_id": str(application.get("_id", "")),
                "application_status": str(application.get("status", "")),
            }
        )

    ranked_candidates.sort(key=lambda item: item["similarity_score"], reverse=True)
    return RankedCandidatesResponse(
        job_id=job_id,
        job_title=job.get("title", ""),
        total_applicants=len(applications),
        ranked_candidates=ranked_candidates,
        scoring_method="embedding" if settings.ENABLE_EMBEDDING_SCORING else "keyword_overlap",
        note=(
            "Ranked by semantic similarity between candidate profile and job description"
            if settings.ENABLE_EMBEDDING_SCORING
            else "Ranked by required skill overlap and experience match"
        ),
    ).model_dump()
