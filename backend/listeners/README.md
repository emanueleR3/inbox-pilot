listeners/
└── gmail_listener/
    ├── Dockerfile
    ├── requirements.txt
    └── src/
        ├── main.py               # pull subscription
        ├── gmail_fetcher.py      # recupero messaggi Gmail usando historyId
        └── utils/
            ├── gmail_api_client.py
            └── pubsub_handler.py