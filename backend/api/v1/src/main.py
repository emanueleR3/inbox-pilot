# api/v1/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.config import settings
from src.core.logger import setup_logger
from src.handler_exception import register_exception_handlers

# Importa le routes dei vari moduli (man mano che li aggiungi)
from src.modules.auth.src.routes import router as auth_router
from src.modules.subscription_service.src.routes import router as subscription_service_router
from src.modules.jerry.src.routes import router as jerry_router
from src.modules.metric.src.routes import router as metric_router
from src.modules.scraper.src.routes import router as scraper_router
from src.modules.subscription.src.routes import router as subscription_router
from src.modules.quiz_session.src.routes import router as quiz_router
from src.modules.calendars.src.routes import router as calendars_router
from src.modules.mailbox.src.routes import router as mailbox_router

logger = setup_logger()
app = FastAPI(title="AI Mail Automation API", version="1.0.0")

# Registra gli exception handlers globali
register_exception_handlers(app)

# CORS (puoi restringerlo in produzione) - must be added before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://corretto.pro", "http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(subscription_router, prefix="/subscription")
app.include_router(subscription_service_router, prefix="/subscriptionServiceRouter")
app.include_router(quiz_router, prefix="/quiz")
app.include_router(metric_router, prefix="/metric")
app.include_router(calendars_router, prefix="/calendars")
app.include_router(mailbox_router, prefix="/mailbox")
app.include_router(jerry_router, prefix="/jerry")
app.include_router(metric_router, prefix="/metric")
app.include_router(scraper_router, prefix="/scraper")


@app.get("/health")
async def health_check():
    return {"status": "sei gay"}

if __name__ == "__main__":
    reload = settings.ENV == "development"
    logger.info(f"### API 📡 Starting API server on port {settings.PORT} in {settings.ENV} mode -> reload = {reload}")
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=reload)