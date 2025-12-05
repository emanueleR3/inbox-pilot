from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, List

from automations.quiz.models import Quiz, CompanyInfo, Address, Question, Answer
from automations.quiz.quiz_chain import QuizChain
from automations.api.db import get_supabase_client


@dataclass
class QuizSession:
    session_id: str
    company_id: str  
    company_info: CompanyInfo
    quiz: Quiz = field(default_factory=lambda: Quiz(id=str(uuid.uuid4()), questions=[], answers=[]))
    chain: QuizChain = field(default_factory=QuizChain)


# Simple in-memory store; consider persisting to Supabase if needed
_SESSIONS: Dict[str, QuizSession] = {}

def get_session_keys() -> List[str]:
    """Return a list of all active session IDs."""
    return list(_SESSIONS.keys())

# TODO create a column in supa for all missing fields (the once that now are None)
def _map_company_to_model(service_row: dict, subscription_row: dict | None) -> CompanyInfo:
    """Map subscription_services + subscriptions rows to CompanyInfo (per provided schema)."""
    sub_address = subscription_row.get("address") if subscription_row else None
    sub_city = subscription_row.get("city") if subscription_row else None
    sub_region = subscription_row.get("region") if subscription_row else None
    sub_postal = subscription_row.get("postal_code") if subscription_row else None
    sub_country = subscription_row.get("country") if subscription_row else None

    sub_name = subscription_row.get("name") if subscription_row else None
    sub_website = subscription_row.get("website") if subscription_row else None
    sub_industry = subscription_row.get("industry") if subscription_row else None
    sub_business_hours = subscription_row.get("business_hours") if subscription_row else None
    sub_employee_count = subscription_row.get("employee_count") if subscription_row else None
    sub_products_services = subscription_row.get("products_services") if subscription_row else None
    sub_ton_of_voice = subscription_row.get("tone_of_voice") if subscription_row else "professional"
    sub_email = service_row.get("email") if service_row else None
    sub_email_signature = service_row.get("email_signature") if service_row else None
    sub_phone_number = service_row.get("phone_number") if service_row else None
    sub_vat = subscription_row.get("vat_number") if subscription_row else None

    address = Address(
        street=sub_address,
        city=sub_city,
        region=sub_region,
        postal_code=sub_postal,
        country=sub_country,
    )

    return CompanyInfo(
        company_name=sub_name,
        website=sub_website,
        industry=sub_industry,
        business_hours=sub_business_hours,
        employee_count=sub_employee_count,
        address=address,
        products_services=sub_products_services,
        tone_of_voice=sub_ton_of_voice,
        email_address=sub_email,
        email_signature=sub_email_signature,
        phone_number=sub_phone_number,
        vat_number=sub_vat,
    )


def fetch_company_info_for_service(service_id: str) -> CompanyInfo:
    supabase = get_supabase_client()
    svc_resp = (
        supabase.table("subscription_services").select("*").eq("service_id", service_id).limit(1).execute()
    )
    if not svc_resp.data:
        return CompanyInfo()
    svc_row = svc_resp.data[0]

    sub_row = None
    if svc_row.get("subscription_id"):
        sub_resp = (
            supabase.table("subscriptions").select("*").eq("subscription_id", svc_row["subscription_id"]).limit(1).execute()
        )
        if sub_resp.data:
            sub_row = sub_resp.data[0]

    return _map_company_to_model(svc_row, sub_row)


def create_session(service_id: str) -> QuizSession:
    company_info = fetch_company_info_for_service(service_id)
    session_id = str(uuid.uuid4())
    sess = QuizSession(session_id=session_id, company_id=service_id, company_info=company_info)
    _SESSIONS[session_id] = sess
    return sess


def get_session(session_id: str) -> Optional[QuizSession]:
    if session_id is None:
        return None

    key = str(session_id)
    key = key.strip().strip('"').strip("'")

    sess = _SESSIONS.get(key)
    if sess:
        return sess

    key_no_dash = key.replace('-', '')
    for k, v in _SESSIONS.items():
        if k.replace('-', '') == key_no_dash:
            return v

    matches = [v for k, v in _SESSIONS.items() if key in k or k in key]
    if matches:
        return matches[0]

    return None


def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)


def append_quiz_answer(service_id: str, question: Question, answer: Answer) -> None:
    """Append the given Q/A to subscription_services.quiz_q_a JSONB array in Supabase."""
    supabase = get_supabase_client()
    resp = (
        supabase.table("subscription_services").select("quiz_q_a").eq("service_id", service_id).limit(1).execute()
    )
    cur = []
    if resp.data and resp.data[0].get("quiz_q_a"):
        cur = resp.data[0]["quiz_q_a"] or []
    cur = list(cur)
    cur.append(
        {
            "question_id": question.id,
            "question_text": question.text,
            "order": question.order,
            "answer": answer.value,
        }
    )
    (
        supabase.table("subscription_services").update({"quiz_q_a": cur}).eq("service_id", service_id).execute()
    )


def persist_quiz_result(service_id: str, markdown: str) -> None:
    """Persist the final extracted markdown into subscription_services.information column."""
    supabase = get_supabase_client()
    (
        supabase.table("subscription_services").update({"information": markdown, "config_completed": True, "activated": True}).eq("service_id", service_id).execute()
    )
