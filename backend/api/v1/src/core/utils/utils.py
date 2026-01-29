import os
import base64
import hashlib
from cryptography.fernet import Fernet
from datetime import datetime
from dotenv import load_dotenv
from pyparsing import Optional
from realtime import List
from api.v1.src.core.model.mailbox import EmailAttachment
from src.core.model.calendar import CalendarEvent, CalendarAttendee, CalendarOrganizer
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

load_dotenv()

_encryption_key_token = None
_cipher_token = None
_encryption_key_pass = None
_cipher_pass = None

def _init_ciphers():
    global _encryption_key_token, _cipher_token, _encryption_key_pass, _cipher_pass
    
    if _cipher_token is not None and _cipher_pass is not None:
        return
    
    encryption_key_token = os.getenv("ENCRYPTION_KEY_TOKEN")
    encryption_key_pass = os.getenv("ENCRYPTION_KEY_PASS")

    if not encryption_key_token:
        raise ValueError("ENCRYPTION_KEY_TOKEN non trovata nelle variabili d'ambiente")
    if not encryption_key_pass:
        raise ValueError("ENCRYPTION_KEY_PASS non trovata nelle variabili d'ambiente")
    
    _encryption_key_token = encryption_key_token.encode()
    key_hash_token = hashlib.sha256(_encryption_key_token).digest()
    _fernet_key_token = base64.urlsafe_b64encode(key_hash_token)
    _cipher_token = Fernet(_fernet_key_token)

    _encryption_key_pass = encryption_key_pass.encode()
    key_hash_pass = hashlib.sha256(_encryption_key_pass).digest()
    _fernet_key_pass = base64.urlsafe_b64encode(key_hash_pass)
    _cipher_pass = Fernet(_fernet_key_pass)


def encrypt_token(token: str, cond: str = "token") -> str:
    if not token:
        return ""
    
    _init_ciphers()
    
    if cond not in ("token", "pass"):
        raise ValueError("cond deve essere 'token' o 'pass'")
    
    cipher = _cipher_token if cond == "token" else _cipher_pass
    
    if cipher is None:
        raise ValueError(f"Cifrario per '{cond}' non inizializzato")
    
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str, cond: str = "token") -> str:
    if not encrypted_token:
        return ""
    
    _init_ciphers()
    
    if cond not in ("token", "pass"):
        raise ValueError("cond deve essere 'token' o 'pass'")
    
    cipher = _cipher_token if cond == "token" else _cipher_pass
    
    if cipher is None:
        raise ValueError(f"Cifrario per '{cond}' non inizializzato")
    
    return cipher.decrypt(encrypted_token.encode()).decode()


def normalize_google_event(event: dict) -> CalendarEvent:
        start_data = event.get("start", {})
        end_data = event.get("end", {})
        
        is_all_day = "date" in start_data
        
        if is_all_day:
            start = datetime.fromisoformat(start_data["date"] + "T00:00:00")
            end = datetime.fromisoformat(end_data["date"] + "T23:59:59")
        else:
            start = datetime.fromisoformat(start_data.get("dateTime", "").replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_data.get("dateTime", "").replace("Z", "+00:00"))
        
        organizer_data = event.get("organizer", {})
        organizer = None
        if organizer_data:
            organizer = CalendarOrganizer(
                email=organizer_data.get("email", ""),
                name=organizer_data.get("displayName")
            )
        
        attendees = []
        for att in event.get("attendees", []):
            attendees.append(CalendarAttendee(
                email=att.get("email", ""),
                name=att.get("displayName"),
                response_status=att.get("responseStatus")
            ))
        
        return CalendarEvent(
            id=event.get("id", ""),
            title=event.get("summary", "Nessun titolo"),
            description=event.get("description"),
            start=start,
            end=end,
            location=event.get("location"),
            organizer=organizer,
            attendees=attendees,
            is_all_day=is_all_day,
            status=event.get("status"),
            html_link=event.get("htmlLink")
        )


def normalize_microsoft_event(event: dict) -> CalendarEvent:
        start_data = event.get("start", {})
        end_data = event.get("end", {})
        
        is_all_day = event.get("isAllDay", False)
        
        start = datetime.fromisoformat(start_data.get("dateTime", "") + "+00:00" if start_data.get("timeZone") == "UTC" else start_data.get("dateTime", ""))
        end = datetime.fromisoformat(end_data.get("dateTime", "") + "+00:00" if end_data.get("timeZone") == "UTC" else end_data.get("dateTime", ""))
        
        organizer_data = event.get("organizer", {}).get("emailAddress", {})
        organizer = None
        if organizer_data:
            organizer = CalendarOrganizer(
                email=organizer_data.get("address", ""),
                name=organizer_data.get("name")
            )
        
        attendees = []
        for att in event.get("attendees", []):
            email_address = att.get("emailAddress", {})
            status_data = att.get("status", {})
            attendees.append(CalendarAttendee(
                email=email_address.get("address", ""),
                name=email_address.get("name"),
                response_status=status_data.get("response")
            ))
        
        status_map = {
            "notStarted": "tentative",
            "inProgress": "confirmed",
            "completed": "confirmed",
            "cancelled": "cancelled"
        }
        
        return CalendarEvent(
            id=event.get("id", ""),
            title=event.get("subject", "Nessun titolo"),
            description=event.get("bodyPreview") or event.get("body", {}).get("content"),
            start=start,
            end=end,
            location=event.get("location", {}).get("displayName"),
            organizer=organizer,
            attendees=attendees,
            is_all_day=is_all_day,
            status=status_map.get(event.get("status", {}).get("response", ""), "confirmed"),
            html_link=event.get("webLink")
        )

def build_mime_message(
        from_email: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        is_html: bool = False
    ) -> str:
        """Costruisce un messaggio MIME per Gmail API."""

        if attachments:
            msg = MIMEMultipart()
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))
            
            for att in attachments:
                part = MIMEBase(*att.content_type.split("/", 1))
                part.set_payload(base64.b64decode(att.content))
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={att.filename}"
                )
                msg.attach(part)
        else:
            content_type = "html" if is_html else "plain"
            msg = MIMEText(body, content_type, "utf-8")

        msg["From"] = from_email
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        
        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)
        if reply_to:
            msg["Reply-To"] = reply_to

        return msg.as_string()