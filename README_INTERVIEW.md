# Interview Bot Integration - Backend API

## Overview
- HR shortlists a candidate and creates an interview; Groq generates the interview questions.
- The candidate receives a link, logs in, and starts a Retell voice interview.
- Retell sends webhook events, Groq analyzes the transcript, and analytics are saved to MongoDB.
- HR reviews interview analytics and updates the candidate to selected or rejected.

## New Modules
| Module | Prefix | Who Can Access | Purpose |
|---|---|---|---|
| interviewer | `/interviewers` | HR + Admin | AI persona management |
| interview | `/interviews` | HR + Candidate | Interview lifecycle |
| interview_response | `/interview-responses` | HR + Candidate | Results + analytics |
| retell | `/webhooks/retell` | Retell only | Webhook handler |

## Environment Variables
| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | Yes | MongoDB connection string used by Motor. |
| `DB_NAME` | Yes | MongoDB database name for the recruitment portal. |
| `JWT_SECRET` | Yes | Secret key used to sign and verify JWT access tokens. |
| `JWT_ALGORITHM` | Yes | JWT signing algorithm, usually `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Candidate and HR access token lifetime in minutes. |
| `GROQ_API_KEY` | Yes | API key for Groq-powered AI services. |
| `GROQ_MODEL` | Yes | Groq model name used by analytics and interview generation. |
| `RETELL_API_KEY` | Yes | API key for Retell call registration and webhook verification. |
| `BASE_URL` | Yes | Public backend base URL used when generating interview links. |
| `RETELL_AGENT_ID_LISA` | Seed only | Retell agent ID for the Lisa interviewer seed record. |
| `RETELL_AGENT_ID_BOB` | Seed only | Retell agent ID for the Bob interviewer seed record. |

## Setup Steps
1. Copy `.env.example` to `.env` and fill all values.
2. Create Retell agents in the dashboard and set `RETELL_AGENT_ID_*` values.
3. Run `pip install -r requirements.txt`.
4. Run `python -m scripts.seed_interviewers`.
5. Start the API with `uvicorn main:app --reload`.
6. Indexes are created automatically on startup via the FastAPI lifespan event.

## API Flow - HR Creates Interview
```text
# 1. HR logs in
POST /auth/login

# 2. HR shortlists candidate
PATCH /applications/{app_id}/status
body: {"status": "shortlisted"}

# 3. HR fetches available interviewers
GET /interviewers/

# 4. HR creates interview (triggers Groq question generation)
POST /interviews/
body: {
  "application_id": "...",
  "interviewer_id": "...",
  "name": "Backend Engineer Interview",
  "objective": "Assess Python and system design skills",
  "question_count": 5,
  "time_duration": "30 mins",
  "context": "Role requires FastAPI and MongoDB experience"
}
# Returns: interview_token for candidate link
```

## API Flow - Candidate Takes Interview
```text
# 1. Candidate logs in
POST /auth/login

# 2. Candidate views their interviews
GET /interviews/candidate/my

# 3. Candidate opens interview link
GET /interviews/candidate/take/{token}

# 4. Candidate registers call (triggers Retell web call)
POST /interviews/candidate/take/{token}/register-call
body: {
  "candidate_name": "John Doe",
  "candidate_email": "john@example.com"
}
# Returns: call_id + access_token -> use with Retell Web SDK
```

## Webhook Events
| Event | Trigger | Action |
|---|---|---|
| `call_started` | Call begins | Updates call status |
| `call_ended` | Call disconnects | Saves duration and marks response ended |
| `call_analyzed` | Retell finishes NLP | Triggers Groq analytics and stores results |

## Key Design Decisions
- Questions and objectives are never returned to the candidate payload.
- Interview tokens are generated as secure opaque values instead of predictable IDs.
- The webhook acknowledges processing with HTTP 200 to prevent Retell retry storms.
- All webhook handlers are idempotent and safe for duplicate delivery.
- Application status is synchronized when interview results are marked selected or rejected.
- The raw Retell call object is stored in MongoDB but never exposed by API schemas.
