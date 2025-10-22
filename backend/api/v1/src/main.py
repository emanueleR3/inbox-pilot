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


# Debug endpoint per verificare lo scheme della richiesta TODO rimuovere in produzione
@app.get("/debug_scheme")
async def debug_scheme(request: Request):
    return {"scheme": request.url.scheme, "headers": dict(request.headers)}

# Middleware manuale per gestire X-Forwarded-Proto e forzare https se richiesto
@app.middleware("http")
async def forwarded_proto_scheme(request: Request, call_next):
    x_forwarded_proto = request.headers.get("x-forwarded-proto")
    if x_forwarded_proto == "https":
        request.scope["scheme"] = "https"
        # Imposta anche l'header per la port se necessario
        if "host" in request.scope and ":8000" not in request.scope["host"]:
            request.scope["server"] = (request.scope["server"][0], 443)
    return await call_next(request)

# Middleware per Content Security Policy
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Disabilita completamente CSP per OAuth endpoints (test temporaneo)
    if request.url.path.startswith("/auth/"):
        # Rimuovi qualsiasi CSP esistente per OAuth usando il metodo corretto per MutableHeaders
        if "Content-Security-Policy" in response.headers:
            del response.headers["Content-Security-Policy"]
        if "Content-Security-Policy-Report-Only" in response.headers:
            del response.headers["Content-Security-Policy-Report-Only"]
        
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