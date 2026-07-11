import os
import tempfile
import requests
from groq import Groq
from fastapi import UploadFile
from core.config import settings

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY)

REWRITE_SYSTEM_PROMPT = """You are an expert editor and writing assistant. Your task is to rewrite the user's text to be clearer, more concise, and grammatically correct.
Guidelines:
1. Maintain the original meaning and core message.
2. Fix any grammatical, spelling, or punctuation errors.
3. Improve flow and readability.
4. If the text is already excellent, you may return it as is or make minor polish.
5. Make the text factually correct based on the provided context if it contains inaccuracies.
6. ONLY return the rewritten text. Do not include any explanations, pleasantries, or introductory phrases.
"""

def get_rewrite_prompt(text: str, context: str) -> str:
    return f"Context: {context}\n\nPlease rewrite the following text:\n\n{text}"

def rewrite_text_service(text: str, context: str = "general") -> dict:
    print(f"[Utils] Rewriting text. Original length: {len(text)}")
    if len(text.strip()) < 5:
        return {
            "original_text": text,
            "rewritten_text": text,
            "improvement_applied": False
        }
    
    try:
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": get_rewrite_prompt(text, context)}
        ]
        
        response = client.chat.completions.create(
            model=settings.GROQ_REWRITE_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        rewritten = response.choices[0].message.content.strip()
        improvement_applied = rewritten.lower() != text.lower()
        
        return {
            "original_text": text,
            "rewritten_text": rewritten,
            "improvement_applied": improvement_applied
        }
    except Exception as e:
        print(f"Error in rewrite_text: {str(e)}")
        return {
            "original_text": text,
            "rewritten_text": text,
            "improvement_applied": False
        }

async def speech_to_text_file(audio_file: UploadFile) -> str:
    """Convert uploaded audio file to text using Groq Whisper"""
    print(f"[Utils] Starting STT process for file: {audio_file.filename}")
    try:
        audio_content = await audio_file.read()
        
        # Determine suffix based on content type or filename
        suffix = ".wav"
        if audio_file.filename:
            suffix = os.path.splitext(audio_file.filename)[1]
            
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(audio_content)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            with open(temp_path, "rb") as file_handle:
                transcription = client.audio.transcriptions.create(
                    file=(temp_path, file_handle.read()),
                    model=settings.GROQ_STT_MODEL,
                    response_format="verbose_json",
                )
            return transcription.text
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
    except Exception as e:
        print(f"STT error: {e}")
        return "Sorry, I couldn't understand the audio. Please try again."

async def speech_to_text_url(audio_url: str) -> str:
    """Convert remote audio file to text using Groq Whisper"""
    response = requests.get(audio_url)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as temp_file:
        temp_file.write(response.content)
        temp_file.flush()
        temp_path = temp_file.name

    try:
        with open(temp_path, "rb") as file_handle:
            transcription = client.audio.transcriptions.create(
                file=(temp_path, file_handle.read()),
                model=settings.GROQ_STT_MODEL,
                response_format="verbose_json",
            )
        return transcription.text
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
