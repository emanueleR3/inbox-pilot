import imaplib
import smtplib
import ssl
from src.handler_exception import (
    IMAPConnectionException,
    SMTPConnectionException,
    IMAPAuthenticationException,
    SMTPAuthenticationException
)


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
        raise IMAPConnectionException(server=server_imap, reason=str(e))


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
        raise IMAPAuthenticationException()
    except Exception as e:
        raise IMAPConnectionException(server=server_imap, reason=f"Errore login: {str(e)}")


def test_smtp_connection(server_smtp: str, smtp_port: int):
    try:
        smtp = smtplib.SMTP_SSL(server_smtp, smtp_port, timeout=5)
        smtp.quit()
        return True
    except Exception:
        pass

    try:
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        smtp = smtplib.SMTP_SSL(server_smtp, smtp_port, context=ctx, timeout=5)
        smtp.quit()
        return True
    except Exception as e:
        raise SMTPConnectionException(server=server_smtp, reason=str(e))


def test_smtp_login(server_smtp: str, smtp_port: int, email: str, password: str):
    try:
        smtp = smtplib.SMTP_SSL(server_smtp, smtp_port, timeout=5)
        smtp.login(email, password)
        smtp.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        raise SMTPAuthenticationException()
    except Exception:
        pass

    try:
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        smtp = smtplib.SMTP_SSL(server_smtp, smtp_port, context=ctx, timeout=5)
        smtp.login(email, password)
        smtp.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        raise SMTPAuthenticationException()
    except Exception as e:
        raise SMTPConnectionException(server=server_smtp, reason=f"Errore login: {str(e)}")
