from fastapi import HTTPException, status
from typing import Optional


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class APIException(HTTPException):
    def __init__(
        self, 
        status_code: int, 
        detail: str,
        headers: Optional[dict] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


# =============================================================================
# 400 BAD REQUEST - Errori di validazione e richieste malformate
# =============================================================================

class BadRequestException(APIException):
    def __init__(self, detail: str = "Richiesta non valida"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class MissingFieldException(BadRequestException):
    def __init__(self, fields: list[str]):
        detail = f"Campi obbligatori mancanti: {', '.join(fields)}"
        super().__init__(detail=detail)


class InvalidFieldException(BadRequestException):
    def __init__(self, field: str, reason: str = "valore non valido"):
        detail = f"Campo '{field}' non valido: {reason}"
        super().__init__(detail=detail)


class InvalidEmailException(BadRequestException):
    def __init__(self, email: str = None):
        detail = "Formato email non valido" if not email else f"Email non valida: {email}"
        super().__init__(detail=detail)


class InvalidDateException(BadRequestException):
    def __init__(self, date_field: str = "data"):
        detail = f"Formato {date_field} non valido. Utilizzare formato ISO 8601"
        super().__init__(detail=detail)


class InvalidPortException(BadRequestException):
    def __init__(self, port_type: str = "porta"):
        detail = f"La {port_type} deve essere un numero intero valido"
        super().__init__(detail=detail)


class SubscriptionIdRequiredException(BadRequestException):
    def __init__(self):
        super().__init__(detail="subscription_id è obbligatorio")


# =============================================================================
# 401 UNAUTHORIZED - Errori di autenticazione
# =============================================================================

class UnauthorizedException(APIException):
    def __init__(self, detail: str = "Non autorizzato"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InvalidTokenException(UnauthorizedException):
    def __init__(self, provider: str = None):
        detail = f"Token {provider} non valido" if provider else "Token non valido o scaduto"
        super().__init__(detail=detail)


class InvalidCredentialsException(UnauthorizedException):
    def __init__(self, service: str = None):
        detail = f"Credenziali {service} non valide" if service else "Credenziali non valide"
        super().__init__(detail=detail)


class IMAPAuthenticationException(InvalidCredentialsException):
    def __init__(self):
        super().__init__(service="IMAP")


class SMTPAuthenticationException(InvalidCredentialsException):
    def __init__(self):
        super().__init__(service="SMTP")


# =============================================================================
# 403 FORBIDDEN - Accesso negato
# =============================================================================

class ForbiddenException(APIException):
    def __init__(self, detail: str = "Accesso negato"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class InsufficientPermissionsException(ForbiddenException):
    def __init__(self, operation: str = None):
        detail = f"Permessi insufficienti per: {operation}" if operation else "Permessi insufficienti"
        super().__init__(detail=detail)


# =============================================================================
# 404 NOT FOUND - Risorsa non trovata
# =============================================================================

class NotFoundException(APIException):
    def __init__(self, detail: str = "Risorsa non trovata"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class SubscriptionNotFoundException(NotFoundException):
    def __init__(self, subscription_id: str = None):
        detail = f"Subscription '{subscription_id}' non trovata" if subscription_id else "Subscription non trovata"
        super().__init__(detail=detail)


class UserNotFoundException(NotFoundException):
    def __init__(self, identifier: str = None):
        detail = f"Utente '{identifier}' non trovato" if identifier else "Utente non trovato"
        super().__init__(detail=detail)


# =============================================================================
# 409 CONFLICT - Conflitto di risorse
# =============================================================================

class ConflictException(APIException):
    def __init__(self, detail: str = "Conflitto di risorse"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ResourceAlreadyExistsException(ConflictException):
    def __init__(self, resource: str = "Risorsa"):
        detail = f"{resource} esiste già"
        super().__init__(detail=detail)


# =============================================================================
# 422 UNPROCESSABLE ENTITY - Errori di validazione semantica
# =============================================================================

class UnprocessableEntityException(APIException):
    def __init__(self, detail: str = "Impossibile processare la richiesta"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ValidationException(UnprocessableEntityException):
    def __init__(self, errors: list[str]):
        detail = f"Errori di validazione: {'; '.join(errors)}"
        super().__init__(detail=detail)


# =============================================================================
# 500 INTERNAL SERVER ERROR - Errori interni
# =============================================================================

class InternalServerException(APIException):
    def __init__(self, detail: str = "Errore interno del server"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class DatabaseException(InternalServerException):
    def __init__(self, operation: str = None):
        detail = f"Errore database durante: {operation}" if operation else "Errore database"
        super().__init__(detail=detail)


class MetricsException(InternalServerException):
    def __init__(self, metric_type: str = None, reason: str = None):
        if metric_type and reason:
            detail = f"Errore recupero metriche {metric_type}: {reason}"
        elif metric_type:
            detail = f"Errore recupero metriche {metric_type}"
        else:
            detail = "Errore recupero metriche"
        super().__init__(detail=detail)


class OAuthException(InternalServerException):
    def __init__(self, provider: str = None, reason: str = None):
        if provider and reason:
            detail = f"Errore OAuth {provider}: {reason}"
        elif provider:
            detail = f"Errore durante autenticazione {provider}"
        else:
            detail = "Errore durante il processo di autenticazione OAuth"
        super().__init__(detail=detail)


# =============================================================================
# 502 BAD GATEWAY - Errori di servizi esterni
# =============================================================================

class BadGatewayException(APIException):
    def __init__(self, detail: str = "Errore di comunicazione con servizio esterno"):
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


class ExternalServiceException(BadGatewayException):
    def __init__(self, service: str, reason: str = None):
        detail = f"Errore servizio {service}: {reason}" if reason else f"Servizio {service} non disponibile"
        super().__init__(detail=detail)


class IMAPConnectionException(ExternalServiceException):
    def __init__(self, server: str = None, reason: str = None):
        service = f"IMAP ({server})" if server else "IMAP"
        super().__init__(service=service, reason=reason)


class SMTPConnectionException(ExternalServiceException):
    def __init__(self, server: str = None, reason: str = None):
        service = f"SMTP ({server})" if server else "SMTP"
        super().__init__(service=service, reason=reason)


class GraphAPIException(ExternalServiceException):
    def __init__(self, reason: str = None):
        super().__init__(service="Microsoft Graph", reason=reason)


class GmailAPIException(ExternalServiceException):
    def __init__(self, reason: str = None):
        super().__init__(service="Gmail", reason=reason)


class SubscriptionCreationException(ExternalServiceException):
    def __init__(self, provider: str, reason: str = None):
        super().__init__(service=f"Subscription {provider}", reason=reason)


# =============================================================================
# 503 SERVICE UNAVAILABLE - Servizio non disponibile
# =============================================================================

class ServiceUnavailableException(APIException):
    def __init__(self, detail: str = "Servizio temporaneamente non disponibile"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=detail,
            headers={"Retry-After": "30"}
        )


# =============================================================================
# HELPER FUNCTION PER REGISTRARE EXCEPTION HANDLERS
# =============================================================================

def register_exception_handlers(app):
    from fastapi.responses import JSONResponse
    from fastapi import Request
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail
            }
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Log dell'errore per debugging
        import logging
        logging.error(f"Unhandled exception: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "detail": "Errore interno del server"
            }
        )
