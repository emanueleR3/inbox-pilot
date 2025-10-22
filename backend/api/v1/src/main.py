from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware
import uvicorn

from src.core.config import settings
from src.core.logger import setup_logger

# Importa le routes dei vari moduli (man mano che li aggiungi)
from src.modules.auth.src.routes import router as auth_router
from src.modules.subscription_service.src.routes import router as subscription_service_router
# from src.services.mail.src.routes.gmail_routes import router as gmail_router

logger = setup_logger()
app = FastAPI(title="AI Mail Automation API", version="1.0.0")

app.add_middleware(ProxyHeadersMiddleware)

# Middleware per Content Security Policy
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Disabilita completamente CSP per OAuth endpoints (test temporaneo)
    if request.url.path.startswith("/auth/"):
        # Rimuovi qualsiasi CSP esistente per OAuth
        response.headers.pop("Content-Security-Policy", None)
        response.headers.pop("Content-Security-Policy-Report-Only", None)
        
        # Aggiungi header di debug
        response.headers["X-Debug-Path"] = request.url.path
        response.headers["X-Debug-CSP"] = "disabled"
        
        logger.info(f"Disabled CSP for OAuth endpoint: {request.url.path}")
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
        response.headers["X-Debug-CSP"] = "enabled"
    
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