"""
AI Skill Matcher — Job-Candidate Fit Scoring

Current implementation: keyword overlap scoring (Jaccard similarity on skill sets).
Runs with zero extra dependencies beyond what is already installed.

Upgrade path to SBERT (when ready):
  1. Uncomment the embedding block in _embedding_similarity()
  2. Remove the keyword fallback block
  3. The public interface (match_candidate_to_job, batch_match) stays identical —
     no changes needed in callers.

Design principles:
  - match_candidate_to_job() is the single public entry point
  - All scoring is normalised to float 0.0–1.0
  - Returns a SkillMatchResult dict — never raises, always returns a result
  - Safe for use in non-async contexts (no Motor calls inside this file)
    Data is fetched by the caller and passed in as plain dicts.
"""

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


class SkillMatchResult(TypedDict):
    score: float            # 0.0–1.0 overall match score
    matched_skills: list    # skills present in both candidate and JD
    missing_skills: list    # required_skills from JD not in candidate profile
    bonus_skills: list      # candidate skills beyond what JD requires
    experience_gap: float   # candidate_years - jd_required_years (negative = gap)
    scoring_method: str     # "keyword_overlap" | "embedding"
    confidence: str         # "low" | "medium" | "high" — based on data completeness


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_candidate_to_job(candidate: dict, job: dict) -> SkillMatchResult:
    """Score a candidate dict against a job dict using keyword overlap.

    Both args are plain MongoDB document dicts already fetched by the caller.

    Args:
        candidate: Must contain ``skills`` (list[str]) and ``experience_years`` (float).
        job:       Must contain ``required_skills`` (list[str]) and optionally
                   ``jd_parsed`` (dict) and ``experience_required`` (float).

    Returns:
        SkillMatchResult with score, matched/missing/bonus skills, experience gap,
        scoring method, and confidence level.
    """
    # STEP 1 — Normalise skill sets (case-insensitive)
    candidate_skills: set[str] = {
        s.lower().strip() for s in candidate.get("skills", []) if s
    }
    base_required: list[str] = job.get("required_skills", []) or []
    required_skills: set[str] = {s.lower().strip() for s in base_required if s}

    # Merge from jd_parsed if available (union)
    jd_parsed: dict | None = job.get("jd_parsed")
    if jd_parsed and isinstance(jd_parsed.get("required_skills"), list):
        required_skills |= {s.lower().strip() for s in jd_parsed["required_skills"] if s}

    # STEP 2 — Jaccard skill score
    matched: set[str] = candidate_skills & required_skills
    union: set[str] = candidate_skills | required_skills
    skill_score: float = len(matched) / len(union) if union else 0.0

    # STEP 3 — Experience score
    required_years: float = float(job.get("experience_required") or 0.0)
    candidate_years: float = float(candidate.get("experience_years") or 0.0)
    experience_gap: float = candidate_years - required_years

    if required_years == 0.0:
        exp_score: float = 1.0
    elif candidate_years >= required_years:
        exp_score = 1.0
    else:
        exp_score = candidate_years / required_years  # partial credit

    # STEP 4 — Weighted overall score (skill 70%, experience 30%)
    raw_score: float = (skill_score * 0.70) + (exp_score * 0.30)
    score: float = round(min(max(raw_score, 0.0), 1.0), 4)

    # STEP 5 — Confidence rating
    if len(required_skills) == 0 or len(candidate_skills) == 0:
        confidence: str = "low"
    elif len(required_skills) < 3:
        confidence = "medium"
    else:
        confidence = "high"

    # STEP 6 — Build result
    return SkillMatchResult(
        score=score,
        matched_skills=sorted(matched),
        missing_skills=sorted(required_skills - candidate_skills),
        bonus_skills=sorted(candidate_skills - required_skills),
        experience_gap=round(experience_gap, 1),
        scoring_method="keyword_overlap",
        confidence=confidence,
    )


def batch_match(candidate: dict, jobs: list[dict]) -> list[dict]:
    """Match a candidate against multiple jobs, sorted by score descending.

    Failures on individual jobs are logged and skipped — the batch never raises.

    Args:
        candidate: Candidate profile dict (same shape as match_candidate_to_job).
        jobs:      List of job document dicts.

    Returns:
        List of dicts: { job_id, title, **SkillMatchResult }, sorted best→worst.
    """
    results: list[dict] = []
    for job in jobs:
        try:
            match = match_candidate_to_job(candidate, job)
            results.append({
                "job_id": str(job.get("_id", "")),
                "title": job.get("title", ""),
                **match,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SkillMatcher] Skipped job %s: %s", job.get("_id"), exc)
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Private — SBERT upgrade path
# ---------------------------------------------------------------------------


def _embedding_similarity(text_a: str, text_b: str) -> float:
    """Semantic similarity between two text strings using embeddings.

    Current: returns 0.0 (not yet integrated into scoring pipeline).

    TODO — SBERT upgrade (3 steps):
      1. Uncomment the block below
      2. In match_candidate_to_job(), replace Jaccard skill_score with:
             skill_score = _embedding_similarity(
                 " ".join(candidate_skills),
                 " ".join(required_skills)
             )
      3. Change scoring_method to "embedding"

    # --- SBERT block (uncomment when upgrading) ---
    # from ai_services.vector_store import get_embedding_for_text
    # import numpy as np
    # emb_a = np.array(get_embedding_for_text(text_a))
    # emb_b = np.array(get_embedding_for_text(text_b))
    # cosine = np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
    # return float(np.clip(cosine, 0.0, 1.0))
    """
    return 0.0
