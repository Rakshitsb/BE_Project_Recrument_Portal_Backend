from groq import AsyncGroq
from fastapi import HTTPException, status

from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"

PROMPT = """
You are an expert cover letter writer.

Write a professional and formal cover letter for a job application.
Use the candidate profile and job description provided below.

Rules:
- Write exactly 3 to 4 paragraphs
- Paragraph 1: Strong opening — mention the job title and express genuine interest
- Paragraph 2: Highlight the candidate's most relevant skills matching the job requirements
- Paragraph 3: Mention experience, education and specific achievements from the profile
- Paragraph 4: Confident closing — express eagerness to discuss further, thank the reader
- Use Professional and Formal tone throughout
- Address as "Dear Hiring Manager" if no specific name is available
- Do NOT include subject line, date, or address headers
- Return ONLY the cover letter text. No explanation. No markdown. No JSON.
"""


async def generate_cover_letter(candidate_profile: dict, job: dict) -> dict:
    try:
        skills = ", ".join(candidate_profile.get("skills", []))
        required_skills = ", ".join(job.get("required_skills", []))

        user_message = (
            f"Candidate Profile:\n"
            f"- Name: {candidate_profile.get('full_name', 'N/A')}\n"
            f"- Skills: {skills}\n"
            f"- Experience: {candidate_profile.get('experience_years', 0)} years\n"
            f"- Education: {candidate_profile.get('education', 'N/A')}\n"
            f"- Bio: {candidate_profile.get('bio', 'N/A')}\n\n"
            f"Job Details:\n"
            f"- Job Title: {job.get('title', 'N/A')}\n"
            f"- Company: {job.get('company_name', 'N/A')}\n"
            f"- Required Skills: {required_skills}\n"
            f"- Job Description: {job.get('description', 'N/A')}\n\n"
            f"Write the cover letter now."
        )

        completion = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
        )

        raw = completion.choices[0].message.content.strip()

        return {"cover_letter": raw}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cover letter generation failed: {str(e)}",
        )
