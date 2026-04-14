ANALYTICS_SYSTEM_PROMPT = "You are an expert in analyzing interview transcripts. You must only use the main questions provided and not generate or infer additional questions."
COMMUNICATION_SYSTEM_PROMPT = "You are an expert in analyzing communication skills from interview transcripts. Identify specific quotes that support your analysis and provide a detailed breakdown of strengths and areas for improvement."
INSIGHTS_SYSTEM_PROMPT = "You are an expert in uncovering deeper insights from interview question and answer sets."

def build_analytics_prompt(transcript: str, questions_str: str) -> str:
    return f"""Analyse the following interview transcript and provide structured feedback:
Transcript: {transcript}
Main Interview Questions:
{questions_str}
Generate the following analytics in JSON format:
1. Overall Score (0-100) and Overall Feedback (60 words) considering:
   Communication Skills, Time Taken to Answer, Confidence, Clarity,
   Attitude, Relevance of Answers, Depth of Knowledge, Problem-Solving
   Ability, Examples and Evidence, Listening Skills, Consistency,
   Adaptability.
2. Communication Skills Score (0-10) and Feedback (60 words).
   Scoring guide:
   10: Fully operational command, fluent, complete understanding.
   09: Fully operational with occasional inaccuracies.
   08: Operational command with occasional misunderstandings.
   07: Effective command despite some inaccuracies.
   06: Partial command, frequent mistakes, handles basic communication.
   05: Basic competence, limited to familiar situations.
   04: Understands only general meaning, frequent breakdowns.
   03: Great difficulty understanding spoken English.
   02: No ability except isolated words.
   01: Did not answer the questions.
3. Question Summaries - use ONLY these questions: {questions_str}
   Rules:
   - Output ALL questions even if not found in transcript
   - Not found in transcript -> summary: "Not Asked"
   - Found but no answer -> summary: "Not Answered"
   - Found with answer -> cohesive paragraph including follow-ups
4. Soft skills summary (10-15 words) covering: confidence, leadership,
   adaptability, critical thinking, decision making.
Return ONLY valid JSON with this exact structure:
{{
  "overallScore": number,
  "overallFeedback": string,
  "communication": {{"score": number, "feedback": string}},
  "questionSummaries": [{{"question": string, "summary": string}}],
  "softSkillSummary": string
}}
No markdown. No explanation. Only JSON."""

def build_communication_prompt(transcript: str) -> str:
    return f"""Analyze the communication skills in this interview transcript:
Transcript: {transcript}
Return ONLY valid JSON with this exact structure:
{{
  "communicationScore": number,
  "overallFeedback": string,
  "supportingQuotes": [{{"quote": string, "analysis": string, "type": "strength" | "improvement_area"}}],
  "strengths": [string],
  "improvementAreas": [string]
}}
No markdown. No explanation. Only JSON."""

def build_insights_prompt(call_summaries: str, interview_name: str, interview_objective: str, interview_description: str) -> str:
    return f"""Imagine you are an interviewer uncovering deeper insights from call summaries.
Call Summaries: {call_summaries}
Interview Title: {interview_name}
Interview Objective: {interview_objective}
Interview Description: {interview_description}
Give 3 insights from the summaries highlighting candidate feedback.
Do not include candidate names. Each insight must be 25 words or less.
Return ONLY valid JSON:
{{"insights": [string, string, string]}}
No markdown. No explanation. Only JSON."""
