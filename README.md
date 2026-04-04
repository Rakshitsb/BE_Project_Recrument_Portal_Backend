# 🧠 AI-Powered Smart HR Recruitment Portal — Backend

> Phase 1: Authentication, Authorization & CRUD Operations

---

## 📌 Project Overview

A full-stack intelligent recruitment platform backend built with **FastAPI** and **MongoDB Atlas**. This phase covers complete authentication, role-based authorization, and CRUD operations for all entities.

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python) |
| Database | MongoDB Atlas (async via Motor) |
| Authentication | JWT (python-jose) |
| Password Hashing | bcrypt (passlib) |
| Validation | Pydantic v2 |
| Server | Uvicorn |

---

## 📁 Folder Structure

```
backend/
├── main.py                  # App entry point, all routers registered
├── config.py                # Environment variables via pydantic-settings
├── database.py              # MongoDB Atlas async connection
│
├── auth/
│   ├── schemas.py           # UserSignup, UserLogin, TokenResponse, UserInDB
│   ├── utils.py             # hash_password, verify_password, JWT helpers
│   ├── service.py           # signup_user, login_user business logic
│   └── router.py            # POST /auth/signup, POST /auth/login
│
├── candidate/
│   ├── schemas.py           # CandidateProfileCreate, Update, Response
│   ├── service.py           # create, get, update, delete profile
│   └── router.py            # CRUD routes /candidate/profile
│
├── hr/
│   ├── schemas.py           # HRProfileCreate, Update, Response
│   ├── service.py           # create, get, update, delete profile
│   └── router.py            # CRUD routes /hr/profile
│
├── jobs/
│   ├── schemas.py           # JobCreate, Update, Response
│   ├── service.py           # create, get_all, get_by_id, update, delete
│   └── router.py            # CRUD routes /jobs/
│
├── applications/
│   ├── schemas.py           # ApplicationCreate, StatusUpdate, Response, Status Enum
│   ├── service.py           # create, get_my, get_job_apps, update_status, withdraw
│   └── router.py            # CRUD routes /applications/
│
├── admin/
│   ├── service.py           # get_all users/jobs/apps, cascade delete
│   └── router.py            # Admin routes /admin/
│
└── middleware/
    └── auth_guard.py        # get_current_user, require_candidate, require_hr, require_admin
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/hr-recruitment-backend.git
cd hr-recruitment-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

Create a `.env` file in the root of the project:

```env
MONGO_URI=your_mongodb_atlas_connection_string
DB_NAME=hr_recruitment
JWT_SECRET=your_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> **MongoDB Atlas URI:** Go to Atlas Dashboard → Connect → Drivers → Copy connection string → Replace `<password>` with your actual password.

### 5. Seed Admin User

Since admin has no public signup, run this once to create the admin account:

```bash
python seed_admin.py
```

This creates an admin with:
- Email: `admin@portal.com`
- Password: `admin123`

> ⚠️ Change these credentials before deploying to production.

### 6. Run the Server

```bash
uvicorn main:app --reload
```

- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`

---

## 📦 Dependencies

```txt
fastapi
uvicorn
motor
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
python-multipart
python-dotenv
```

---

## 🔐 Authentication

Single `users` MongoDB collection stores all roles. JWT token contains `user_id + role` in payload. Token expiry: 60 minutes.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/signup` | Public | Register as HR or Candidate |
| POST | `/auth/login` | Public | Login, returns JWT token + role |

### Signup Request Body
```json
{
  "name": "John",
  "email": "john@gmail.com",
  "password": "secret123",
  "role": "candidate"
}
```

### Login Response
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "role": "candidate"
}
```

---

## 🛡️ Authorization

Three roles: `candidate` | `hr` | `admin`

Every protected route uses FastAPI `Depends()` with role guard functions from `middleware/auth_guard.py`.

```
Request → Bearer Token → Decode JWT → Check Role → ✅ Allow / ❌ 403 Forbidden
```

### Using the Token

Add this header to every protected request:
```
Authorization: Bearer eyJ...
```

---

## 🗄️ MongoDB Collections

| Collection | Stores |
|---|---|
| `users` | All users with role field |
| `candidate_profiles` | Candidate profile data |
| `hr_profiles` | HR + company data |
| `jobs` | Job postings |
| `applications` | Job applications with status |

---

## 👤 Candidate API

All routes protected with `require_candidate`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/candidate/profile` | Create profile |
| GET | `/candidate/profile` | View own profile |
| PUT | `/candidate/profile` | Update profile |
| DELETE | `/candidate/profile` | Delete profile |

---

## 👔 HR API

All routes protected with `require_hr`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/hr/profile` | Create HR + company profile |
| GET | `/hr/profile` | View own profile |
| PUT | `/hr/profile` | Update profile |
| DELETE | `/hr/profile` | Delete profile |

---

## 💼 Jobs API

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/jobs/` | HR only | Create job posting |
| GET | `/jobs/` | Public | Browse all active jobs |
| GET | `/jobs/{job_id}` | Public | View single job |
| PUT | `/jobs/{job_id}` | HR only (owner) | Update job |
| DELETE | `/jobs/{job_id}` | HR only (owner) | Delete job |

---

## 📋 Applications API

### Status Flow
```
applied → under_review → shortlisted → interview → selected / rejected
```

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/applications/` | Candidate only | Apply to a job |
| GET | `/applications/my` | Candidate only | View own applications |
| GET | `/applications/job/{job_id}` | HR only | View all applicants for a job |
| PUT | `/applications/{app_id}/status` | HR only | Update application status |
| DELETE | `/applications/{app_id}` | Candidate only | Withdraw application |

---

## 👑 Admin API

All routes protected with `require_admin`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/candidates` | View all candidates |
| GET | `/admin/hrs` | View all HRs |
| GET | `/admin/jobs` | View all job postings |
| GET | `/admin/applications` | View all applications |
| DELETE | `/admin/candidate/{user_id}` | Permanently delete candidate + all data |
| DELETE | `/admin/hr/{user_id}` | Permanently delete HR + all data |

### Cascade Delete Rules

```
Delete Candidate →
  ├── Delete all applications
  ├── Delete candidate profile
  └── Delete user

Delete HR →
  ├── Fetch all jobs by hr_id
  ├── Delete all applications on those jobs
  ├── Delete all jobs
  ├── Delete HR profile
  └── Delete user
```

---

## 🧪 Testing with Swagger

1. Go to `http://localhost:8000/docs`
2. Use `POST /auth/login` to login and copy the `access_token`
3. Click **Authorize** (top right) and enter: `Bearer eyJ...`
4. All protected routes are now accessible with that role

---

## 📌 Coding Standards Followed

| Rule | Detail |
|---|---|
| Max 150 lines/file | Logic split across router, service, schema |
| Modular | Each feature is a self-contained folder |
| No DB code in routes | Routes only call service functions |
| No hardcoding | All config via `.env` and `config.py` |
| Dependency Injection | FastAPI `Depends()` for all auth guards |
| Consistent naming | snake_case files, PascalCase classes |
| Stateless Auth | JWT only — no sessions |

---

## 🚀 Coming Next — Phase 2: AI Features

- 🤖 Resume Skill Extractor (Gemini LLM)
- ✉️ Cover Letter Generator
- 🎯 Skill-JD Matching Engine
- 🗣️ AI Interview Engine
- 💬 RAG-Based HR Chatbot

---

## 👨‍💻 Author

Built with ❤️ using FastAPI + MongoDB Atlas
