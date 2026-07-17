# Note Tube Backend

This is the backend API for **Note Tube**, an AI-powered tutorial companion that helps you take smart notes and chat with an AI assistant while watching YouTube videos.

## Tech Stack
- **Framework:** FastAPI (Python)
- **Database:** MongoDB
- **AI/LLM:** Google Gemini API and Groq API
- **Authentication:** JWT (Access & Refresh tokens) with Email OTP verification
- **Cloud Storage:** Google Cloud Bucket (for image/media uploads)

## Features & Modules

- **Authentication (`/auth`)**: User registration, OTP-based login, password reset, token refreshing, and profile stats.
- **Tutorials (`/tutorials`)**: Manage video tutorial sessions, sync YouTube videos with the user's workspace.
- **Notes (`/notes`)**: Timestamped note-taking with support for multiple image attachments per note.
- **Groups & Subgroups (`/groups`)**: Organize tutorials into folders/collections.
- **Chats (`/chats`)**: AI Chat Assistant that answers questions about the video content contextually.
- **Utilities (`/utils`)**: AI-powered text rewriting ("Enhance with AI") and Speech-to-Text (STT) for voice notes.

## Setup Instructions

### Prerequisites
- Python 3.10+
- MongoDB instance (local or Atlas)
- Google Gemini API Key and Groq API Key (for proper fallback)
- Google Cloud Storage Service Account Key (for image/media uploads)
- Gmail Account with App Password (for OTP emails)

### Installation

1. **Clone the repository and enter the directory:**
   ```bash
   cd note-tube-backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory based on `.env.example`

5. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```
   The API will be running at `http://127.0.0.1:8000`. You can view the interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

## Database Indexes
Indexes for MongoDB (like email uniqueness, TTL for OTPs, and compound indexes) are automatically set up when the FastAPI application starts up via the lifespan event in `main.py`.

## License
MIT License
