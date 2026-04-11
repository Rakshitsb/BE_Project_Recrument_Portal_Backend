import json

from fastapi import HTTPException, status

from ai_services.analytics_engine import MODEL, client, _parse_json
from ai_services.analytics_prompts import (
    COMMUNICATION_SYSTEM_PROMPT,
    INSIGHTS_SYSTEM_PROMPT,
    build_communication_prompt,
    build_insights_prompt,
)


async def analyze_communication(transcript: str) -> dict:
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": COMMUNICATION_SYSTEM_PROMPT},
                {"role": "user", "content": build_communication_prompt(transcript)},
            ],
            temperature=0.2,
        )
        result = _parse_json(completion.choices[0].message.content.strip())
        required = ["communicationScore", "overallFeedback", "supportingQuotes", "strengths", "improvementAreas"]
        if any(key not in result for key in required):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Analytics response missing required fields")
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Model returned invalid JSON")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analytics failed: {str(e)}")


async def generate_insights(call_summaries: list[str], interview_name: str, interview_objective: str, interview_description: str) -> list[str]:
    try:
        summaries_str = "\n\n".join([f"Response {i+1}: {s}" for i, s in enumerate(call_summaries)])
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": INSIGHTS_SYSTEM_PROMPT},
                {"role": "user", "content": build_insights_prompt(summaries_str, interview_name, interview_objective, interview_description)},
            ],
            temperature=0.3,
        )
        result = _parse_json(completion.choices[0].message.content.strip())
        insights = result.get("insights", [])
        if not isinstance(insights, list) or len(insights) != 3:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Insights response must contain exactly 3 insights")
        return insights
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Model returned invalid JSON")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Analytics failed: {str(e)}")
