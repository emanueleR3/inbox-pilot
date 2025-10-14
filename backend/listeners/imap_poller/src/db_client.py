
# simulazione DB
IMAP_ACCOUNTS = [
    {
        "user_id": "user_1",
        "imap_host": "imap.mailserver.com",
        "imap_port": 993,
        "username": "user1@mailserver.com",
        "password": "PASSWORD",
        "use_ssl": True
    },
    # altri utenti...
]

async def get_all_imap_accounts():
    """
    Ritorna tutte le caselle IMAP da monitorare.
    """
    # TODO recupero dal DB reale
    pass