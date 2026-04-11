import json
import re

from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

INSIGHTS_SYSTEM_PROMPT = """You are an expert in uncovering \
deeper insights from interview call summaries. You identify \
patterns, trends, and key themes across multiple candidate \
responses to help hiring managers make better decisions. \
Return only valid JSON. No explanations outside the JSON."""


def _build_insights_prompt(
    summaries: list[str],
    interview_name: str,
    interview_objective: str,
    interview_description: str,
) -> str:
    formatted_summaries = "\n".join(
        f"Summary {i+1}: {s}" for i, s in enumerate(summaries)
    )

    return f"""You are an expert interviewer uncovering deeper insights from \
call summaries across multiple candidate responses.

Interview Title: {interview_name}
Interview Objective: {interview_objective}
Interview Description: {interview_description}

Call Summaries from all candidates:
{formatted_summaries}

Instructions:
- Generate exactly 3 insights from the call summaries
- Each insight must highlight a pattern or theme from \
candidate feedback
- Do not include any candidate names in the insights
- Do not reference individual candidates
- Each insight must be 25 words or less
- Focus on what the summaries collectively reveal about \
candidate quality, common strengths, or common gaps

Return ONLY valid JSON in this exact format, nothing else:
{{
  "insights": [string, string, string]
}}"""


async def generate_insights(
    summaries: list[str],
    interview_name: str,
    interview_objective: str,
    interview_description: str,
) -> dict:
    if len(summaries) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No completed responses found to generate insights",
        )

    try:
        prompt = _build_insights_prompt(
            summaries,
            interview_name,
            interview_objective,
            interview_description,
        )

        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": INSIGHTS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )

        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        result = json.loads(raw)

        if "insights" not in result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model returned unexpected format",
            )

        if not isinstance(result["insights"], list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model returned unexpected format",
            )

        if len(result["insights"]) > 3:
            result["insights"] = result["insights"][:3]
        elif len(result["insights"]) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model returned fewer than 3 insights",
            )

        for insight in result["insights"]:
            if not isinstance(insight, str) or not insight.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="One or more insights are invalid",
                )

        return result

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Model returned invalid JSON",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Insights generation failed: {str(e)}",
        )
