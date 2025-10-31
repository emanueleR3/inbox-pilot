# api/v1/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import os
from routers import agents_router, chatbot_router, quiz_router

load_dotenv()

app = FastAPI(title="Automations API", version="1.0.0")

app.include_router(agents_router, prefix="/agents")
app.include_router(chatbot_router, prefix="/chatbot")
app.include_router(quiz_router, prefix="/quiz")

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