from pydantic import BaseModel
from typing import List, Optional, Any

class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    answer: str
    type: str = "mcq" # can be "mcq" or "descriptive"

class QuestionFeedback(BaseModel):
    question_id: int
    is_correct: bool
    correct_answer: str
    feedback: str
    score: int # usually 0 or 1 for mcq, 0-10 for descriptive

class QuizEvaluationResponse(BaseModel):
    total_score: int
    max_score: int
    feedback: List[QuestionFeedback]
    overall_analysis: str

class QuizAnswer(BaseModel):
    question_id: int
    answer: str

class QuizSubmission(BaseModel):
    answers: List[QuizAnswer]

class QuizResponse(BaseModel):
    id: str
    tutorial_id: str
    questions: List[QuizQuestion]
    created_at: str
    status: str = "pending" # pending, completed
    evaluation: Optional[QuizEvaluationResponse] = None
    user_answers: Optional[List[QuizAnswer]] = None

class PaginatedQuizzes(BaseModel):
    meta: dict
    data: List[QuizResponse]
