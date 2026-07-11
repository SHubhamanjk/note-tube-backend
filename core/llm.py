from google import genai
from google.genai import types
from groq import Groq
from core.config import settings

# Initialize providers
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
groq_client = Groq(api_key=settings.GROQ_API_KEY)

async def chat_completion_with_fallback(
    messages: list, 
    system_instruction: str = None, 
    temperature: float = 0.6, 
    max_tokens: int = 4000
) -> str:
    """
    Tries Gemini first, falls back to Groq if it fails.
    """
    
    # 1. Try Gemini
    try:
        # Convert standard OpenAI/Groq format to Gemini format
        gemini_messages = []
        for msg in messages:
            # Skip system messages since they're in system_instruction
            if msg["role"] == "system":
                continue
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_messages.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
            )
            
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        # In the new SDK, chat history is passed via the chats module or contents array
        response = await gemini_client.aio.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL,
            contents=gemini_messages,
            config=config
        )
        return response.text
        
    except Exception as gemini_error:
        print(f"Gemini failed: {gemini_error}. Falling back to Groq.")
        
        # 2. Fallback to Groq
        try:
            groq_messages = []
            if system_instruction:
                groq_messages.append({"role": "system", "content": system_instruction})
            groq_messages.extend(messages)
            
            response = groq_client.chat.completions.create(
                model=settings.GROQ_REWRITE_MODEL, # Using the default fast model we have
                messages=groq_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
            
        except Exception as groq_error:
            print(f"Groq fallback also failed: {groq_error}")
            return "I'm temporarily unable to respond. Please try again in a moment."
