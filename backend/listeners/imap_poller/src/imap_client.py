import imaplib
import email
import ssl
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Dict
import re
from datetime import datetime, timedelta
from src.utils.logger import log_info, log_error

class ImapClient:
    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.conn = None

    def connect(self):
        try:
            if self.use_ssl:
                # Crea un contesto SSL personalizzato per gestire server con configurazioni SSL più vecchie
                ssl_context = ssl.create_default_context()
                # Imposta il livello di sicurezza per permettere chiavi DH più piccole
                ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
                # Consenti protocolli TLS più vecchi se necessario
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1
                
                self.conn = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=ssl_context)
            else:
                self.conn = imaplib.IMAP4(self.host, self.port)

            self.conn.login(self.username, self.password)
            self.conn.select("INBOX")   # di default seleziono la inbox (TODO pensare eventualmente di andare a controllare anche la spam)
            
        except ssl.SSLError as e:
            # Prova con un contesto SSL ancora più permissivo
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                ssl_context.set_ciphers('ALL:@SECLEVEL=0')
                
                self.conn = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=ssl_context)
                self.conn.login(self.username, self.password)
                self.conn.select("INBOX")
            except Exception as fallback_e:
                log_error(f"Errore SSL per {self.host}: {str(fallback_e)}")
                raise
        except Exception as e:
            log_error(f"Errore connessione IMAP per {self.username}: {str(e)}")
            raise

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

    def _is_email_recent(self, date_str: str) -> bool:
        """
        Controlla se un'email è stata inviata dopo ieri.
        
        Args:
            date_str: Stringa data dell'email
            
        Returns:
            True se l'email è recente (inviata dopo ieri), False altrimenti
        """
        if not date_str:
            return False
            
        try:
            parsed_date = parsedate_to_datetime(date_str)
            # Calcola la data di ieri a mezzanotte
            yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            
            # Converte anche parsed_date in timezone naive se necessario per il confronto
            if parsed_date.tzinfo is not None:
                # Converte in UTC e poi rimuove timezone info per il confronto
                parsed_date = parsed_date.utctimetuple()
                parsed_date = datetime(*parsed_date[:6])
            
            return parsed_date > yesterday
        except Exception as e:
            log_error(f"Errore nel parsing della data {date_str}: {str(e)}")
            # In caso di errore nel parsing, consideriamo l'email come recente per sicurezza
            return True

    def fetch_unseen_messages(self) -> List[Dict]:
        """
        Recupera i messaggi non letti inviati dopo ieri.
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
            
            # Controlla se l'email è recente (inviata dopo ieri)
            if not self._is_email_recent(date_str):
                continue  # Salta le email vecchie
            
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
            if self.conn:
                self.conn.close()
                self.conn.logout()
        except Exception as e:
            log_error(f"Errore durante chiusura connessione IMAP per {self.username}: {str(e)}")