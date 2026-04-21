"""
RAG Chatbot — Stateless Context Assembler + Groq Engine
========================================================
This module is the brain of the candidate-facing chatbot.  It is STATELESS:
chat history is always passed in from the DB layer (built in Prompt 4) so
this module can be tested and reused independently.

Context is assembled from three sources on every request:
  1. ChromaDB in-memory vector search (JD semantic chunks via vector_store)
  2. MongoDB hr_profiles (company identity, industry, location)
  3. MongoDB candidate_profiles (skills, experience, education)

The assembled context is injected into a system prompt that constrains the
model to stay on-topic and professional.  The Groq client and model name are
imported from ai/service.py — no second client is created here.
"""

import logging
from typing import Any

from ai.service import MODEL, client
from ai_services.rag_helpers import (
    _fetch_candidate_profile,
    _fetch_hr_profile,
    _fetch_job_with_hr,
)
from ai_services.vector_store import query_similar_chunks

logger = logging.getLogger(__name__)

_FALLBACK_RESPONSE = (
    "I'm having trouble responding right now. Please try again in a moment."
)
_MAX_HISTORY = 20  # messages kept from chat_history to avoid token overflow


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_chatbot_response(
    db: Any,
    job_id: str,
    candidate_id: str,
    user_message: str,
    chat_history: list[dict],
) -> str:
    """Assemble RAG context and return an AI-generated reply.

    Steps:
      1. Query ChromaDB for semantically similar JD chunks.
      2. Fetch HR company profile from MongoDB.
      3. Fetch candidate profile from MongoDB.
      4. Build system prompt from all context.
      5. Build Groq messages array (system + history + new message).
      6. Call Groq and return the response text.

    Args:
        db:           Motor async database instance.
        job_id:       The job the candidate is enquiring about.
        candidate_id: The authenticated candidate's user_id.
        user_message: The new message from the candidate.
        chat_history: Previous messages as list of dicts with keys
                      ``role`` ("user" | "assistant" | "hr") and ``content``.

    Returns:
        The model's reply as a plain string.
    """
    # STEP 1 — JD context via ChromaDB vector search
    jd_context = await _build_jd_context(db, job_id, user_message)

    # STEP 2 — HR company info
    job_meta = await _fetch_job_with_hr(db, job_id)
    hr_profile = await _fetch_hr_profile(db, job_meta.get("hr_id", ""))
    job_title: str = job_meta.get("title", "the role")

    # STEP 3 — Candidate profile
    candidate_profile = await _fetch_candidate_profile(db, candidate_id)

    # STEP 4 — Build system prompt
    system_prompt = _build_system_prompt(
        jd_context=jd_context,
        company_info=hr_profile,
        candidate_info=candidate_profile,
        job_title=job_title,
    )

    # STEP 5 — Build Groq messages array
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Append history (last N), mapping "hr" role → "assistant"
    recent_history = chat_history[-_MAX_HISTORY:]
    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "hr":
            role = "assistant"
            content = f"[HR Message] {content}"
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    # STEP 6 — Call Groq
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("[RAGChatbot] Groq call failed: %s", exc)
        return _FALLBACK_RESPONSE


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _build_jd_context(db: Any, job_id: str, query_text: str) -> str:
    """Return a formatted JD context string from ChromaDB or MongoDB fallback."""
    chunks = await query_similar_chunks(job_id, query_text, n_results=3)

    if chunks:
        titles = [c.get("title", "") for c in chunks if c.get("title")]
        return "Relevant roles: " + ", ".join(titles) if titles else "JD context available."

    # Fallback: use raw jd_parsed stored in MongoDB
    job_meta = await _fetch_job_with_hr(db, job_id)
    jd_parsed: dict | None = job_meta.get("jd_parsed")
    if not jd_parsed:
        return "No detailed job description available."

    parts: list[str] = []
    if jd_parsed.get("summary"):
        parts.append(f"Summary: {jd_parsed['summary']}")
    if jd_parsed.get("responsibilities"):
        resp = "; ".join(jd_parsed["responsibilities"][:5])
        parts.append(f"Responsibilities: {resp}")
    if jd_parsed.get("required_skills"):
        skills = ", ".join(jd_parsed["required_skills"][:10])
        parts.append(f"Required Skills: {skills}")
    return "\n".join(parts) if parts else "No detailed job description available."


def _build_system_prompt(
    jd_context: str,
    company_info: dict,
    candidate_info: dict,
    job_title: str,
) -> str:
    """Build and return the system prompt string (synchronous, pure string ops).

    Args:
        jd_context:     Formatted JD context text from ChromaDB / MongoDB.
        company_info:   Dict with company_name, industry, company_size, etc.
        candidate_info: Dict with full_name, skills, experience_years, education.
        job_title:      Display title of the job role.

    Returns:
        A multi-section system prompt string ready for Groq.
    """
    company_name: str = company_info.get("company_name", "the company") or "the company"
    candidate_name: str = candidate_info.get("full_name", "the candidate") or "the candidate"
    skills: list[str] = candidate_info.get("skills") or []
    skills_str: str = ", ".join(skills) if skills else "Not specified"
    education: Any = candidate_info.get("education", "")
    if isinstance(education, list):
        education = "; ".join(
            e.get("degree", "") + " at " + e.get("institution", "") if isinstance(e, dict) else str(e)
            for e in education
        )

    return f"""You are a helpful AI assistant for {company_name}. You are assisting {candidate_name}, \
a candidate shortlisted for the role of {job_title}.

BEHAVIORAL RULES:
- Answer only questions related to the job, company, interview process, and the candidate's fit.
- Be professional, encouraging, and concise.
- Do not reveal internal HR notes, other candidates' information, or salary details unless explicitly present in the JD.
- If you don't know something, say so honestly — do not hallucinate.
- Do not make hiring decisions or promises on behalf of the company.
- Keep responses under 150 words unless a detailed explanation is genuinely needed.

--- JOB DESCRIPTION CONTEXT ---
{jd_context}

--- COMPANY INFORMATION ---
Company: {company_name}
Industry: {company_info.get("industry", "")}
Size: {company_info.get("company_size", "")}
Location: {company_info.get("company_location", "")}

--- CANDIDATE PROFILE ---
Name: {candidate_name}
Skills: {skills_str}
Experience: {candidate_info.get("experience_years", 0)} years
Education: {education}"""
