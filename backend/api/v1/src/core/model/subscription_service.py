from pydantic import BaseModel
from google.oauth2.credentials import Credentials

class OAuthGoogleCredentials(Credentials):
    def __init__(self, email: str, access_token: str, refresh_token: str, expiry: str, **kwargs):
        self.email = email
        super().__init__(
            token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            **kwargs
        )