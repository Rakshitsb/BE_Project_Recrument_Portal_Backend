import json
import re

from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

COMMUNICATION_SYSTEM_PROMPT = """You are an expert in analyzing \
communication skills from interview transcripts. Your tasks are:
1. Analyze the communication skills demonstrated in the transcript
2. Identify specific quotes that support your analysis
3. Provide a detailed breakdown of strengths and areas for \
improvement
Return only valid JSON. No explanations outside the JSON."""


def _build_communication_prompt(transcript: str) -> str:
    return f"""Analyze the communication skills demonstrated in the following \
interview transcript.

Transcript:
{transcript}

Evaluate the candidate on:
- Clarity and structure of responses
- Vocabulary and grammar usage
- Confidence in delivery
- Active listening and relevance of answers
- Ability to express complex ideas simply

Return ONLY valid JSON in this exact format, nothing else:
{{
  "communicationScore": number,
  "overallFeedback": string,
  "supportingQuotes": [
    {{
      "quote": string,
      "analysis": string,
      "type": string
    }}
  ],
  "strengths": [string],
  "improvementAreas": [string]
}}

Rules for supportingQuotes:
- "quote" must be an exact phrase taken from the transcript
- "analysis" must be 1-2 sentences explaining what the quote \
demonstrates about communication
- "type" must be exactly "strength" or "improvement_area"
- Include between 3 and 5 supporting quotes

Rules for strengths and improvementAreas:
- Each must be a short phrase (10 words or less)
- Include between 2 and 4 items in each list

communicationScore must be a number between 0 and 10.
overallFeedback must be 2-3 sentences summarizing overall \
communication skills."""


async def analyze_communication(transcript: str) -> dict:
    try:
        prompt = _build_communication_prompt(transcript)

        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": COMMUNICATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )

        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        result = json.loads(raw)

        required_keys = [
            "communicationScore",
            "overallFeedback",
            "supportingQuotes",
            "strengths",
            "improvementAreas",
        ]
        for key in required_keys:
            if key not in result:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Model returned unexpected format",
                )

        for quote in result["supportingQuotes"]:
            if not all(k in quote for k in ["quote", "analysis", "type"]):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid supportingQuotes format",
                )
            if quote["type"] not in ["strength", "improvement_area"]:
                quote["type"] = "strength"

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
            detail=f"Communication analysis failed: {str(e)}",
        )
