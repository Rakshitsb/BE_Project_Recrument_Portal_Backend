from ai.service import MODEL, client


def _fallback_insight(
    match_percentage: int,
    matched_skills: list[str],
    missing_skills: list[str],
    experience_gap: float,
) -> str:
    if matched_skills:
        top_skills = ", ".join(matched_skills[:3])
        return f"Strongest visible overlap is in {top_skills}. Review the missing skills before shortlisting."
    gap_text = (
        f"{experience_gap} years above requirement"
        if experience_gap > 0
        else f"{abs(experience_gap)} years below requirement"
        if experience_gap < 0
        else "at the stated experience level"
    )
    if match_percentage >= 40:
        return f"Semantic similarity suggests some transferable fit, but there is little direct keyword overlap and the candidate is {gap_text}."
    if missing_skills:
        return "Direct overlap looks limited. This appears to be a low-confidence semantic match rather than a strong skill match."
    return "Not enough direct evidence was found for a strong recruiter recommendation."


async def generate_candidate_match_insight(
    *,
    candidate: dict,
    job: dict,
    match_percentage: int,
    matched_skills: list[str],
    missing_skills: list[str],
    experience_gap: float,
) -> str | None:
    should_explain = not matched_skills or 0 < match_percentage < 75
    if not should_explain:
        return None
    prompt = f"""
You are assisting an HR recruiter.

Write one short, precise note explaining this candidate's fit for the role.
Use only evidence present in the provided data.
Do not invent adjacent experience.
If there is no direct skill overlap, say that clearly.
Only mention transferable or adjacent fit when it is explicitly supported by candidate skills, bio, education, or past roles.
Keep it under 45 words.
No bullets. No markdown.

Job title: {job.get("title", "")}
Job description: {job.get("description", "")}
Required skills: {", ".join(job.get("required_skills") or [])}

Candidate skills: {", ".join(candidate.get("skills") or [])}
Candidate bio: {candidate.get("bio", "")}
Candidate education: {candidate.get("education", "")}
Candidate experience years: {candidate.get("experience_years", 0)}
Candidate past roles: {candidate.get("experience", [])}

Match percentage: {match_percentage}
Matched skills: {", ".join(matched_skills)}
Missing skills: {", ".join(missing_skills[:10])}
Experience gap: {experience_gap}
"""
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You write careful recruiter notes grounded only in the provided evidence."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = (completion.choices[0].message.content or "").strip()
        return content[:220] if content else _fallback_insight(match_percentage, matched_skills, missing_skills, experience_gap)
    except Exception:
        return _fallback_insight(match_percentage, matched_skills, missing_skills, experience_gap)
