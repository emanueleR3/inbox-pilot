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
# NOTIFICATION EXCEPTIONS
# =============================================================================


class NotificationTypeRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Notification type is required")


class NotificationSenderEmailRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Sender email is required")


class NotificationBoxEmailRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Box email is required")


class NotificationSubjectRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Subject is required")


class NotificationBodyRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Body is required")


class NotificationTimestampRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Timestamp is required")


class NotificationSendFailedException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Failed to send notification", exc)


# =============================================================================
# SEND EMAIL EXCEPTIONS
# =============================================================================


class EmailRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Email is required")


class SubjectRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Subject is required")


class BodyRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Body is required")


class HashedAccessTokenRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Hashed access token is required")


class SmtpPortRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Smtp port is required")


class SmtpServerRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Smtp server is required")


class SmtpEmailRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Smtp email is required")


class SmtpPasswordRequiredException(BadRequestException):
	def __init__(self):
		super().__init__(detail="Smtp password is required")


class GmailSendFailedException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Failed to send gmail email", exc)


class MicrosoftSendFailedException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Failed to send microsoft email", exc)


class SmtpSendFailedException(InternalServerWithPrefixException):
	def __init__(self, exc: BaseException):
		super().__init__("Failed to send smtp email", exc)


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
