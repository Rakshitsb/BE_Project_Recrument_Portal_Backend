import json
import re

from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"

PROMPT = """
You are an expert resume parser.

Extract these fields from the resume text below:
- full_name
- email
- phone
- location
- skills (as a list of strings)
- experience_years (as a number)
- education (list of objects with: degree, institution, year)
- experience (list of objects with: company, role, duration, description)
- projects (list of objects with: name, description)
- bio

Rules:
Return ONLY valid JSON.
"""


async def parse_resume(text: str) -> dict:
    try:
        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )

        raw = completion.choices[0].message.content.strip()

        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        return json.loads(raw)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Model returned invalid JSON",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume parsing failed: {str(e)}",
        )