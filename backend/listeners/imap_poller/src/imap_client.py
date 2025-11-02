import imaplib
import email
import ssl
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Dict
import re
from datetime import datetime, timedelta
from src.utils.logger import log_info, log_error
from src.utils.mail_parser import clean_email_body, extract_plain_text_from_html

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
            # Non selezioniamo più automaticamente INBOX - facciamo questo nei metodi specifici
            
        except ssl.SSLError as e:
            # Prova con un contesto SSL ancora più permissivo
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                ssl_context.set_ciphers('ALL:@SECLEVEL=0')
                
                self.conn = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=ssl_context)
                self.conn.login(self.username, self.password)
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
        Estrae il corpo del messaggio (testo e HTML se disponibili) con supporto per strutture annidate.
        """
        body_text = ""
        body_html = ""
        
        def _decode_payload(part, content_type):
            """Helper per decodificare il payload di una parte."""
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="ignore")
            except Exception as e:
                log_error(f"Errore decodifica payload {content_type}: {str(e)}")
            return ""
        
        def _extract_from_multipart(msg_part, found_text="", found_html=""):
            """Estrae ricorsivamente il contenuto dalle parti multipart."""
            nonlocal body_text, body_html
            
            for part in msg_part.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Salta gli allegati
                if "attachment" in content_disposition:
                    continue
                
                # Salta il container multipart stesso
                if part.is_multipart():
                    continue
                
                if content_type == "text/plain" and not found_text:
                    decoded_content = _decode_payload(part, content_type)
                    if decoded_content:
                        found_text = decoded_content
                        # Se preferiamo text/plain, usalo subito
                        if not body_text:
                            body_text = decoded_content
                
                elif content_type == "text/html" and not found_html:
                    decoded_content = _decode_payload(part, content_type)
                    if decoded_content:
                        found_html = decoded_content
                        # Se non abbiamo ancora text/plain, usa HTML
                        if not body_text:
                            body_html = decoded_content
            
            return found_text, found_html
        
        if msg.is_multipart():
            # Gestisce messaggi multipart con strutture annidate
            text_content, html_content = _extract_from_multipart(msg)
            
            # Preferisce text/plain se disponibile, altrimenti HTML
            body_text = text_content if text_content else ""
            body_html = html_content if html_content else ""
            
        else:
            # Messaggio semplice (non multipart)
            content_type = msg.get_content_type()
            decoded_content = _decode_payload(msg, content_type)
            
            if decoded_content:
                if content_type == "text/plain":
                    body_text = decoded_content
                elif content_type == "text/html":
                    body_html = decoded_content
        
        return body_text, body_html

    def _clean_message_id(self, message_id: str) -> str:
        """
        Rimuove i caratteri < > dai Message-ID se presenti.
        Esempi:
        - "<123456@gmail.com>" -> "123456@gmail.com"
        - "<VI1PR02MB5216BB2DDAE4C17080150FD380FBA@VI1PR02MB5216.eurprd02.prod.outlook.com>" -> "VI1PR02MB5216BB2DDAE4C17080150FD380FBA@VI1PR02MB5216.eurprd02.prod.outlook.com"
        - "123456@gmail.com" -> "123456@gmail.com"
        """
        if not message_id:
            return message_id
        
        # Rimuovi < > se presenti all'inizio e alla fine
        if message_id.startswith('<') and message_id.endswith('>'):
            return message_id[1:-1]
        # Rimuovi solo < all'inizio se presente (per casi come il tuo esempio)
        elif message_id.startswith('<'):
            return message_id[1:]
        # Rimuovi solo > alla fine se presente
        elif message_id.endswith('>'):
            return message_id[:-1]
        
        return message_id

    def _extract_message_id(self, msg):
        """
        Estrae il Message-ID dell'email e rimuove < > se presenti.
        """
        message_id = msg.get("Message-ID", "")
        return self._clean_message_id(message_id)

    def _extract_thread_id(self, msg):
        """
        Estrae il Thread-ID usando sempre l'header IMAP standard In-Reply-To.
        Se In-Reply-To non è presente, restituisce "no" (per messaggi che iniziano una nuova conversazione).
        Rimuove < > se presenti.
        """
        # Usa sempre In-Reply-To come standard IMAP per il threading
        in_reply_to = msg.get("In-Reply-To", "")
        if in_reply_to:
            thread_id = self._clean_message_id(in_reply_to)
        else:
            thread_id = "no"
        
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

    def list_folders(self) -> List[str]:
        """
        Lista tutte le cartelle disponibili nell'account IMAP.
        
        Returns:
            List[str]: Lista dei nomi delle cartelle
        """
        try:
            status, folders = self.conn.list()
            if status != "OK":
                log_error(f"Errore nel listing delle cartelle per {self.username}")
                return []
            
            folder_names = []
            for folder in folders:
                # Decodifica la risposta (formato: (flags) delimiter folder_name)
                folder_str = folder.decode() if isinstance(folder, bytes) else folder
                # Estrae il nome della cartella dalla risposta IMAP
                folder_name = folder_str.split('"')[-2] if '"' in folder_str else folder_str.split()[-1]
                folder_names.append(folder_name)
            
            log_info(f"Cartelle trovate per {self.username}: {folder_names}")
            return folder_names
            
        except Exception as e:
            log_error(f"Errore nel listing cartelle per {self.username}: {str(e)}")
            return []

    def select_folder(self, folder_name: str) -> bool:
        """
        Seleziona una cartella specifica.
        
        Args:
            folder_name: Nome della cartella da selezionare
            
        Returns:
            bool: True se la selezione è riuscita, False altrimenti
        """
        try:
            status, count = self.conn.select(folder_name)
            if status == "OK":
                log_info(f"Cartella '{folder_name}' selezionata per {self.username}")
                return True
            else:
                log_error(f"Errore nella selezione cartella '{folder_name}' per {self.username}: {status}")
                return False
        except Exception as e:
            log_error(f"Errore nella selezione cartella '{folder_name}' per {self.username}: {str(e)}")
            return False

    def get_sent_folder_name(self) -> str:
        """
        Determina il nome della cartella Sent per questo provider.
        Diversi provider usano nomi diversi per la cartella delle email inviate.
        
        Returns:
            str: Nome della cartella Sent o stringa vuota se non trovata
        """
        # Lista dei possibili nomi per la cartella Sent
        possible_sent_folders = [
            "Sent",
            "Sent Messages", 
            "Sent Items",
            "Gesendet",      # Gmail DE
            "Enviados",      # Gmail ES
            "Inviata",       # Gmail IT
            "Envoyés",       # Gmail FR
            "Отправленные",  # Gmail RU
            "已发送",         # Gmail CN
            "INBOX.Sent",    # Alcune configurazioni
            "[Gmail]/Sent Mail",  # Gmail IMAP
            "Drafts/Sent"    # Alcune configurazioni meno comuni
        ]
        
        available_folders = self.list_folders()
        
        for sent_name in possible_sent_folders:
            if sent_name in available_folders:
                log_info(f"Cartella Sent trovata: '{sent_name}' per {self.username}")
                return sent_name
        
        log_error(f"Nessuna cartella Sent trovata per {self.username}. Cartelle disponibili: {available_folders}")
        return ""

    def fetch_unseen_messages(self, folder_name: str = "INBOX") -> List[Dict]:
        """
        Recupera i messaggi non letti da una cartella specifica inviati dopo ieri.
        
        Args:
            folder_name: Nome della cartella da cui recuperare i messaggi (default: INBOX)
        """
        # Seleziona la cartella richiesta
        if not self.select_folder(folder_name):
            return []
            
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
                log_info(f"Email {mail_id.decode()} ignorata (data: {date_str})")
                continue  # Salta le email vecchie
            
            # Converte la data in formato timestamp
            timestamp = ""
            if date_str:
                try:
                    parsed_date = parsedate_to_datetime(date_str)
                    timestamp = parsed_date.isoformat()
                except:
                    timestamp = date_str

            # Estrae il corpo del messaggio e lo pulisce
            body_text, body_html = self._extract_email_body(msg)
            
            # Pulisce il corpo del messaggio
            if body_text:
                body_text = clean_email_body(body_text)
            elif body_html:
                # Se non c'è text/plain, estrae il testo dall'HTML
                body_text = extract_plain_text_from_html(body_html)
                body_html = clean_email_body(body_html)
            
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

    def fetch_sent_messages(self) -> List[Dict]:
        """
        Recupera i messaggi inviati dalla cartella Sent.
        Restituisce solo i messaggi inviati dopo ieri.
        
        Returns:
            List[Dict]: Lista di messaggi inviati
        """
        sent_folder = self.get_sent_folder_name()
        if not sent_folder:
            log_error(f"Impossibile trovare cartella Sent per {self.username}")
            return []
        
        return self.fetch_unseen_messages(sent_folder)

    def fetch_sent_messages_since(self, since_timestamp: str = None, is_first_polling: bool = False) -> List[Dict]:
        """
        Recupera i messaggi inviati dalla cartella Sent più recenti di un timestamp specifico.
        
        Args:
            since_timestamp: ISO timestamp dell'ultimo messaggio processato (None per primo polling)
            is_first_polling: True se è il primo polling per questo account
            
        Returns:
            List[Dict]: Lista di messaggi inviati più recenti
        """
        sent_folder = self.get_sent_folder_name()
        if not sent_folder:
            log_error(f"Impossibile trovare cartella Sent per {self.username}")
            return []
        
        # Seleziona la cartella Sent
        if not self.select_folder(sent_folder):
            return []
        
        try:
            # Logica per il primo polling
            if is_first_polling:
                log_info(f"📤 Primo polling per {self.username} - cerco messaggi degli ultimi 2 minuti")
                # Per il primo polling: prendi solo messaggi degli ultimi 2 minuti
                two_minutes_ago = datetime.now() - timedelta(minutes=2)
                imap_date = two_minutes_ago.strftime("%d-%b-%Y")
                search_criteria = f'SINCE "{imap_date}"'
            elif since_timestamp:
                try:
                    # Converte timestamp in formato IMAP per ricerca
                    since_date = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
                    imap_date = since_date.strftime("%d-%b-%Y")
                    search_criteria = f'SINCE "{imap_date}"'
                    log_info(f"📤 Polling incrementale per {self.username} - cerco messaggi dal {imap_date}")
                except:
                    # Se il parsing fallisce, usa gli ultimi 2 giorni
                    yesterday = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
                    search_criteria = f'SINCE "{yesterday}"'
                    log_info(f"📤 Fallback per {self.username} - cerco messaggi dal {yesterday}")
            else:
                # Default: prendi i messaggi degli ultimi 2 giorni
                yesterday = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
                search_criteria = f'SINCE "{yesterday}"'
                log_info(f"📤 Polling default per {self.username} - cerco messaggi dal {yesterday}")
            
            status, messages = self.conn.search(None, search_criteria)
            if status != "OK":
                log_error(f"Errore nella ricerca messaggi inviati per {self.username}")
                return []

            mail_ids = messages[0].split()
            emails = []
            now = datetime.now()
            two_minutes_ago = now - timedelta(minutes=2)
            
            log_info(f"📤 Trovati {len(mail_ids)} messaggi nella cartella Sent per {self.username}")
            
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
                parsed_date = None
                if date_str:
                    try:
                        parsed_date = parsedate_to_datetime(date_str)
                        timestamp = parsed_date.isoformat()
                    except:
                        timestamp = date_str

                # Logica specifica per primo polling
                if is_first_polling:
                    # Per il primo polling: prendi solo messaggi degli ultimi 2 minuti
                    if parsed_date:
                        # Converte in timezone naive per confronto
                        msg_date_naive = parsed_date.replace(tzinfo=None) if parsed_date.tzinfo else parsed_date
                        if msg_date_naive < two_minutes_ago:
                            log_info(f"📤 Primo polling: messaggio {mail_id.decode()} troppo vecchio ({msg_date_naive}), saltato")
                            continue
                        else:
                            log_info(f"📤 Primo polling: messaggio {mail_id.decode()} recente ({msg_date_naive}), processato")
                elif since_timestamp and parsed_date:
                    # Per polling incrementali: salta i messaggi più vecchi dell'ultimo processato
                    try:
                        since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
                        msg_dt = parsed_date.replace(tzinfo=None) if parsed_date.tzinfo else parsed_date
                        since_dt_naive = since_dt.replace(tzinfo=None) if since_dt.tzinfo else since_dt
                        
                        if msg_dt <= since_dt_naive:
                            continue  # Salta questo messaggio
                    except:
                        pass  # In caso di errore, processa il messaggio

                # Estrae il corpo del messaggio e lo pulisce
                body_text, body_html = self._extract_email_body(msg)
                
                # Pulisce il corpo del messaggio
                if body_text:
                    body_text = clean_email_body(body_text)
                elif body_html:
                    body_text = extract_plain_text_from_html(body_html)
                    body_html = clean_email_body(body_html)
                
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
                    "folder": sent_folder,  # Indica che è dalla cartella Sent
                    "is_outbound": True,    # Flag per indicare che è un messaggio inviato
                    # Metadati aggiuntivi
                    "content_type": msg.get_content_type(),
                    "charset": msg.get_content_charset() or "utf-8",
                    "size": len(raw_email) if raw_email else 0
                }

                emails.append(email_data)

            log_info(f"📤 Selezionati {len(emails)} messaggi inviati per {self.username}")
            return emails
            
        except Exception as e:
            log_error(f"Errore nel recupero messaggi inviati per {self.username}: {str(e)}")
            return []

    def get_most_recent_sent_message(self) -> Dict:
        """
        Recupera il messaggio inviato più recente dalla cartella Sent.
        Utilizzato per inizializzare il tracking quando non ci sono messaggi recenti.
        
        Returns:
            Dict: Dati del messaggio più recente o dict vuoto se non trovato
        """
        sent_folder = self.get_sent_folder_name()
        if not sent_folder:
            return {}
        
        # Seleziona la cartella Sent
        if not self.select_folder(sent_folder):
            return {}
        
        try:
            # Cerca tutti i messaggi dell'ultima settimana
            one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            status, messages = self.conn.search(None, f'SINCE "{one_week_ago}"')
            
            if status != "OK" or not messages[0]:
                log_info(f"📤 Nessun messaggio recente trovato nella cartella Sent per {self.username}")
                return {}

            mail_ids = messages[0].split()
            if not mail_ids:
                return {}
            
            # Prendi l'ultimo messaggio (più recente)
            latest_mail_id = mail_ids[-1]
            _, msg_data = self.conn.fetch(latest_mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Estrae solo i dati essenziali
            date_str = msg.get("Date", "")
            message_id = self._extract_message_id(msg)
            
            timestamp = ""
            if date_str:
                try:
                    parsed_date = parsedate_to_datetime(date_str)
                    timestamp = parsed_date.isoformat()
                except:
                    timestamp = date_str

            log_info(f"📤 Messaggio più recente per {self.username}: {message_id} (data: {date_str})")
            
            return {
                "message_id": message_id,
                "timestamp": timestamp,
                "date": date_str
            }
            
        except Exception as e:
            log_error(f"Errore nel recupero messaggio più recente per {self.username}: {str(e)}")
            return {}

    def mark_as_seen(self, mail_id):
        self.conn.store(mail_id, '+FLAGS', '\\Seen')

    def close(self):
        try:
            if self.conn:
                self.conn.close()
                self.conn.logout()
        except Exception as e:
            log_error(f"Errore durante chiusura connessione IMAP per {self.username}: {str(e)}")