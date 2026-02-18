from fastapi import FastAPI
from app.routers import auth, admin, user, resume_router, job_router

app = FastAPI()


app.include_router(auth.router)
app.include_router(admin.router)
# app.include_router(hr.router)
app.include_router(user.router)
app.include_router(resume_router.router)
app.include_router(job_router.router)
