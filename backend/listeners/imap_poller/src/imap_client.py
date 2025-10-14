import imaplib
import email
from email.header import decode_header
from typing import List, Dict

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

    def fetch_unseen_messages(self) -> List[Dict]:
        """
        Recupera i messaggi non letti.
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

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            from_ = msg.get("From")
            emails.append({
                "id": mail_id.decode(),
                "from": from_,
                "subject": subject,
                "raw": raw_email,
            })

        return emails

    def mark_as_seen(self, mail_id):
        self.conn.store(mail_id, '+FLAGS', '\\Seen')

    def close(self):
        try:
            self.conn.close()
            self.conn.logout()
        except:
            pass