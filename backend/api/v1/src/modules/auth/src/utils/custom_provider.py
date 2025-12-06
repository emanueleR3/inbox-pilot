import imaplib
import ssl
from fastapi import HTTPException, status


def test_imap_connection(server_imap: str, imap_port: int):
    try:
        imap = imaplib.IMAP4_SSL(server_imap, imap_port, timeout=5)
        imap.logout()
        return True
    except Exception:
        pass

    try:
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        imap = imaplib.IMAP4_SSL(server_imap, imap_port, ssl_context=ctx, timeout=5)
        imap.logout()
        return True
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossibile connettersi al server IMAP: " + str(e)
        )


def test_imap_login(server_imap: str, imap_port: int, email: str, password: str):
    try:
        imap = imaplib.IMAP4_SSL(server_imap, imap_port, timeout=5)
        imap.login(email, password)
        imap.logout()
        return True
    except Exception:
        pass

    try:
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        imap = imaplib.IMAP4_SSL(server_imap, imap_port, ssl_context=ctx, timeout=5)
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
            detail="Errore durante il tentativo di login IMAP: " + str(e)
        )

