from googleapiclient.discovery import build
from src.core.config import settings
from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO

subscription_service_dao = SubscriptionServiceDAO()

#def create_watch_for_user(user_email: str):
# TODO DEBUG eliminare ########################### usare la firma di sopra
def create_watch_for_user(user_email: str):
    """
    Attiva watch Gmail per un utente
    """
    credentials = subscription_service_dao.get_google_credentials(user_email)

    # TODO DEBUG eliminare ###########################
    '''
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            #"https://www.googleapis.com/auth/gmail.metadata",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
    )
    '''
    # ###############################################

    # TODO controllare se le credenziali sono valide come tipo di dato Credentials wrapped
    service = build("gmail", "v1", credentials=credentials)

    request = {
        "labelIds": ["INBOX"],
        "topicName": settings.PUBSUB_TOPIC_PATH
    }

    response = service.users().watch(userId="me", body=request).execute()

    import logging
    logging.info(f"Gmail watch created for {user_email}: {response}")

    return response  # contiene historyId e expiration