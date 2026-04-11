import json
import re

from groq import AsyncGroq
from fastapi import HTTPException, status

from ai_services.analytics_prompts import (
    ANALYTICS_SYSTEM_PROMPT,
    build_analytics_prompt,
)
from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = settings.GROQ_MODEL


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


async def analyze_transcript(transcript: str, questions: list[str]) -> dict:
    try:
        questions_str = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        prompt = build_analytics_prompt(transcript, questions_str)
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ANALYTICS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        result = _parse_json(completion.choices[0].message.content.strip())
        required = ["overallScore", "overallFeedback", "communication", "questionSummaries", "softSkillSummary"]
        if any(key not in result for key in required):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Analytics response missing required fields")
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Model returned invalid JSON")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analytics failed: {str(e)}")


from ai_services.analytics_engine_extra import (
    analyze_communication,
    generate_insights,
)
