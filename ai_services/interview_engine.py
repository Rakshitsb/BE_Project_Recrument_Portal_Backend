"""Groq-powered interview question generation."""

import json
import re
from uuid import uuid4

from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings
from ai_services.interview_prompts import (
    QUESTION_SYSTEM_PROMPT,
    QUESTION_USER_TEMPLATE,
    RETELL_AGENT_TEMPLATE,
)

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = settings.GROQ_MODEL


async def generate_interview_questions(
    name: str, objective: str, count: int, context: str,
) -> dict:
    if not 1 <= count <= 20:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Question count must be between 1 and 20",
        )
    try:
        prompt = QUESTION_USER_TEMPLATE.format(
            name=name, objective=objective,
            count=count, context=context,
        )
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": QUESTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        data = json.loads(raw)

        questions = data.get("questions", [])
        description = data.get("description", "")
        if not questions or not description:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Model returned unexpected structure",
            )
        for q in questions:
            q["id"] = str(uuid4())
            q["follow_up_count"] = 1

        return {"questions": questions, "description": description}

    except json.JSONDecodeError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Model returned invalid JSON",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Service failed: {str(e)}",
        )


def generate_retell_agent_prompt(
    name: str, objective: str, questions: list[dict],
    duration_mins: int, candidate_name: str,
) -> str:
    formatted_questions = "\n".join(
        f"{i+1}. {q['question']}" for i, q in enumerate(questions)
    )
    return RETELL_AGENT_TEMPLATE.format(
        duration_mins=duration_mins,
        candidate_name=candidate_name,
        objective=objective,
        formatted_questions=formatted_questions,
    )
