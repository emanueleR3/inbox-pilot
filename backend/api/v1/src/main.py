# api/v1/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.config import settings
from src.core.logger import setup_logger

# Importa le routes dei vari moduli (man mano che li aggiungi)
from src.modules.auth.src.routes import router as auth_router
# from src.services.mail.src.routes.gmail_routes import router as gmail_router

logger = setup_logger()
app = FastAPI(title="AI Mail Automation API", version="1.0.0")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])

# CORS (puoi restringerlo in produzione)
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

# Registra le route modulari
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
# app.include_router(gmail_router, prefix="/mail", tags=["Gmail"])

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)