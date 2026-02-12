import os
import json
from fastapi import HTTPException
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

        self.model = "gemini-3-flash-preview"

    def extract_resume_data(self, resume_text: str) -> dict:
        if not self.client:
            raise HTTPException(
                status_code=500, detail="GEMINI_API_KEY not configured."
            )

        prompt = f"""
You are an AI Resume Parser.

Extract structured information from the resume below.

Return ONLY valid JSON.
Do NOT include markdown.
Do NOT include explanations.

Required JSON format:

{{
  "full_name": "",
  "email": "",
  "phone": "",
  "skills": [],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "year": ""
    }}
  ],
  "experience": [
    {{
      "company": "",
      "role": "",
      "duration": "",
      "description": ""
    }}
  ],
  "projects": [
    {{
      "name": "",
      "description": ""
    }}
  ]
}}

Resume Text:
{resume_text}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )

            content = response.text.strip()

            # Clean accidental markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]

            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content)

        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500, detail="Failed to parse Gemini response as JSON."
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")
