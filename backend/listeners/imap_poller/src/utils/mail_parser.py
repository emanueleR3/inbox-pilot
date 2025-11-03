"""
Utility per il parsing e l'elaborazione delle email IMAP.
Questo modulo contiene funzioni helper per processare i dati delle email.
"""

import re
from email.utils import parseaddr, parsedate_to_datetime
from typing import Dict, List, Tuple, Optional
from datetime import datetime

def extract_email_addresses(address_string: str) -> List[Dict[str, str]]:
    """
    Estrae nome e indirizzo email da una stringa di indirizzi.
    
    Args:
        address_string: Stringa contenente indirizzi email (es: "Nome <email@domain.com>")
    
    Returns:
        Lista di dizionari con 'name' ed 'email'
    """
    if not address_string:
        return []
    
    addresses = []
    # Splitta per virgola per gestire indirizzi multipli
    for addr in address_string.split(','):
        name, email = parseaddr(addr.strip())
        addresses.append({
            'name': name.strip() if name else '',
            'email': email.strip() if email else ''
        })
    
    return addresses

def clean_email_body(body_text: str) -> str:
    """
    Pulisce il corpo dell'email rimuovendo caratteri indesiderati e normalizzando il testo.
    """
    if not body_text:
        return ""
    
    # Rimuove caratteri di controllo e normalizza gli spazi
    cleaned = re.sub(r'[\r\n\t]+', '\n', body_text)
    cleaned = re.sub(r' +', ' ', cleaned)
    
    # Rimuove righe vuote multiple consecutive
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    
    # Rimuove spazi all'inizio e fine delle righe
    lines = [line.strip() for line in cleaned.split('\n')]
    cleaned = '\n'.join(lines)
    
    # Rimuove quoted-printable artifacts comuni
    cleaned = re.sub(r'=\d{2}', '', cleaned)  # Rimuove =20, =3D, etc.
    cleaned = re.sub(r'=\n', '', cleaned)     # Rimuove soft line breaks
    
    return cleaned.strip()

def extract_plain_text_from_html(html_content: str) -> str:
    """
    Estrae il testo semplice da contenuto HTML.
    Rimuove tag HTML e decodifica entità HTML.
    """
    if not html_content:
        return ""
    
    import html
    
    # Rimuove tag HTML comuni
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decodifica entità HTML
    text = html.unescape(text)
    
    # Pulisce il testo risultante
    return clean_email_body(text)

def extract_urls_from_text(text: str) -> List[str]:
    """
    Estrae tutti gli URL presenti nel testo.
    
    Args:
        text: Testo da analizzare
    
    Returns:
        Lista di URL trovati
    """
    if not text:
        return []
    
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    return url_pattern.findall(text)

def parse_date_string(date_string: str) -> Optional[datetime]:
    """
    Converte una stringa di data email in oggetto datetime.
    
    Args:
        date_string: Stringa data dell'email
    
    Returns:
        Oggetto datetime o None se il parsing fallisce
    """
    if not date_string:
        return None
    
    try:
        return parsedate_to_datetime(date_string)
    except (ValueError, TypeError):
        return None

def is_automated_email(from_address: str, subject: str, body: str) -> bool:
    """
    Determina se un'email è automatica/di sistema.
    
    Args:
        from_address: Indirizzo del mittente
        subject: Oggetto dell'email
        body: Corpo dell'email
    
    Returns:
        True se l'email sembra automatica
    """
    automated_patterns = [
        r'no[-_]?reply',
        r'do[-_]?not[-_]?reply',
        r'noreply',
        r'mailer[-_]?daemon',
        r'postmaster',
        r'bounce',
        r'notification',
        r'automated',
        r'system'
    ]
    
    # Controlla l'indirizzo del mittente
    from_lower = from_address.lower() if from_address else ""
    for pattern in automated_patterns:
        if re.search(pattern, from_lower):
            return True
    
    # Controlla l'oggetto
    subject_lower = subject.lower() if subject else ""
    auto_subjects = [
        'delivery status notification',
        'mail delivery failure',
        'returned mail',
        'undelivered mail',
        'auto reply',
        'out of office'
    ]
    
    for auto_subject in auto_subjects:
        if auto_subject in subject_lower:
            return True
    
    return False

def extract_email_from_address(address_string: str) -> str:
    """
    Estrae solo l'indirizzo email da una stringa che può contenere nome e email.
    
    Args:
        address_string: Stringa tipo "Nome <email@domain.com>" o "email@domain.com"
    
    Returns:
        Solo l'indirizzo email estratto
    """
    if not address_string:
        return ""
    
    # Usa parseaddr per estrarre l'email
    name, email = parseaddr(address_string.strip())
    return email.strip() if email else ""

def is_no_reply_email(from_address: str) -> bool:
    """
    Determina se un'email proviene da un indirizzo no-reply.
    
    Args:
        from_address: Indirizzo del mittente (può includere il nome)
    
    Returns:
        True se è un indirizzo no-reply
    """
    if not from_address:
        return False
    
    # Estrai solo l'indirizzo email
    email = extract_email_from_address(from_address)
    if not email:
        return False
    
    email_lower = email.lower()
    no_reply_patterns = [
        'no-reply', 'noreply', 'do-not-reply', 'donotreply',
        'no_reply', 'donot-reply', 'auto-reply', 'autoreply',
        'mailer-daemon', 'postmaster', 'bounce'
    ]
    
    return any(pattern in email_lower for pattern in no_reply_patterns)

def is_sent_message(from_address: str, user_email: str, folder_type: str = None) -> bool:
    """
    Determina se un messaggio è stato inviato dall'account stesso.
    
    Args:
        from_address: Indirizzo del mittente (può includere il nome)
        user_email: Email dell'account IMAP
        folder_type: Tipo di cartella (opzionale, es. "sent", "inbox")
    
    Returns:
        True se il messaggio è stato inviato dall'account stesso
    """
    if not from_address or not user_email:
        return False
    
    # Estrai solo l'indirizzo email del mittente
    sender_email = extract_email_from_address(from_address)
    if not sender_email:
        return False
    
    # Confronta gli indirizzi email (case-insensitive)
    is_same_sender = sender_email.lower() == user_email.lower()
    
    # Se è specificato il tipo di cartella, considera anche quello
    is_sent_folder = folder_type and 'sent' in folder_type.lower()
    
    return is_same_sender or is_sent_folder

def extract_quoted_text(body: str) -> Tuple[str, str]:
    """
    Separa il testo originale da quello quotato in una risposta.
    
    Args:
        body: Corpo dell'email
    
    Returns:
        Tupla (testo_nuovo, testo_quotato)
    """
    if not body:
        return "", ""
    
    # Pattern comuni per identificare testo quotato
    quote_patterns = [
        r'^>.*$',  # Linee che iniziano con >
        r'^On .* wrote:$',  # "On [date] [person] wrote:"
        r'^From:.*$',  # Headers quotati
        r'^-----Original Message-----.*',  # Outlook
        r'^________________________________.*'  # Separatori
    ]
    
    lines = body.split('\n')
    new_text_lines = []
    quoted_text_lines = []
    in_quoted_section = False
    
    for line in lines:
        is_quoted_line = any(re.match(pattern, line.strip(), re.MULTILINE | re.DOTALL) 
                            for pattern in quote_patterns)
        
        if is_quoted_line:
            in_quoted_section = True
        
        if in_quoted_section:
            quoted_text_lines.append(line)
        else:
            new_text_lines.append(line)
    
    return '\n'.join(new_text_lines).strip(), '\n'.join(quoted_text_lines).strip()