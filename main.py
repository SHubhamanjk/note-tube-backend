from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import setup_indexes
from core.config import settings
from api.auth.router import router as auth_router
from api.groups.router import router as groups_router
from api.tutorials.router import router as tutorials_router
from api.notes.router import router as notes_router
from api.utils.router import router as utils_router
from api.chats.router import router as chats_router
from api.quizzes.router import router as quizzes_router
async def lifespan(app: FastAPI):
    # Startup: Create database indexes
    await setup_indexes()
    yield
    # Shutdown logic (if any) can go here

is_prod = settings.ENVIRONMENT.lower() == "prod"

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Lightweight backend for the Note Tube browser extension, which helps you take smart notes and chat with an AI assistant while watching YouTube videos.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(groups_router)
app.include_router(tutorials_router)
app.include_router(notes_router)
app.include_router(utils_router)
app.include_router(chats_router)
app.include_router(quizzes_router)
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": f"{settings.PROJECT_NAME} is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
