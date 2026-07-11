from fastapi import APIRouter, status, Depends, Query, BackgroundTasks
from api.quizzes import schemas, service
from core.dependencies import get_current_user

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

@router.post("/tutorial/{tutorial_id}/generate", response_model=schemas.QuizResponse, status_code=status.HTTP_201_CREATED)
async def generate_quiz(
    tutorial_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Generate a dynamic quiz for a tutorial based on its video transcript and notes."""
    user_id = str(current_user["_id"])
    return await service.generate_quiz(user_id, tutorial_id, background_tasks)

@router.post("/{quiz_id}/evaluate", response_model=schemas.QuizEvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_quiz(
    quiz_id: str,
    submission: schemas.QuizSubmission,
    current_user: dict = Depends(get_current_user)
):
    """Evaluate a user's quiz submission and return feedback/scores."""
    user_id = str(current_user["_id"])
    answers_dict = [{"question_id": a.question_id, "answer": a.answer} for a in submission.answers]
    return await service.evaluate_quiz(user_id, quiz_id, answers_dict)

@router.get("/tutorial/{tutorial_id}", response_model=schemas.PaginatedQuizzes, status_code=status.HTTP_200_OK)
async def get_quizzes(
    tutorial_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve paginated generated quizzes for a tutorial."""
    user_id = str(current_user["_id"])
    return await service.get_quizzes(user_id, tutorial_id, skip, limit)
