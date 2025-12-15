from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status


# =============================================================================
# BASE EXCEPTION
# =============================================================================


class APIException(HTTPException):
	def __init__(
		self,
		status_code: int,
		detail: str,
		headers: Optional[dict] = None,
	):
		super().__init__(status_code=status_code, detail=detail, headers=headers)


# =============================================================================
# 400 BAD REQUEST
# =============================================================================


class BadRequestException(APIException):
	def __init__(self, detail: str = "Richiesta non valida"):
		super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# =============================================================================
# 404 NOT FOUND
# =============================================================================


class NotFoundException(APIException):
	def __init__(self, detail: str = "Risorsa non trovata"):
		super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


# =============================================================================
# 500 INTERNAL SERVER ERROR
# =============================================================================


class InternalServerException(APIException):
	def __init__(self, detail: str = "Errore interno del server"):
		super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class InternalServerWithPrefixException(InternalServerException):
	def __init__(self, prefix: str, exc: Optional[BaseException] = None):
		detail = prefix if exc is None else f"{prefix}: {str(exc)}"
		super().__init__(detail=detail)


# =============================================================================
# QUIZ EXCEPTIONS
# =============================================================================


class QuizServiceIdRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Service ID richiesto")


class QuizSessionIdRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Session ID richiesto")


class QuizSessionAndAnswerRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Session ID e risposta sono obbligatori")


class QuizEmailRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Email richiesta")


class QuizSessionNotFoundException(NotFoundException):
	def __init__(self):
		super().__init__(detail="Sessione non trovata")


class QuizNoQuestionsToAnswerException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Nessuna domanda da rispondere. Avvia prima il quiz.")


class QuizErrorStartingException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Errore durante l'avvio del quiz", exc)


class QuizErrorAppendingAnswerException(InternalServerException):
	def __init__(self):
		super().__init__(detail="Errore durante l'aggiunta della risposta al quiz")


class QuizErrorPersistingResultException(InternalServerException):
	def __init__(self):
		super().__init__(detail="Errore durante la persistenza del risultato del quiz")


class QuizErrorSubmittingAnswerException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Errore durante l'invio della risposta", exc)


class QuizErrorGettingStateException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Errore durante il recupero dello stato", exc)


class QuizErrorFinishingException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Errore durante la conclusione del quiz", exc)


class QuizErrorListingSessionsException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Errore durante il recupero delle sessioni", exc)


# =============================================================================
# JERRY EXCEPTIONS
# =============================================================================


class JerryUserIdRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="user_id is required")


class JerryMessageRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="message is required")


class JerryThreadIdRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="thread_id is required")


class JerryToolNameRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="tool_name is required")


class JerryToolParamsRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="tool_params is required")


class JerryThreadNotFoundException(NotFoundException):
	def __init__(self):
		super().__init__(detail="Thread not found or could not be deleted")


class JerryInternalException(InternalServerWithPrefixException):
	def __init__(self, prefix: str, exc: BaseException):
		super().__init__(prefix, exc)


# =============================================================================
# OPTIONAL: EXCEPTION HANDLER REGISTRATION
# =============================================================================


def register_exception_handlers(app):
	from fastapi import Request
	from fastapi.responses import JSONResponse

	@app.exception_handler(APIException)
	async def api_exception_handler(request: Request, exc: APIException):
		return JSONResponse(
			status_code=exc.status_code,
			content={
				"error": True,
				"status_code": exc.status_code,
				"detail": exc.detail,
			},
		)

