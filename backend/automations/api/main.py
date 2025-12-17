# api/v1/src/main.py
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
import os
import json
from routers import chatbot_router, quiz_router, workflows_router
from api.handler_exception import register_exception_handlers

load_dotenv()

app = FastAPI(title="Automations API", version="1.0.0")

# Middleware per loggare le richieste
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"🔍 [REQUEST] {request.method} {request.url}")
    print(f"🔍 [HEADERS] {dict(request.headers)}")
    
    # Se è una POST, logga anche il body
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                print(f"🔍 [BODY] {body.decode()[:500]}...")  # Solo primi 500 caratteri
        except Exception as e:
            print(f"⚠️ [REQUEST] Could not read body: {e}")
    
    response = await call_next(request)
    print(f"[RESPONSE] Status: {response.status_code}")
    return response

app.include_router(chatbot_router, prefix="/jerry")
app.include_router(quiz_router, prefix="/internal-quiz")
app.include_router(workflows_router, prefix="/workflows")

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # da limitare in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    current_environment = os.getenv("ENV", "development")
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=(current_environment == "development"))