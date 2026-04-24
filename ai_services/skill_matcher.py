import logging
from typing import TypedDict

from ai_services.candidate_embeddings import build_candidate_profile_text

logger = logging.getLogger(__name__)


class SkillMatchResult(TypedDict):
    score: float
    matched_skills: list[str]
    missing_skills: list[str]
    bonus_skills: list[str]
    experience_gap: float
    scoring_method: str
    confidence: str


def _normalized_skills(candidate: dict, job: dict) -> tuple[set[str], set[str]]:
    candidate_skills = {str(s).lower().strip() for s in candidate.get("skills", []) if s}
    required = {str(s).lower().strip() for s in job.get("required_skills", []) if s}
    jd_parsed = job.get("jd_parsed") or {}
    if isinstance(jd_parsed.get("required_skills"), list):
        required |= {
            str(skill).lower().strip() for skill in jd_parsed["required_skills"] if skill
        }
    return candidate_skills, required


def _experience_score(candidate: dict, job: dict) -> tuple[float, float]:
    required_years = float(job.get("experience_required") or 0.0)
    candidate_years = float(candidate.get("experience_years") or 0.0)
    gap = candidate_years - required_years
    if required_years == 0.0 or candidate_years >= required_years:
        return 1.0, gap
    return candidate_years / required_years, gap


def _confidence(candidate_skills: set[str], required_skills: set[str]) -> str:
    if not candidate_skills or not required_skills:
        return "low"
    if len(required_skills) < 3:
        return "medium"
    return "high"


def match_candidate_to_job(candidate: dict, job: dict) -> SkillMatchResult:
    candidate_skills, required_skills = _normalized_skills(candidate, job)
    matched = candidate_skills & required_skills
    missing = required_skills - candidate_skills
    bonus = candidate_skills - required_skills
    union = candidate_skills | required_skills
    jaccard_skill_score = len(matched) / len(union) if union else 0.0
    exp_score, experience_gap = _experience_score(candidate, job)
    scoring_method = "embedding"

    try:
        import numpy as np
        from ai_services.vector_store import get_embedding_for_text

        candidate_text = build_candidate_profile_text(candidate)
        job_text = (
            f"{job.get('title', '')}. {job.get('description', '')}. "
            f"Required: {', '.join(sorted(required_skills))}"
        )
        emb_candidate = np.array(get_embedding_for_text(candidate_text))
        emb_job = np.array(get_embedding_for_text(job_text))
        norm_a = np.linalg.norm(emb_candidate)
        norm_b = np.linalg.norm(emb_job)
        semantic_score = 0.0
        if norm_a and norm_b:
            semantic_score = float(np.dot(emb_candidate, emb_job) / (norm_a * norm_b))
            semantic_score = max(0.0, min(1.0, semantic_score))
        raw_score = (semantic_score * 0.60) + (exp_score * 0.20) + (jaccard_skill_score * 0.20)
    except Exception as exc:
        logger.warning("[SkillMatcher] Embedding scoring failed: %s", exc)
        raw_score = (jaccard_skill_score * 0.70) + (exp_score * 0.30)
        scoring_method = "keyword_overlap"

    return SkillMatchResult(
        score=round(min(max(raw_score, 0.0), 1.0), 4),
        matched_skills=sorted(matched),
        missing_skills=sorted(missing),
        bonus_skills=sorted(bonus),
        experience_gap=round(experience_gap, 1),
        scoring_method=scoring_method,
        confidence=_confidence(candidate_skills, required_skills),
    )


def batch_match(candidate: dict, jobs: list[dict]) -> list[dict]:
    results: list[dict] = []
    for job in jobs:
        try:
            results.append(
                {
                    "job_id": str(job.get("_id", "")),
                    "title": job.get("title", ""),
                    **match_candidate_to_job(candidate, job),
                }
            )
        except Exception as exc:
            logger.warning("[SkillMatcher] Skipped job %s: %s", job.get("_id"), exc)
    results.sort(key=lambda item: item["score"], reverse=True)
    return results
