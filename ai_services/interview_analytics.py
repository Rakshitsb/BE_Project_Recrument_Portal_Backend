import json
import re

from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

ANALYTICS_SYSTEM_PROMPT = """You are an expert in analyzing \
interview transcripts. You must only use the main questions \
provided and not generate or infer additional questions. \
Evaluate the candidate fairly and provide structured feedback \
in valid JSON format only."""


def _build_analytics_prompt(transcript: str, main_questions: str) -> str:
    return f"""Analyse the following interview transcript and provide structured \
feedback.

Transcript:
{transcript}

Main Interview Questions:
{main_questions}

Based on this transcript and the provided main interview questions, \
generate the following analytics in JSON format:

1. Overall Score (0-100) and Overall Feedback (60 words).
   Consider these factors:
   Communication Skills, Time Taken to Answer, Confidence, \
Clarity, Attitude, Relevance of Answers, Depth of Knowledge, \
Problem-Solving Ability, Examples and Evidence, \
Listening Skills, Consistency, Adaptability.

2. Communication Skills Score (0-10) and Feedback (60 words).
   Use this rating system exactly:
   10: Fully operational command, fluent, complete understanding
   09: Fully operational with occasional inaccuracies
   08: Operational command with occasional inaccuracies
   07: Effective command despite some inaccuracies
   06: Partial command, copes with overall meaning
   05: Basic competence limited to familiar situations
   04: Understands only general meaning in familiar situations
   03: Has great difficulty understanding spoken English
   02: No ability to use language except isolated words
   01: Did not answer the questions

3. Summary for each main interview question listed below.
   Rules:
   - Output ALL questions, even if not found in transcript
   - If question not found in transcript: summary = "Not Asked"
   - If question found but no answer given: summary = "Not Answered"
   - If question found and answered: write a cohesive paragraph \
covering the candidate's answer AND any related follow-up \
questions and answers

4. Soft Skills Summary (10-15 words only).
   Consider: confidence, leadership, adaptability, \
critical thinking, decision making.

Return ONLY valid JSON in this exact format, nothing else:
{{
  "overallScore": number,
  "overallFeedback": string,
  "communication": {{"score": number, "feedback": string}},
  "questionSummaries": [{{"question": string, "summary": string}}],
  "softSkillSummary": string
}}

IMPORTANT: Only use the main questions provided. \
Do not generate or infer additional questions."""


async def generate_analytics(transcript: str, questions: list[str]) -> dict:
    try:
        main_questions = "\n".join(
            f"{i+1}. {q}" for i, q in enumerate(questions)
        )
        prompt = _build_analytics_prompt(transcript, main_questions)

        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ANALYTICS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        raw = completion.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        result = json.loads(raw)

        required_keys = [
            "overallScore",
            "overallFeedback",
            "communication",
            "questionSummaries",
            "softSkillSummary",
        ]
        for key in required_keys:
            if key not in result:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Model returned unexpected format",
                )

        result["mainInterviewQuestions"] = questions
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
            detail=f"Analytics generation failed: {str(e)}",
        )
