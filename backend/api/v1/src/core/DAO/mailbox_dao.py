import httpx
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import Optional
import base64
import re

from src.core.database import get_supabase_client
from src.core.model.mailbox import (
    EmailThread, 
    EmailMessage, 
    EmailAddress, 
    EmailAttachment
)
from src.core.utils.utils import decrypt_token
from src.handler_exception import (
    GmailAPIException,
    GraphAPIException,
    InvalidTokenException,
    IMAPConnectionException,
    IMAPAuthenticationException
)


class MailboxDAO:
    def __init__(self):
        self.supabase = get_supabase_client()

    # =========================================================================
    # GMAIL API
    # =========================================================================

    async def fetch_gmail_threads(
        self,
        token: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        include_drafts: bool = True,
        include_spam_trash: bool = False,
        query: Optional[str] = None
    ) -> list[EmailThread]:
        decrypted_token = decrypt_token(token, "token")
        
        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Accept": "application/json"
        }

        # Costruisci la query per Gmail
        q_parts = []
        if query:
            q_parts.append(query)
        if time_min:
            q_parts.append(f"after:{int(time_min.timestamp())}")
        if time_max:
            q_parts.append(f"before:{int(time_max.timestamp())}")

        params = {
            "maxResults": max_results,
            "includeSpamTrash": include_spam_trash
        }
        if q_parts:
            params["q"] = " ".join(q_parts)

        try:
            async with httpx.AsyncClient() as client:
                # 1. Recupera la lista dei thread
                threads_url = "https://gmail.googleapis.com/gmail/v1/users/me/threads"
                response = await client.get(
                    threads_url, 
                    headers=headers, 
                    params=params, 
                    timeout=30.0
                )

                if response.status_code == 401:
                    raise InvalidTokenException(provider="Google")

                if response.status_code != 200:
                    raise GmailAPIException(
                        reason=f"Status code {response.status_code}: {response.text}"
                    )

                data = response.json()
                thread_list = data.get("threads", [])

                if not thread_list:
                    return []

                # 2. Recupera i dettagli di ogni thread
                threads = []
                for thread_info in thread_list:
                    thread_id = thread_info.get("id")
                    thread_detail = await self._fetch_gmail_thread_detail(
                        client, headers, thread_id
                    )
                    if thread_detail:
                        threads.append(thread_detail)

                # 3. Se include_drafts, recupera anche i draft e associali ai thread
                if include_drafts:
                    drafts = await self._fetch_gmail_drafts(client, headers)
                    threads = self._merge_drafts_into_threads(threads, drafts)

                return threads

        except httpx.TimeoutException:
            raise GmailAPIException(reason="Timeout durante la richiesta")
        except httpx.RequestError as e:
            raise GmailAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GmailAPIException:
            raise
        except Exception as e:
            raise GmailAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def _fetch_gmail_thread_detail(
        self, 
        client: httpx.AsyncClient, 
        headers: dict, 
        thread_id: str
    ) -> Optional[EmailThread]:
        """Recupera i dettagli completi di un thread Gmail."""
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
        params = {"format": "full"}

        response = await client.get(url, headers=headers, params=params, timeout=30.0)
        
        if response.status_code != 200:
            return None

        data = response.json()
        messages_data = data.get("messages", [])

        messages = []
        participants_set = set()
        has_attachments = False
        has_drafts = False
        is_unread = False
        labels_set = set()
        subject = None
        last_date = None

        for msg_data in messages_data:
            msg = self._parse_gmail_message(msg_data)
            messages.append(msg)

            # Raccogli informazioni aggregate
            if msg.from_address:
                participants_set.add((msg.from_address.email, msg.from_address.name))
            for addr in msg.to_addresses + msg.cc_addresses:
                participants_set.add((addr.email, addr.name))

            if msg.attachments:
                has_attachments = True
            if msg.is_draft:
                has_drafts = True
            if not msg.is_read:
                is_unread = True
            labels_set.update(msg.labels)

            if not subject and msg.subject:
                subject = msg.subject
            if msg.date and (not last_date or msg.date > last_date):
                last_date = msg.date

        participants = [
            EmailAddress(email=email, name=name) 
            for email, name in participants_set
        ]

        return EmailThread(
            id=thread_id,
            subject=subject,
            snippet=data.get("snippet"),
            messages=messages,
            message_count=len(messages),
            has_drafts=has_drafts,
            has_attachments=has_attachments,
            participants=participants,
            last_message_date=last_date,
            is_unread=is_unread,
            labels=list(labels_set)
        )

    def _parse_gmail_message(self, msg_data: dict) -> EmailMessage:
        """Parsa un messaggio Gmail nel formato EmailMessage."""
        payload = msg_data.get("payload", {})
        headers_list = payload.get("headers", [])
        
        headers = {h["name"].lower(): h["value"] for h in headers_list}
        
        labels = msg_data.get("labelIds", [])
        is_draft = "DRAFT" in labels
        is_read = "UNREAD" not in labels

        # Estrai corpo del messaggio
        body_text, body_html = self._extract_gmail_body(payload)

        # Estrai allegati
        attachments = self._extract_gmail_attachments(payload)

        # Parsa la data
        date = None
        if "date" in headers:
            try:
                date = email.utils.parsedate_to_datetime(headers["date"])
            except:
                pass

        return EmailMessage(
            id=msg_data.get("id", ""),
            subject=headers.get("subject"),
            snippet=msg_data.get("snippet"),
            body_text=body_text,
            body_html=body_html,
            from_address=self._parse_email_address(headers.get("from")),
            to_addresses=self._parse_email_addresses(headers.get("to")),
            cc_addresses=self._parse_email_addresses(headers.get("cc")),
            bcc_addresses=self._parse_email_addresses(headers.get("bcc")),
            date=date,
            is_read=is_read,
            is_draft=is_draft,
            attachments=attachments,
            labels=labels
        )

    def _extract_gmail_body(self, payload: dict) -> tuple[Optional[str], Optional[str]]:
        """Estrae il corpo text e html da un payload Gmail."""
        body_text = None
        body_html = None

        def extract_from_parts(parts):
            nonlocal body_text, body_html
            for part in parts:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain" and not body_text:
                    data = part.get("body", {}).get("data")
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif mime_type == "text/html" and not body_html:
                    data = part.get("body", {}).get("data")
                    if data:
                        body_html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif "parts" in part:
                    extract_from_parts(part["parts"])

        if "parts" in payload:
            extract_from_parts(payload["parts"])
        else:
            mime_type = payload.get("mimeType", "")
            data = payload.get("body", {}).get("data")
            if data:
                decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                if mime_type == "text/plain":
                    body_text = decoded
                elif mime_type == "text/html":
                    body_html = decoded

        return body_text, body_html

    def _extract_gmail_attachments(self, payload: dict) -> list[EmailAttachment]:
        """Estrae informazioni sugli allegati da un payload Gmail."""
        attachments = []

        def extract_from_parts(parts):
            for part in parts:
                filename = part.get("filename")
                if filename:
                    attachments.append(EmailAttachment(
                        filename=filename,
                        mime_type=part.get("mimeType"),
                        size=part.get("body", {}).get("size")
                    ))
                if "parts" in part:
                    extract_from_parts(part["parts"])

        if "parts" in payload:
            extract_from_parts(payload["parts"])

        return attachments

    async def _fetch_gmail_drafts(
        self, 
        client: httpx.AsyncClient, 
        headers: dict
    ) -> list[dict]:
        """Recupera tutti i draft da Gmail."""
        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        response = await client.get(url, headers=headers, timeout=30.0)

        if response.status_code != 200:
            return []

        data = response.json()
        drafts_list = data.get("drafts", [])
        
        drafts = []
        for draft_info in drafts_list:
            draft_id = draft_info.get("id")
            draft_url = f"https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}"
            draft_response = await client.get(
                draft_url, 
                headers=headers, 
                params={"format": "full"},
                timeout=30.0
            )
            if draft_response.status_code == 200:
                drafts.append(draft_response.json())

        return drafts

    def _merge_drafts_into_threads(
        self, 
        threads: list[EmailThread], 
        drafts: list[dict]
    ) -> list[EmailThread]:
        """Associa i draft ai rispettivi thread."""
        thread_map = {t.id: t for t in threads}

        for draft in drafts:
            message_data = draft.get("message", {})
            thread_id = message_data.get("threadId")
            
            if thread_id and thread_id in thread_map:
                draft_msg = self._parse_gmail_message(message_data)
                draft_msg.is_draft = True
                
                # Aggiungi il draft al thread esistente
                thread = thread_map[thread_id]
                # Evita duplicati
                if not any(m.id == draft_msg.id for m in thread.messages):
                    thread.messages.append(draft_msg)
                    thread.has_drafts = True
                    thread.message_count = len(thread.messages)

        return threads

    def _parse_email_address(self, raw: Optional[str]) -> Optional[EmailAddress]:
        """Parsa una stringa email in EmailAddress."""
        if not raw:
            return None
        
        # Pattern: "Name <email@example.com>" o "email@example.com"
        match = re.match(r'^"?([^"<]*)"?\s*<?([^>]+@[^>]+)>?$', raw.strip())
        if match:
            name = match.group(1).strip() or None
            email_addr = match.group(2).strip()
            return EmailAddress(email=email_addr, name=name)
        
        return EmailAddress(email=raw.strip())

    def _parse_email_addresses(self, raw: Optional[str]) -> list[EmailAddress]:
        """Parsa una lista di indirizzi email separati da virgola."""
        if not raw:
            return []
        
        addresses = []
        for addr in raw.split(","):
            parsed = self._parse_email_address(addr.strip())
            if parsed:
                addresses.append(parsed)
        
        return addresses

    # =========================================================================
    # MICROSOFT GRAPH API
    # =========================================================================

    async def fetch_microsoft_threads(
        self,
        token: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        include_drafts: bool = True,
        include_spam_trash: bool = False,
        folder: str = "inbox"
    ) -> list[EmailThread]:
        """
        Recupera i thread di email da Microsoft Graph API.
        Microsoft usa conversationId per raggruppare i messaggi.
        """
        decrypted_token = decrypt_token(token, "token")

        headers = {
            "Authorization": f"Bearer {decrypted_token}",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient() as client:
                # 1. Recupera i messaggi dalla cartella specificata
                messages = await self._fetch_microsoft_messages(
                    client, headers, folder, time_min, time_max, max_results
                )

                # 2. Se include_drafts, recupera anche i draft
                if include_drafts:
                    drafts = await self._fetch_microsoft_messages(
                        client, headers, "drafts", time_min, time_max, max_results
                    )
                    messages.extend(drafts)

                # 3. Raggruppa i messaggi per conversationId
                threads = self._group_microsoft_messages_by_conversation(messages)

                return threads[:max_results]

        except httpx.TimeoutException:
            raise GraphAPIException(reason="Timeout durante la richiesta")
        except httpx.RequestError as e:
            raise GraphAPIException(reason=f"Errore di connessione: {str(e)}")
        except InvalidTokenException:
            raise
        except GraphAPIException:
            raise
        except Exception as e:
            raise GraphAPIException(reason=f"Errore inaspettato: {str(e)}")

    async def _fetch_microsoft_messages(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        folder: str,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        max_results: int
    ) -> list[dict]:
        """Recupera i messaggi da una cartella Microsoft."""
        url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"

        params = {
            "$top": max_results,
            "$orderby": "receivedDateTime desc",
            "$select": "id,conversationId,subject,bodyPreview,body,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,isDraft,isRead,hasAttachments,categories"
        }

        filters = []
        if time_min:
            filters.append(f"receivedDateTime ge {time_min.isoformat()}Z")
        if time_max:
            filters.append(f"receivedDateTime le {time_max.isoformat()}Z")

        if filters:
            params["$filter"] = " and ".join(filters)

        response = await client.get(url, headers=headers, params=params, timeout=30.0)

        if response.status_code == 401:
            raise InvalidTokenException(provider="Microsoft")

        if response.status_code != 200:
            # Cartella non trovata è ok, ritorna lista vuota
            if response.status_code == 404:
                return []
            raise GraphAPIException(
                reason=f"Status code {response.status_code}: {response.text}"
            )

        data = response.json()
        return data.get("value", [])

    def _group_microsoft_messages_by_conversation(
        self, 
        messages: list[dict]
    ) -> list[EmailThread]:
        """Raggruppa i messaggi Microsoft per conversationId."""
        conversations = {}

        for msg_data in messages:
            conv_id = msg_data.get("conversationId", msg_data.get("id"))
            
            if conv_id not in conversations:
                conversations[conv_id] = []
            conversations[conv_id].append(msg_data)

        threads = []
        for conv_id, msgs in conversations.items():
            # Ordina per data
            msgs.sort(key=lambda x: x.get("receivedDateTime", ""), reverse=False)
            
            parsed_messages = []
            participants_set = set()
            has_attachments = False
            has_drafts = False
            is_unread = False
            labels_set = set()
            subject = None
            last_date = None

            for msg_data in msgs:
                msg = self._parse_microsoft_message(msg_data)
                parsed_messages.append(msg)

                if msg.from_address:
                    participants_set.add((msg.from_address.email, msg.from_address.name))
                for addr in msg.to_addresses + msg.cc_addresses:
                    participants_set.add((addr.email, addr.name))

                if msg.attachments:
                    has_attachments = True
                if msg.is_draft:
                    has_drafts = True
                if not msg.is_read:
                    is_unread = True
                labels_set.update(msg.labels)

                if not subject and msg.subject:
                    subject = msg.subject
                if msg.date and (not last_date or msg.date > last_date):
                    last_date = msg.date

            participants = [
                EmailAddress(email=email, name=name)
                for email, name in participants_set
            ]

            threads.append(EmailThread(
                id=conv_id,
                subject=subject,
                snippet=msgs[0].get("bodyPreview") if msgs else None,
                messages=parsed_messages,
                message_count=len(parsed_messages),
                has_drafts=has_drafts,
                has_attachments=has_attachments,
                participants=participants,
                last_message_date=last_date,
                is_unread=is_unread,
                labels=list(labels_set)
            ))

        # Ordina per ultima data
        threads.sort(key=lambda t: t.last_message_date or datetime.min, reverse=True)
        return threads

    def _parse_microsoft_message(self, msg_data: dict) -> EmailMessage:
        """Parsa un messaggio Microsoft nel formato EmailMessage."""
        body = msg_data.get("body", {})
        body_text = None
        body_html = None

        if body.get("contentType") == "text":
            body_text = body.get("content")
        elif body.get("contentType") == "html":
            body_html = body.get("content")

        # Parsa la data
        date = None
        received_dt = msg_data.get("receivedDateTime")
        if received_dt:
            try:
                date = datetime.fromisoformat(received_dt.replace("Z", "+00:00"))
            except:
                pass

        # Parsa mittente
        from_data = msg_data.get("from", {}).get("emailAddress", {})
        from_address = EmailAddress(
            email=from_data.get("address", ""),
            name=from_data.get("name")
        ) if from_data.get("address") else None

        # Parsa destinatari
        to_addresses = [
            EmailAddress(
                email=r.get("emailAddress", {}).get("address", ""),
                name=r.get("emailAddress", {}).get("name")
            )
            for r in msg_data.get("toRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]

        cc_addresses = [
            EmailAddress(
                email=r.get("emailAddress", {}).get("address", ""),
                name=r.get("emailAddress", {}).get("name")
            )
            for r in msg_data.get("ccRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]

        bcc_addresses = [
            EmailAddress(
                email=r.get("emailAddress", {}).get("address", ""),
                name=r.get("emailAddress", {}).get("name")
            )
            for r in msg_data.get("bccRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]

        # Allegati (solo flag, non dettagli)
        attachments = []
        if msg_data.get("hasAttachments"):
            attachments = [EmailAttachment(filename="attachment", mime_type=None, size=None)]

        return EmailMessage(
            id=msg_data.get("id", ""),
            subject=msg_data.get("subject"),
            snippet=msg_data.get("bodyPreview"),
            body_text=body_text,
            body_html=body_html,
            from_address=from_address,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            bcc_addresses=bcc_addresses,
            date=date,
            is_read=msg_data.get("isRead", False),
            is_draft=msg_data.get("isDraft", False),
            attachments=attachments,
            labels=msg_data.get("categories", [])
        )

    # =========================================================================
    # IMAP
    # =========================================================================

    async def fetch_imap_threads(
        self,
        imap_server: str,
        imap_port: int,
        email_address: str,
        password: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        include_drafts: bool = True,
        folder: str = "INBOX"
    ) -> list[EmailThread]:
        """
        Recupera i thread di email via IMAP.
        Raggruppa i messaggi per subject (threading semplificato).
        """
        decrypted_password = decrypt_token(password, "pass")

        try:
            # Connessione IMAP
            if imap_port == 993:
                mail = imaplib.IMAP4_SSL(imap_server, imap_port)
            else:
                mail = imaplib.IMAP4(imap_server, imap_port)
                mail.starttls()

            try:
                mail.login(email_address, decrypted_password)
            except imaplib.IMAP4.error as e:
                raise IMAPAuthenticationException()

            messages = []

            # Recupera messaggi dalla cartella principale
            folder_messages = self._fetch_imap_folder_messages(
                mail, folder, time_min, time_max, max_results
            )
            messages.extend(folder_messages)

            # Se include_drafts, recupera anche dalla cartella Drafts
            if include_drafts:
                draft_folders = ["Drafts", "[Gmail]/Drafts", "INBOX.Drafts", "Draft"]
                for draft_folder in draft_folders:
                    try:
                        draft_messages = self._fetch_imap_folder_messages(
                            mail, draft_folder, time_min, time_max, max_results, is_draft=True
                        )
                        messages.extend(draft_messages)
                        break  # Trovata la cartella draft
                    except:
                        continue

            mail.logout()

            # Raggruppa per subject (threading semplificato)
            threads = self._group_imap_messages_by_subject(messages)
            return threads[:max_results]

        except IMAPAuthenticationException:
            raise
        except imaplib.IMAP4.error as e:
            raise IMAPConnectionException(server=imap_server, reason=str(e))
        except Exception as e:
            raise IMAPConnectionException(server=imap_server, reason=f"Errore inaspettato: {str(e)}")

    def _fetch_imap_folder_messages(
        self,
        mail: imaplib.IMAP4,
        folder: str,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        max_results: int,
        is_draft: bool = False
    ) -> list[EmailMessage]:
        """Recupera i messaggi da una cartella IMAP."""
        messages = []

        try:
            status, _ = mail.select(folder, readonly=True)
            if status != "OK":
                return []
        except:
            return []

        # Costruisci criteri di ricerca
        search_criteria = []
        if time_min:
            search_criteria.append(f'SINCE {time_min.strftime("%d-%b-%Y")}')
        if time_max:
            search_criteria.append(f'BEFORE {time_max.strftime("%d-%b-%Y")}')

        search_str = " ".join(search_criteria) if search_criteria else "ALL"

        status, msg_ids = mail.search(None, search_str)
        if status != "OK":
            return []

        msg_id_list = msg_ids[0].split()
        # Prendi gli ultimi max_results messaggi
        msg_id_list = msg_id_list[-max_results:]

        for msg_id in reversed(msg_id_list):
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822 FLAGS)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                flags = msg_data[0][0].decode() if msg_data[0][0] else ""

                email_msg = email.message_from_bytes(raw_email)
                parsed_msg = self._parse_imap_message(email_msg, msg_id.decode(), flags, is_draft)
                messages.append(parsed_msg)
            except Exception:
                continue

        return messages

    def _parse_imap_message(
        self, 
        email_msg: email.message.Message, 
        msg_id: str,
        flags: str,
        is_draft: bool = False
    ) -> EmailMessage:
        """Parsa un messaggio IMAP nel formato EmailMessage."""
        # Decodifica subject
        subject_header = email_msg.get("Subject", "")
        subject = self._decode_mime_header(subject_header)

        # Parsa data
        date = None
        date_header = email_msg.get("Date")
        if date_header:
            try:
                date = email.utils.parsedate_to_datetime(date_header)
            except:
                pass

        # Estrai corpo
        body_text, body_html = self._extract_imap_body(email_msg)

        # Estrai allegati
        attachments = self._extract_imap_attachments(email_msg)

        # Determina se letto
        is_read = "\\Seen" in flags

        return EmailMessage(
            id=msg_id,
            subject=subject,
            snippet=body_text[:200] if body_text else None,
            body_text=body_text,
            body_html=body_html,
            from_address=self._parse_email_address(
                self._decode_mime_header(email_msg.get("From", ""))
            ),
            to_addresses=self._parse_email_addresses(
                self._decode_mime_header(email_msg.get("To", ""))
            ),
            cc_addresses=self._parse_email_addresses(
                self._decode_mime_header(email_msg.get("Cc", ""))
            ),
            bcc_addresses=self._parse_email_addresses(
                self._decode_mime_header(email_msg.get("Bcc", ""))
            ),
            date=date,
            is_read=is_read,
            is_draft=is_draft,
            attachments=attachments,
            labels=[]
        )

    def _decode_mime_header(self, header: str) -> str:
        """Decodifica un header MIME."""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                charset = charset or "utf-8"
                try:
                    result.append(part.decode(charset, errors="ignore"))
                except:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(part)
        return "".join(result)

    def _extract_imap_body(
        self, 
        email_msg: email.message.Message
    ) -> tuple[Optional[str], Optional[str]]:
        """Estrae il corpo text e html da un messaggio IMAP."""
        body_text = None
        body_html = None

        if email_msg.is_multipart():
            for part in email_msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain" and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="ignore")
                elif content_type == "text/html" and not body_html:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body_html = payload.decode(charset, errors="ignore")
        else:
            content_type = email_msg.get_content_type()
            payload = email_msg.get_payload(decode=True)
            if payload:
                charset = email_msg.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="ignore")
                if content_type == "text/plain":
                    body_text = decoded
                elif content_type == "text/html":
                    body_html = decoded

        return body_text, body_html

    def _extract_imap_attachments(
        self, 
        email_msg: email.message.Message
    ) -> list[EmailAttachment]:
        """Estrae informazioni sugli allegati da un messaggio IMAP."""
        attachments = []

        if email_msg.is_multipart():
            for part in email_msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_mime_header(filename)
                        attachments.append(EmailAttachment(
                            filename=filename,
                            mime_type=part.get_content_type(),
                            size=len(part.get_payload(decode=True) or b"")
                        ))

        return attachments

    def _group_imap_messages_by_subject(
        self, 
        messages: list[EmailMessage]
    ) -> list[EmailThread]:
        """Raggruppa i messaggi IMAP per subject (threading semplificato)."""
        # Normalizza subject rimuovendo Re:, Fwd:, etc.
        def normalize_subject(subject: str) -> str:
            if not subject:
                return ""
            subject = re.sub(r'^(Re|Fwd|Fw|R|I):\s*', '', subject, flags=re.IGNORECASE)
            return subject.strip().lower()

        threads_map = {}

        for msg in messages:
            key = normalize_subject(msg.subject or "")
            if not key:
                key = msg.id  # Usa ID se non c'è subject

            if key not in threads_map:
                threads_map[key] = []
            threads_map[key].append(msg)

        threads = []
        for key, msgs in threads_map.items():
            # Ordina per data
            msgs.sort(key=lambda m: m.date or datetime.min)

            participants_set = set()
            has_attachments = False
            has_drafts = False
            is_unread = False
            subject = None
            last_date = None

            for msg in msgs:
                if msg.from_address:
                    participants_set.add((msg.from_address.email, msg.from_address.name))
                for addr in msg.to_addresses + msg.cc_addresses:
                    participants_set.add((addr.email, addr.name))

                if msg.attachments:
                    has_attachments = True
                if msg.is_draft:
                    has_drafts = True
                if not msg.is_read:
                    is_unread = True

                if not subject and msg.subject:
                    subject = msg.subject
                if msg.date and (not last_date or msg.date > last_date):
                    last_date = msg.date

            participants = [
                EmailAddress(email=email, name=name)
                for email, name in participants_set
            ]

            threads.append(EmailThread(
                id=msgs[0].id,  # Usa ID del primo messaggio
                subject=subject,
                snippet=msgs[-1].snippet if msgs else None,
                messages=msgs,
                message_count=len(msgs),
                has_drafts=has_drafts,
                has_attachments=has_attachments,
                participants=participants,
                last_message_date=last_date,
                is_unread=is_unread,
                labels=[]
            ))

        # Ordina per ultima data
        threads.sort(key=lambda t: t.last_message_date or datetime.min, reverse=True)
        return threads
