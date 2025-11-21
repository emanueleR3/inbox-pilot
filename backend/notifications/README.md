# Notifications Service

Servizio di notifiche per il sistema Corretto. Riceve webhook dal servizio automations e gestisce l'invio di email di notifica agli utenti.

## Funzionalità

Il servizio notifications riceve notifiche dai vari nodi del workflow di automazione per i seguenti scenari:

- **HIGH_PRIORITY**: Email ad alta priorità che richiedono attenzione immediata
- **LOW_CONFIDENCE_CLASSIFICATION**: Classificazione con bassa confidenza che richiede revisione umana
- **EVENT_INVITE_RECEIVED**: Invito a evento ricevuto che richiede risposta umana

## Architettura

Il servizio è un'applicazione FastAPI che espone un endpoint webhook:

- **POST /send-notification**: Riceve richieste di notifica dal servizio automations
- **GET /health**: Health check endpoint
- **GET /**: Informazioni sul servizio

## Configurazione

Il servizio gira sulla porta **8020** e può essere configurato tramite variabili d'ambiente:

- `NOTIFICATIONS_PORT`: Porta del servizio (default: 8020)
- `NOTIFICATIONS_HOST`: Host del servizio (default: 0.0.0.0)

## Struttura del Payload

Il webhook riceve un payload JSON con i seguenti campi:

```json
{
  "notification_type": "HIGH_PRIORITY|LOW_CONFIDENCE_CLASSIFICATION|EVENT_INVITE_RECEIVED",
  "sender_email": "sender@example.com",
  "box_email": "mailbox@example.com",
  "subject": "Email subject",
  "body": "Email body content",
  "summary_attachment": "Summary of attachments (optional)",
  "timestamp": "2024-11-21T10:30:00+01:00"
}
```

## Deployment

Il servizio viene deployato automaticamente tramite GitHub Actions quando vengono rilevate modifiche nella cartella `notifications/`.

### Docker

```bash
docker build -t notifications .
docker run -p 8020:8020 notifications
```

### Docker Compose

Il servizio è incluso nel `docker-compose.yml` principale e viene avviato automaticamente con:

```bash
docker compose up -d notifications
```

## Sviluppo

### Requisiti

- Python 3.11+
- FastAPI
- Uvicorn

### Installazione dipendenze

```bash
pip install -r requirements.txt
```

### Avvio locale

```bash
python -m src.main
```

Il servizio sarà disponibile su `http://localhost:8020`

## TODO

- [ ] Implementare logica di invio email effettivo
- [ ] Aggiungere rate limiting per prevenire spam
- [ ] Implementare retry logic per email fallite
- [ ] Aggiungere logging su database delle notifiche inviate
- [ ] Implementare template email personalizzabili per tipo di notifica
