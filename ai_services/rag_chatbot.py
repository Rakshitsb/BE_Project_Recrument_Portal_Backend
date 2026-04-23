"""
RAG chatbot response builder for the candidate-facing assistant.

This version intentionally grounds answers in the CURRENT job only.
It uses the stored job title, description, raw JD text, and the complete
structured `jd_parsed` payload to build context for the model.
"""

import logging
from typing import Any

from ai.service import MODEL, client
from ai_services.rag_helpers import (
    _fetch_candidate_profile,
    _fetch_hr_profile,
    _fetch_job_with_hr,
)

logger = logging.getLogger(__name__)

_FALLBACK_RESPONSE = (
    "I'm having trouble responding right now. Please try again in a moment."
)
_MAX_HISTORY = 20


async def get_chatbot_response(
    db: Any,
    job_id: str,
    candidate_id: str,
    user_message: str,
    chat_history: list[dict],
) -> str:
    """Assemble grounded job context and return an AI-generated reply."""
    jd_context = await _build_jd_context(db, job_id)

    job_meta = await _fetch_job_with_hr(db, job_id)
    hr_profile = await _fetch_hr_profile(db, job_meta.get("hr_id", ""))
    job_title: str = job_meta.get("title", "the role")
    candidate_profile = await _fetch_candidate_profile(db, candidate_id)

    system_prompt = _build_system_prompt(
      jd_context=jd_context,
      company_info=hr_profile,
      candidate_info=candidate_profile,
      job_title=job_title,
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    recent_history = chat_history[-_MAX_HISTORY:]
    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "hr":
            role = "assistant"
            content = f"[HR Message] {content}"
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("[RAGChatbot] Groq call failed: %s", exc)
        return _FALLBACK_RESPONSE


async def _build_jd_context(db: Any, job_id: str) -> str:
    """Return grounded context for the exact current job only."""
    job_meta = await _fetch_job_with_hr(db, job_id)
    if not job_meta:
        return "No detailed job description available."

    parts: list[str] = []

    title = _stringify_value(job_meta.get("title"))
    if title:
        parts.append(f"Job Title: {title}")

    description = _stringify_value(job_meta.get("description"))
    if description:
        parts.append(f"Form Description: {description}")

    raw_jd_text = _stringify_value(job_meta.get("raw_jd_text"))
    if raw_jd_text:
        parts.append(f"Raw JD Text: {raw_jd_text}")

    jd_parsed = job_meta.get("jd_parsed")
    if isinstance(jd_parsed, dict) and jd_parsed:
        structured = _format_structured_jd(jd_parsed)
        if structured:
            parts.append(f"Structured JD Data:\n{structured}")

    return "\n\n".join(part for part in parts if part) or "No detailed job description available."


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        items = [_stringify_value(item) for item in value]
        return ", ".join(item for item in items if item)
    if isinstance(value, dict):
        parts = []
        for key, child in value.items():
            child_text = _stringify_value(child)
            if child_text:
                parts.append(f"{key.replace('_', ' ').title()}: {child_text}")
        return "; ".join(parts)
    return str(value).strip()


def _format_structured_jd(data: dict[str, Any], prefix: str = "") -> str:
    lines: list[str] = []

    for key, value in data.items():
        label = f"{prefix}{key.replace('_', ' ').title()}"

        if isinstance(value, dict):
            nested = _format_structured_jd(value, prefix=f"{label} - ")
            if nested:
                lines.append(nested)
            continue

        if isinstance(value, list):
            if not value:
                continue

            if all(not isinstance(item, (dict, list)) for item in value):
                items = [_stringify_value(item) for item in value]
                items = [item for item in items if item]
                if items:
                    lines.append(f"{label}: {', '.join(items)}")
                continue

            for index, item in enumerate(value, start=1):
                if isinstance(item, dict):
                    nested = _format_structured_jd(item, prefix=f"{label} {index} - ")
                    if nested:
                        lines.append(nested)
                else:
                    item_text = _stringify_value(item)
                    if item_text:
                        lines.append(f"{label} {index}: {item_text}")
            continue

        value_text = _stringify_value(value)
        if value_text:
            lines.append(f"{label}: {value_text}")

    return "\n".join(lines)


def _build_system_prompt(
    jd_context: str,
    company_info: dict,
    candidate_info: dict,
    job_title: str,
) -> str:
    company_name: str = company_info.get("company_name", "the company") or "the company"
    candidate_name: str = candidate_info.get("full_name", "the candidate") or "the candidate"
    skills: list[str] = candidate_info.get("skills") or []
    skills_str: str = ", ".join(skills) if skills else "Not specified"
    education: Any = candidate_info.get("education", "")
    if isinstance(education, list):
        education = "; ".join(
            e.get("degree", "") + " at " + e.get("institution", "")
            if isinstance(e, dict) else str(e)
            for e in education
        )

    return f"""You are a helpful AI assistant for {company_name}. You are assisting {candidate_name}, a candidate shortlisted for the role of {job_title}.

BEHAVIORAL RULES:
- Answer only questions related to this exact job, company, interview process, and candidate fit.
- Use only the CURRENT job description context below. Do not use information from any other job or company.
- If salary, leave policy, working hours, benefits, location, or job type are present in the JD context, answer directly from them.
- If a field is not present in this JD context, explicitly say it is not specified in this job description.
- Be professional, encouraging, and concise.
- Do not reveal internal HR notes, other candidates' information, or invent missing details.
- Do not make hiring decisions or promises on behalf of the company.
- Keep responses under 150 words unless a detailed explanation is genuinely needed.

--- CURRENT JOB DESCRIPTION CONTEXT ---
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
