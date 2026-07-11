import os
import uuid
from typing import Optional
from google.cloud import storage
from fastapi import UploadFile
from core.config import settings

# Initialize GCS client
# We assume GOOGLE_APPLICATION_CREDENTIALS is set in the environment or ADC is configured.
bucket_name = settings.GCS_BUCKET_NAME or "note-tube-bucket"
try:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
except Exception as e:
    print(f"Warning: Failed to initialize GCS client: {e}")
    client = None
    bucket = None

async def upload_file_to_bucket(file: UploadFile, content_type: str = None) -> Optional[str]:
    """Uploads a file to GCS and returns the public URL."""
    if not bucket:
        # Fallback to returning a dummy URL for local testing if GCS is unavailable
        print("Warning: GCS bucket not available. Returning dummy URL.")
        return f"https://dummy-storage.com/{uuid.uuid4()}-{file.filename}"

    try:
        # Generate a unique filename to prevent collisions
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"notes/{uuid.uuid4()}{file_extension}"
        
        blob = bucket.blob(unique_filename)
        
        # Read the file bytes
        file_bytes = await file.read()
        
        # Upload
        blob.upload_from_string(
            file_bytes,
            content_type=content_type or file.content_type
        )
        
        # The public URL follows this format:
        public_url = f"https://storage.googleapis.com/{bucket_name}/{unique_filename}"
        return public_url
    except Exception as e:
        print(f"Error uploading file to GCS: {e}")
        return None
