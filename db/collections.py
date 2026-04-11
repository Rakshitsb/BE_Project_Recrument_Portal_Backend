"""Collection name constants and schema documentation."""

# Existing collections
USERS = "users"
HR_PROFILES = "hr_profiles"
CANDIDATE_PROFILES = "candidate_profiles"
JOBS = "jobs"
APPLICATIONS = "applications"

# Interview bot collections
INTERVIEWERS = "interviewers"
INTERVIEWS = "interviews"
INTERVIEW_RESPONSES = "interview_responses"
INTERVIEW_FEEDBACK = "interview_feedback"

# MongoDB Document Schemas (Interview Bot)
#
# interviewers {
#   _id: ObjectId,
#   agent_id: str,           # Retell agent ID
#   name: str,
#   description: str,
#   image: str,              # path or URL
#   audio: str | None,
#   empathy: int,            # 1-10
#   exploration: int,        # 1-10
#   rapport: int,            # 1-10
#   speed: int,              # 1-10
#   created_at: datetime
# }
#
# interviews {
#   _id: ObjectId,
#   interview_token: str,    # secure unique token for candidate access
#   application_id: str,     # ref → applications._id
#   job_id: str,             # ref → jobs._id
#   hr_id: str,              # ref → users._id (HR who created)
#   candidate_id: str,       # ref → users._id (candidate)
#   interviewer_id: str,     # ref → interviewers._id
#   name: str,               # interview title
#   objective: str,
#   description: str,        # AI-generated, shown to candidate
#   questions: [             # AI-generated
#     { id: str, question: str, follow_up_count: int }
#   ],
#   question_count: int,
#   time_duration: str,      # e.g. "30 mins"
#   is_active: bool,
#   is_archived: bool,
#   response_count: int,
#   created_at: datetime,
#   updated_at: datetime
# }
#
# interview_responses {
#   _id: ObjectId,
#   interview_id: str,       # ref → interviews._id
#   candidate_id: str,       # ref → users._id
#   call_id: str,            # Retell call ID
#   name: str | None,        # candidate name at time of call
#   email: str | None,
#   duration: int | None,    # seconds
#   details: dict | None,    # full Retell call object
#   analytics: dict | None,  # Groq-generated analytics
#   candidate_status: str,   # "pending" | "selected" | "rejected"
#   is_analysed: bool,
#   is_ended: bool,
#   is_viewed: bool,
#   tab_switch_count: int,
#   created_at: datetime,
#   updated_at: datetime
# }
#
# interview_feedback {
#   _id: ObjectId,
#   interview_id: str,
#   candidate_id: str,
#   email: str | None,
#   feedback: str | None,
#   satisfaction: int | None,  # 1-5
#   created_at: datetime
# }
