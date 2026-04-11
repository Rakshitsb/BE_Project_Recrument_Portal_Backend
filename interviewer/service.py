from retell import Retell
from fastapi import HTTPException, status

from config import settings
from supabase_client import get_supabase
from interviewer.schemas import InterviewerCreate, InterviewerResponse

retell_client = Retell(api_key=settings.RETELL_API_KEY)

RETELL_AGENT_PROMPT = """You are an interviewer who is an expert \
in asking follow up questions to uncover deeper insights. You have \
to keep the interview for {{mins}} minutes or shorter.

The name of the person you are interviewing is {{name}}.

The interview objective is {{objective}}.

These are some of the questions you can ask:
{{questions}}

Once you ask a question, make sure you ask a follow up question \
on it.

Follow these guidelines when conversing:
- Follow a professional yet friendly tone.
- Ask precise and open-ended questions
- The question word count should be 30 words or less
- Make sure you do not repeat any of the questions.
- Do not talk about anything not related to the objective and \
the given questions.
- If the name is given, use it in the conversation.
- End the call politely after covering the main questions."""

INTERVIEWERS = {
    "LISA": {
        "name": "Explorer Lisa",
        "rapport": 7,
        "exploration": 10,
        "empathy": 7,
        "speed": 5,
        "image": "/interviewers/Lisa.png",
        "audio": "Lisa.wav",
        "description": "Hi! I'm Lisa, an enthusiastic and empathetic "
        "interviewer who loves to explore. With a perfect balance of "
        "empathy and rapport, I delve deep into conversations while "
        "maintaining a steady pace.",
        "voice_id": "11labs-Chloe",
    },
    "BOB": {
        "name": "Empathetic Bob",
        "rapport": 7,
        "exploration": 7,
        "empathy": 10,
        "speed": 5,
        "image": "/interviewers/Bob.png",
        "audio": "Bob.wav",
        "description": "Hi! I'm Bob, your go-to empathetic interviewer. "
        "I excel at understanding and connecting with people on a deeper "
        "level, ensuring every conversation is insightful and meaningful.",
        "voice_id": "11labs-Brian",
    },
}


def _to_response(doc: dict) -> InterviewerResponse:
    return InterviewerResponse(
        id=doc["id"],
        agent_id=doc["agent_id"],
        name=doc["name"],
        rapport=doc["rapport"],
        exploration=doc["exploration"],
        empathy=doc["empathy"],
        speed=doc["speed"],
        image=doc["image"],
        audio=doc["audio"],
        description=doc["description"],
    )


async def setup_interviewers() -> list[InterviewerResponse]:
    supabase = get_supabase()

    # Check if interviewers already exist
    result = supabase.table("interviewer").select("id").execute()
    if len(result.data) >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interviewers already set up",
        )

    try:
        # Create one shared Retell LLM for both agents
        llm = retell_client.llm.create(
            model="gpt-4o",
            general_prompt=RETELL_AGENT_PROMPT,
            general_tools=[
                {
                    "type": "end_call",
                    "name": "end_call_1",
                    "description": "End the call if the user uses "
                    "goodbye phrases such as 'bye', 'goodbye', "
                    "or 'have a nice day'.",
                }
            ],
        )

        created = []
        for interviewer in INTERVIEWERS.values():
            # Create Retell agent
            agent = retell_client.agent.create(
                response_engine={
                    "llm_id": llm.llm_id,
                    "type": "retell-llm",
                },
                voice_id=interviewer["voice_id"],
                agent_name=interviewer["name"],
            )

            # Insert into Supabase
            result = supabase.table("interviewer").insert({
                "agent_id": agent.agent_id,
                "name": interviewer["name"],
                "rapport": interviewer["rapport"],
                "exploration": interviewer["exploration"],
                "empathy": interviewer["empathy"],
                "speed": interviewer["speed"],
                "image": interviewer["image"],
                "audio": interviewer["audio"],
                "description": interviewer["description"],
                "voice_id": interviewer["voice_id"],
            }).execute()

            created.append(_to_response(result.data[0]))

        return created

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interviewers: {str(e)}",
        )


async def get_all_interviewers() -> list[InterviewerResponse]:
    supabase = get_supabase()
    result = supabase.table("interviewer").select("*").execute()
    return [_to_response(doc) for doc in result.data]


async def get_interviewer_by_id(interviewer_id: str) -> InterviewerResponse:
    supabase = get_supabase()
    result = supabase.table("interviewer").select("*").eq("id", interviewer_id).single().execute()
    doc = result.data

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interviewer not found",
        )

    return _to_response(doc)
