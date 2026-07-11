from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
import httpx
from api.utils import schemas, services
from core.dependencies import get_current_user

router = APIRouter(prefix="/utils", tags=["Utility"])

@router.get("/download-image")
async def download_image(url: str = Query(..., description="The public URL of the image to download")):
    """
    Acts as a proxy to download an image from a public bucket and stream it to the client.
    This helps bypass CORS issues if the bucket isn't configured for the client's origin.
    """
    try:
        # httpx client needs to be used in an async context manager or instantiated globally.
        # We use a context manager here for simplicity and safety.
        async def fetch_and_stream():
            async with httpx.AsyncClient() as client:
                async with client.stream('GET', url) as response:
                    if response.status_code != 200:
                        raise HTTPException(status_code=response.status_code, detail="Failed to fetch image")
                    
                    # Yield chunks of the response
                    async for chunk in response.aiter_bytes():
                        yield chunk
                        
        # We also need to get the content-type from a head request or first chunk
        # To make it simple, we do a head request first.
        async with httpx.AsyncClient() as client:
            head_response = await client.head(url)
            content_type = head_response.headers.get("Content-Type", "application/octet-stream")
            
            if head_response.status_code != 200:
                 raise HTTPException(status_code=head_response.status_code, detail="Failed to fetch image")

        return StreamingResponse(fetch_and_stream(), media_type=content_type)
        
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request to fetch image failed: {str(e)}")

@router.post("/rewrite-text", response_model=schemas.RewriteResponse)
async def rewrite_text_api(request: schemas.RewriteRequest, current_user: dict = Depends(get_current_user)):
    """Rewrites text to be clearer and grammatically correct using Groq."""
    result = services.rewrite_text_service(request.text, request.context)
    return result

@router.post("/speech-to-text", response_model=schemas.STTResponse)
async def speech_to_text_api(
    audio_file: UploadFile = File(None),
    audio_url: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Converts speech to text using Groq's Whisper API. Provide either a file or a URL."""
    if audio_file:
        text = await services.speech_to_text_file(audio_file)
    elif audio_url:
        text = await services.speech_to_text_url(audio_url)
    else:
        raise HTTPException(status_code=400, detail="Must provide either audio_file or audio_url")
        
    return {"text": text}
