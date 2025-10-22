# api/v1/src/main.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.config import settings
from src.core.logger import setup_logger

# Importa le routes dei vari moduli (man mano che li aggiungi)
from src.modules.auth.src.routes import router as auth_router
from src.modules.subscription_service.src.routes import router as subscription_service_router
# from src.services.mail.src.routes.gmail_routes import router as gmail_router

logger = setup_logger()
app = FastAPI(title="AI Mail Automation API", version="1.0.0")

# Middleware per Content Security Policy
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # CSP permissiva per OAuth endpoints
    if request.url.path.startswith("/auth/"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com https://login.microsoftonline.com https://graph.microsoft.com; "
            "form-action 'self' https://accounts.google.com https://login.microsoftonline.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self' https://accounts.google.com https://login.microsoftonline.com"
        )
        logger.info(f"Applied OAuth CSP for path: {request.url.path}")
    else:
        # CSP normale per altre route
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
    
    return response

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(subscription_service_router, prefix="/subscriptionServiceRouter", tags=["SubscriptionServiceRouter"])

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

# Note: Routes già registrate sopra, rimuovo duplicati
# app.include_router(gmail_router, prefix="/mail", tags=["Gmail"])

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)