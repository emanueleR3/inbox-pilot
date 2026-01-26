from typing import Optional, Dict
from datetime import datetime
from src.handler_exception import (
    InvalidFieldException,
    MissingFieldException
)

def build_common_params(req: dict) -> Dict:
    provider = req.get("provider")
    if not provider:
        raise MissingFieldException(fields=["provider"])

    provider = provider.lower()
    if provider not in {"google", "microsoft", "imap"}:
        raise InvalidFieldException(
            field="provider",
            reason="deve essere 'google', 'microsoft' o 'imap'"
        )

    max_results = req.get("max_results", 50)
    if not isinstance(max_results, int) or not 1 <= max_results <= 500:
        raise InvalidFieldException(
            field="max_results",
            reason="deve essere un intero tra 1 e 500"
        )

    include_drafts = req.get("include_drafts", True)
    if not isinstance(include_drafts, bool):
        raise InvalidFieldException(
            field="include_drafts",
            reason="deve essere un valore booleano"
        )

    include_spam_trash = req.get("include_spam_trash", False)
    if not isinstance(include_spam_trash, bool):
        raise InvalidFieldException(
            field="include_spam_trash",
            reason="deve essere un valore booleano"
        )

    time_min = _parse_datetime(req.get("time_min"), "time_min")
    time_max = _parse_datetime(req.get("time_max"), "time_max")

    if time_min and time_max and time_min >= time_max:
        raise InvalidFieldException(
            field="time_min/time_max",
            reason="time_min deve essere precedente a time_max"
        )

    return {
        "provider": provider,
        "time_min": time_min,
        "time_max": time_max,
        "max_results": max_results,
        "include_drafts": include_drafts,
        "include_spam_trash": include_spam_trash,
    }

def build_google_params(req: dict) -> Dict:
    token = req.get("token")
    if not token:
        raise MissingFieldException(fields=["token"])

    params = build_common_params(req)
    params.update({
        "token": token,
        "query": req.get("query")
    })
    return params


def build_microsoft_params(req: dict) -> Dict:
    token = req.get("token")
    if not token:
        raise MissingFieldException(fields=["token"])

    params = build_common_params(req)
    params.update({
        "token": token,
        "folder": req.get("folder", "inbox")
    })
    return params


def build_imap_params(req: dict) -> Dict:
    required = ["imap_server", "imap_port", "email", "password"]
    missing = [f for f in required if not req.get(f)]
    if missing:
        raise MissingFieldException(fields=missing)

    port = req["imap_port"]
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise InvalidFieldException(
            field="imap_port",
            reason="deve essere un intero tra 1 e 65535"
        )

    params = build_common_params(req)
    params.update({
        "imap_server": req["imap_server"],
        "imap_port": port,
        "email_address": req["email"],
        "password": req["password"],
        "folder": req.get("folder", "INBOX"),
    })

    return params


def _parse_datetime(value: Optional[str], field: str) -> Optional[datetime]:
    if value is None:
        return None

    if not isinstance(value, str):
        raise InvalidFieldException(
            field=field,
            reason="deve essere una stringa ISO 8601"
        )

    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        raise InvalidFieldException(
            field=field,
            reason="formato data/ora non valido"
        )

