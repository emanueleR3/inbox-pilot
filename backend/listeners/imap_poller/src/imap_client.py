import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Dict
import re

class ImapClient:
    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.conn = None

    def connect(self):
        if self.use_ssl:
            self.conn = imaplib.IMAP4_SSL(self.host, self.port)
        else:
            self.conn = imaplib.IMAP4(self.host, self.port)

        self.conn.login(self.username, self.password)
        self.conn.select("INBOX")   # di default seleziono la inbox (TODO pensare eventualmente di andare a controllare anche la spam)

    def _decode_header(self, header_value):
        """
        Decodifica un header dell'email gestendo la codifica.
        """
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_string += str(part)
        
        return decoded_string

    def _extract_email_body(self, msg):
        """
        Estrae il corpo del messaggio (testo e HTML se disponibili).
        """
        body_text = ""
        body_html = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Salta gli allegati
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        else:
            # Messaggio semplice (non multipart)
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            if payload:
                decoded_payload = payload.decode(msg.get_content_charset() or "utf-8", errors="ignore")
                if content_type == "text/plain":
                    body_text = decoded_payload
                elif content_type == "text/html":
                    body_html = decoded_payload
        
        return body_text, body_html

    def _extract_message_id(self, msg):
        """
        Estrae il Message-ID dell'email.
        """
        message_id = msg.get("Message-ID", "")
        return message_id.strip("<>") if message_id else ""

    def _extract_thread_id(self, msg):
        """
        Estrae il Thread-ID se disponibile, altrimenti usa References o In-Reply-To.
        """
        # Prima prova con Thread-Index (Outlook) o Thread-Topic
        thread_id = msg.get("Thread-Index") or msg.get("Thread-Topic")
        
        if not thread_id:
            # Prova con References (RFC standard)
            references = msg.get("References", "")
            if references:
                # Prende il primo Message-ID dalle references
                refs = re.findall(r'<([^>]+)>', references)
                thread_id = refs[0] if refs else ""
            else:
                # Fallback su In-Reply-To
                in_reply_to = msg.get("In-Reply-To", "")
                thread_id = in_reply_to.strip("<>") if in_reply_to else ""
        
        return thread_id

    def fetch_unseen_messages(self) -> List[Dict]:
        """
        Recupera i messaggi non letti con tutti i dati disponibili.
        """
        status, messages = self.conn.search(None, "UNSEEN")
        if status != "OK":
            return []

        mail_ids = messages[0].split()
        emails = []

        for mail_id in mail_ids:
            _, msg_data = self.conn.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Estrae tutti i dati dell'email
            subject = self._decode_header(msg.get("Subject", ""))
            from_address = self._decode_header(msg.get("From", ""))
            to_address = self._decode_header(msg.get("To", ""))
            cc_address = self._decode_header(msg.get("Cc", ""))
            bcc_address = self._decode_header(msg.get("Bcc", ""))
            date_str = msg.get("Date", "")
            
            # Converte la data in formato timestamp
            timestamp = ""
            if date_str:
                try:
                    parsed_date = parsedate_to_datetime(date_str)
                    timestamp = parsed_date.isoformat()
                except:
                    timestamp = date_str

            # Estrae il corpo del messaggio
            body_text, body_html = self._extract_email_body(msg)
            
            # Estrae Message-ID e Thread-ID
            message_id = self._extract_message_id(msg)
            thread_id = self._extract_thread_id(msg)

            email_data = {
                "id": mail_id.decode(),
                "message_id": message_id,
                "thread_id": thread_id,
                "from": from_address,
                "to": to_address,
                "cc": cc_address,
                "bcc": bcc_address,
                "subject": subject,
                "date": date_str,
                "timestamp": timestamp,
                "body_text": body_text,
                "body_html": body_html,
                "raw": raw_email,
                # Metadati aggiuntivi
                "content_type": msg.get_content_type(),
                "charset": msg.get_content_charset() or "utf-8",
                "size": len(raw_email) if raw_email else 0
            }

            emails.append(email_data)

        return emails

    def mark_as_seen(self, mail_id):
        self.conn.store(mail_id, '+FLAGS', '\\Seen')

    def close(self):
        try:
            self.conn.close()
            self.conn.logout()
        except:
            pass