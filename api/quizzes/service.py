import json
from fastapi import HTTPException
from bson import ObjectId
from core.database import get_quiz_collection, get_tutorial_collection, get_note_collection
from core.utils import get_ist_now
from core.llm import chat_completion_with_fallback
from core.prompts import QUIZ_GENERATION_PROMPT, QUIZ_EVALUATION_PROMPT
from api.tutorials.service import increment_counters
from fastapi import BackgroundTasks

async def verify_tutorial_ownership(user_id: str, tutorial_id: str) -> dict:
    print(f"[Quizzes] Verifying ownership of tutorial {tutorial_id} for user {user_id}")
    tutorials = get_tutorial_collection()
    try:
        obj_id = ObjectId(tutorial_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")
        
    tutorial = await tutorials.find_one({"_id": obj_id, "user_id": user_id})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or permission denied")
    return tutorial

def clean_json_response(response: str) -> str:
    """Removes markdown code blocks if the LLM included them."""
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    return response.strip()

async def generate_quiz(user_id: str, tutorial_id: str, background_tasks: BackgroundTasks) -> dict:
    print(f"[Quizzes] Starting quiz generation for tutorial {tutorial_id} by user {user_id}")
    tutorial = await verify_tutorial_ownership(user_id, tutorial_id)
    notes_coll = get_note_collection()
    quizzes_coll = get_quiz_collection()
    
    # Context gathering
    context_parts = []
    context_parts.append(f"Tutorial: {tutorial.get('title', 'Unknown')}")
    
    transcript = tutorial.get('transcript')
    if transcript:
        # Assuming the transcript is a list of dicts stored in cache
        if isinstance(transcript, list):
            full_text = " ".join([t['text'] for t in transcript])
            transcript_text = full_text[:15000]
        else:
            transcript_text = str(transcript)[:15000]
        context_parts.append(f"\nTranscript Excerpt:\n{transcript_text}\n")
        
    notes_cursor = notes_coll.find({"tutorial_id": tutorial_id, "user_id": user_id}).sort("created_at", 1)
    notes_list = await notes_cursor.to_list(length=None)
    if notes_list:
        context_parts.append("\nUser Notes:")
        for note in notes_list:
            if note.get('note_content'):
                context_parts.append(f"- {note['note_content']}")
                
    context_message = "\n".join(context_parts)
    user_prompt = f"Please generate a quiz based on the following context:\n\n{context_message}"
    
    print(f"[Quizzes] Calling LLM orchestrator for quiz generation")
    # Call LLM
    response_text = await chat_completion_with_fallback(
        messages=[{"role": "user", "content": user_prompt}],
        system_instruction=QUIZ_GENERATION_PROMPT
    )
    
    print(f"[Quizzes] Received LLM response for generation, length: {len(response_text)}")
    cleaned_json = clean_json_response(response_text)
    
    try:
        questions = json.loads(cleaned_json)
        # Ensure it's a list
        if not isinstance(questions, list):
            if isinstance(questions, dict) and "questions" in questions:
                questions = questions["questions"]
            else:
                raise ValueError("Expected a JSON array of questions.")
    except Exception as e:
        print(f"Failed to parse generated quiz: {e}\nRaw: {cleaned_json}")
        raise HTTPException(status_code=500, detail="Failed to generate a valid quiz format. Please try again.")
        
    quiz_doc = {
        "tutorial_id": tutorial_id,
        "user_id": user_id,
        "questions": questions,
        "created_at": get_ist_now(),
        "status": "pending"
    }
    
    result = await quizzes_coll.insert_one(quiz_doc)
    quiz_doc["id"] = str(result.inserted_id)
    
    # Assuming tutorials have number_of_quizzes
    tutorials = get_tutorial_collection()
    background_tasks.add_task(
        tutorials.update_one,
        {"_id": tutorial["_id"]},
        {"$inc": {"number_of_quizzes": 1}}
    )
    
    if "created_at" in quiz_doc and hasattr(quiz_doc["created_at"], "isoformat"):
        quiz_doc["created_at"] = quiz_doc["created_at"].isoformat()
        
    return quiz_doc

async def evaluate_quiz(user_id: str, quiz_id: str, answers: list) -> dict:
    print(f"[Quizzes] Evaluating quiz {quiz_id} for user {user_id}")
    quizzes = get_quiz_collection()
    try:
        obj_id = ObjectId(quiz_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid quiz ID")
        
    quiz = await quizzes.find_one({"_id": obj_id, "user_id": user_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    if quiz.get("status") == "completed":
        # Already evaluated, just return the existing evaluation if needed, but for simplicity let's re-eval or block
        # Usually we want to return the evaluation data. 
        pass
        
    user_prompt = "Original Quiz:\n" + json.dumps(quiz["questions"], indent=2) + "\n\nStudent Answers:\n" + json.dumps(answers, indent=2)
    
    print(f"[Quizzes] Calling LLM orchestrator for quiz evaluation")
    response_text = await chat_completion_with_fallback(
        messages=[{"role": "user", "content": user_prompt}],
        system_instruction=QUIZ_EVALUATION_PROMPT
    )
    
    print(f"[Quizzes] Received LLM response for evaluation, length: {len(response_text)}")
    cleaned_json = clean_json_response(response_text)
    
    try:
        evaluation = json.loads(cleaned_json)
    except Exception as e:
        print(f"Failed to parse quiz evaluation: {e}\nRaw: {cleaned_json}")
        raise HTTPException(status_code=500, detail="Failed to evaluate the quiz properly. Please try again.")
        
    # Save evaluation to db
    await quizzes.update_one(
        {"_id": obj_id},
        {"$set": {
            "status": "completed",
            "evaluation": evaluation,
            "user_answers": answers,
            "evaluated_at": get_ist_now()
        }}
    )
    
    return evaluation

async def get_quizzes(user_id: str, tutorial_id: str, skip: int = 0, limit: int = 50) -> dict:
    print(f"[Quizzes] Fetching quizzes for tutorial {tutorial_id}, user {user_id} (skip={skip}, limit={limit})")
    await verify_tutorial_ownership(user_id, tutorial_id)
    quizzes = get_quiz_collection()
    
    total = await quizzes.count_documents({"tutorial_id": tutorial_id, "user_id": user_id})
    cursor = quizzes.find({"tutorial_id": tutorial_id, "user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    formatted = []
    for doc in docs:
        doc["id"] = str(doc["_id"])
        if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
            doc["created_at"] = doc["created_at"].isoformat()
        formatted.append(doc)
        
    return {
        "meta": {
            "total": total,
            "skip": skip,
            "limit": limit
        },
        "data": formatted
    }
