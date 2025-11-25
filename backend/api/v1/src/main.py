# api/v1/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.config import settings
from src.core.logger import setup_logger

# Importa le routes dei vari moduli (man mano che li aggiungi)
from src.modules.auth.src.routes import router as auth_router
from src.modules.subscription_service.src.routes import router as subscription_service_router
from src.modules.jerry.src.routes import router as jerry_router
# from src.services.mail.src.routes.gmail_routes import router as gmail_router

logger = setup_logger()
app = FastAPI(title="AI Mail Automation API", version="1.0.0")

app.include_router(auth_router, prefix="/auth")
app.include_router(subscription_service_router, prefix="/subscriptionServiceRouter")
app.include_router(jerry_router, prefix="/jerry")

# CORS (puoi restringerlo in produzione)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://corretto.pro", "http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    reload = settings.ENV == "development"
    logger.info(f"### API 📡 Starting API server on port {settings.PORT} in {settings.ENV} mode (reload = {reload})")
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=reload)