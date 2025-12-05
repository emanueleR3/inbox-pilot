import imaplib
from fastapi import HTTPException, status

def test_imap_connection(server_imap: str, imap_port: int | None):
    try:
        port = imap_port if imap_port else 993
        imap = imaplib.IMAP4_SSL(server_imap, port, timeout=5)
        imap.logout()
        return True

    except imaplib.IMAP4.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il server IMAP esiste ma ha rifiutato la connessione"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossibile connettersi al server IMAP: {str(e)}"
        )

def test_imap_login(server_imap: str, imap_port: int | None, email: str, password: str):
    try:
        port = imap_port if imap_port else 993
        imap = imaplib.IMAP4_SSL(server_imap, port, timeout=5)
        imap.login(email, password)
        imap.logout()
        return True

    except imaplib.IMAP4.error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credenziali IMAP non valide"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore durante il tentativo di login IMAP: {str(e)}"
        )