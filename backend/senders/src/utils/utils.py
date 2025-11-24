"""
Utility functions for token encryption/decryption.
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

encryption_key_token = os.getenv("ENCRYPTION_KEY_TOKEN")
encryption_key_pass = os.getenv("ENCRYPTION_KEY_PASS")

if not encryption_key_token:
    raise ValueError("ENCRYPTION_KEY_TOKEN non trovata nelle variabili d'ambiente")
if not encryption_key_pass:
    raise ValueError("ENCRYPTION_KEY_PASS non trovata nelle variabili d'ambiente")

_key_token = encryption_key_token.encode()
_hash_token = hashlib.sha256(_key_token).digest()
_cipher_token = Fernet(base64.urlsafe_b64encode(_hash_token))
_key_pass = encryption_key_pass.encode()
_hash_pass = hashlib.sha256(_key_pass).digest()
_cipher_pass = Fernet(base64.urlsafe_b64encode(_hash_pass))

def decrypt(value: str, cond: str) -> str:
    if not value:
        return ""

    if cond == "token":
        cipher = _cipher_token
    elif cond == "pass":
        cipher = _cipher_pass
    else:
        raise ValueError("cond deve essere 'token' o 'pass'")

    return cipher.decrypt(value.encode()).decode()