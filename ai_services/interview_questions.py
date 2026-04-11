import json
import re

from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings
from interview.schemas import GenerateQuestionsRequest

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert interviewer specialized in \
designing interview questions to evaluate candidates for technical \
roles. You help hiring managers find candidates with strong technical \
expertise and project experience."""


def _build_prompt(data: GenerateQuestionsRequest) -> str:
    context_line = data.context if data.context else "No additional context provided."

    return f"""Job Title: {data.job_title}
Interview Objective: {data.objective}
Number of questions to generate: {data.number}

Follow these guidelines when crafting questions:
- Focus on evaluating technical knowledge and project experience. \
These carry the most weight.
- Include practical problem-solving questions based on real \
project scenarios.
- Soft skills like communication and teamwork should be addressed \
but given less emphasis.
- Keep a professional yet approachable tone.
- Each question must be 30 words or less. Concise and open-ended.

Additional context:
{context_line}

Also generate a short second-person description (50 words or less) \
about this interview to show the candidate. Do not copy the \
objective directly. Make it clear to the candidate what the \
interview will cover.

Return ONLY valid JSON in this exact format, nothing else:
{{
  "questions": [{{"question": "string"}}],
  "description": "string"
}}"""


async def generate_questions(data: GenerateQuestionsRequest) -> dict:
    try:
        prompt = _build_prompt(data)

        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        result = json.loads(raw)

        if "questions" not in result or "description" not in result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Model returned unexpected format",
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
            detail=f"Question generation failed: {str(e)}",
        )
