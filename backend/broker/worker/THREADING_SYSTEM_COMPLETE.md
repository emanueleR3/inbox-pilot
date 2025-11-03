# 📧 Email Threading & Filtering System

## 🎯 Panoramica

Sistema completo per il filtering e salvataggio automatico delle email in thread nel database, implementato nel broker worker. Il sistema rileva automaticamente nuove conversazioni e gestisce risposte a thread esistenti prima dell'elaborazione AI.

## 📋 Filtri Implementati

### 1. 🔴 Conversazioni iniziate dall'utente
**Criteri:** `is_sent = True` AND `reply_to_id = "no"`

**Comportamento:**
- Crea nuovo thread con categoria `"STARTED_BY_HUMAN"`
- Imposta `human_response = True`
- Non richiede elaborazione AI immediata
- Log: `"Created new thread for user-initiated conversation"`

**Campi salvati:**
```javascript
{
  started_at: timestamp,
  history: [message_id],
  subject: oggetto_email,
  sender_email: user_email,
  cc_emails: [...],
  last_message_id: message_id,
  last_message_at: timestamp,
  category: "STARTED_BY_HUMAN",
  human_response: true,
  last_sender_email: user_email,
  box_email: user_email
}
```

### 2. 🔵 Conversazioni iniziate da utenti esterni
**Criteri:** `is_sent = False` AND `reply_to_id = "no"`

**Comportamento:**
- Crea nuovo thread senza categoria specifica
- Imposta `human_response = False`
- Richiede elaborazione AI immediata
- Log: `"Created new thread for external-initiated conversation"`

**Campi salvati:**
```javascript
{
  started_at: timestamp,
  history: [message_id],
  subject: oggetto_email,
  sender_email: from_field,
  cc_emails: [...],
  last_message_id: message_id,
  last_message_at: timestamp,
  attachment_emails_id: null,
  category: null,
  human_response: false,
  last_sender_email: from_field,
  box_email: user_email
}
```

### 3. 🟡 Risposte a thread esistenti
**Criteri:** `reply_to_id != "no"` AND `reply_to_id` non vuoto

**Comportamento:**
1. **Ricerca thread**: Trova thread contenente `reply_to_id` nella `history`
2. **Check duplicati**: Verifica se `message_id` già presente nella `history`
3. **Gestione basata su `is_sent`:**
   - **Se `is_sent = True`** (utente risponde):
     - Imposta `human_response = True`
     - Log: `"Human response marked for thread"`
     - TODO: notifica, aggiornare summary e category
   - **Se `is_sent = False`** (esterno risponde):
     - Aggiorna thread con nuovo messaggio
     - Log: `"Thread updated with reply"`

**Aggiornamenti per risposte esterne:**
```javascript
{
  history: [...existing, new_message_id],
  cc_emails: [...existing, ...new_cc_emails],
  last_message_id: new_message_id,
  last_message_at: new_timestamp,
  last_sender_email: sender_email
}
```

**Ottimizzazione query:**
- Pre-filtra per `box_email` prima di cercare nella `history`
- Usa operatore PostgreSQL `@>` per ricerca in array

## 🔄 Flusso di Elaborazione

```
📧 Email arriva → RabbitMQ → Worker
    ↓
🔍 AdvancedEmailFilter.process_message()
    ↓
📝 Filtri in sequenza:
    ├─ Filter 1: Nuova conversazione utente?
    ├─ Filter 2: Nuova conversazione esterna?
    └─ Filter 3: Risposta a thread esistente?
    ↓
🗂️ ThreadRepository operations
    ↓
💬 MessageProcessor gestisce output
    ↓
🖥️ Console output + routing workflow
```

## 🏗️ Architettura

### Struttura Cartelle
```
/broker/worker/src/
├── filters/
│   └── advanced_filter.py    # Logica di filtering centralizzata
├── repositories/
│   └── thread_repository.py  # Operazioni database threads
├── processors/
│   └── message_processor.py  # Orchestrazione workflow
├── managers/
│   └── thread_manager.py     # Gestione thread avanzata
├── models/
│   └── email_models.py       # Modelli dati
└── utils/
    └── db_client.py          # Connessione Supabase
```

### Componenti Principali

#### 🔍 AdvancedEmailFilter
- `process_message()`: Punto di ingresso principale
- `_is_new_conversation_from_user()`: Rileva conversazioni utente
- `_is_new_conversation_from_external()`: Rileva conversazioni esterne
- `_is_reply_to_existing_thread()`: Rileva risposte a thread
- `_handle_reply_to_thread()`: Gestisce logica risposte
- `_create_new_thread_from_sent()`: Crea thread per email inviate
- `_create_new_thread_from_external()`: Crea thread per email ricevute

#### 🗂️ ThreadRepository
- `create_thread()`: Crea nuovo thread nel database
- `find_thread_by_reply_to()`: Trova thread per reply_to_id
- `is_message_in_thread_history()`: Check duplicati
- `update_thread_with_new_message()`: Aggiorna thread con nuovo messaggio
- `set_human_response_needed()`: Marca risposta umana necessaria
- Validazione foreign key per `box_email`
- Pattern simile a `create_subscription_service`

#### 💬 MessageProcessor
- Orchestrazione tra filtri e workflow AI
- Console output differenziato per tipo thread
- Routing verso workflow appropriati
- Gestione status: `thread_created`, `thread_updated`, `human_response_needed`, `skipped`

## 🎮 Console Output

### Thread da Utente
```
🎯 [FILTER] Detected new conversation from user: user@example.com -> client@example.com
🗂️ [THREAD] Thread created successfully with ID: thread_xyz
👤 [PROCESSOR] Thread created from user - no AI processing needed
```

### Thread da Esterno
```
🎯 [FILTER] Detected new conversation from external user: client@company.com -> user@example.com
🗂️ [THREAD] Thread created successfully with ID: thread_abc
🤖 [PROCESSOR] Thread created from external user - sending to AI workflow
🧵 Thread ID: thread_abc
📧 Subject: Question about your services
👤 Sender: client@company.com
📮 Mailbox: user@example.com
```

### Risposta Utente
```
🔗 [FILTER] Detected reply to message: msg-002-external-received
🔍 [THREAD] Found thread thread_abc containing message: msg-002-external-received
🔍 [THREAD] Message msg-003-user-reply not found in thread thread_abc history
👤 [THREAD] Thread thread_abc marked as needing human response
👤 [FILTER] Human response set for thread thread_abc
👤 [PROCESSOR] Human response marked for thread thread_abc
```

### Risposta Esterna
```
🔗 [FILTER] Detected reply to message: msg-003-user-reply
🔍 [THREAD] Found thread thread_abc containing message: msg-003-user-reply
🔍 [THREAD] Message msg-004-external-reply not found in thread thread_abc history
📝 [THREAD] Thread thread_abc updated with new message msg-004-external-reply
📝 [FILTER] Thread thread_abc updated with new message msg-004-external-reply
📝 [PROCESSOR] Thread thread_abc updated with reply - sending to AI workflow
```

### Messaggio Duplicato
```
🔗 [FILTER] Detected reply to message: msg-003-user-reply
🔍 [THREAD] Found thread thread_abc containing message: msg-003-user-reply
🔍 [THREAD] Message msg-004-external-reply found in thread thread_abc history
🔄 [FILTER] Duplicate message msg-004-external-reply found in thread thread_abc
🚫 [PROCESSOR] Message skipped: duplicate
```

## 🧪 Testing

### Test Completo
```bash
cd /broker/worker
python test_complete_threading.py
```

### Test Solo Logica
```bash
cd /broker/worker
python test_filter_logic.py
```

### Test Singoli Filtri
```bash
cd /broker/worker
python test_external_filter.py
```

## ⚠️ Note Importanti

1. **Foreign Key Constraint**: Il campo `box_email` ha vincolo verso `subscription_services.email`
2. **Validazione**: Repository verifica esistenza email prima di creare thread
3. **Ottimizzazione Query**: Pre-filtraggio per `box_email` nelle ricerche thread
4. **Gestione Duplicati**: Controllo automatico duplicati in thread history
5. **Timestamp**: Gestione automatica di formati diversi dai provider
6. **CC Emails**: Merge intelligente di CC emails in thread esistenti
7. **Campi Opzionali**: Repository gestisce campi `null` correttamente

## 🚀 Prossimi Passi

- [x] ✅ Gestione risposte a thread esistenti
- [x] ✅ Rilevamento messaggi duplicati
- [ ] TODO: notifica, aggiornare summary e category (per risposte utente)
- [ ] Integrazione con workflow AI
- [ ] Gestione attachment
- [ ] Metriche e monitoring

## 📊 Esempi Payload

### Email Inviata dall'Utente
```json
{
  "message_id": "msg-001",
  "user_email": "user@company.com",
  "is_sent": true,
  "reply_to_id": "no",
  "from": "user@company.com",
  "to": "client@external.com",
  "subject": "New project proposal",
  "body": "Hi, I'd like to discuss...",
  "timestamp": "1699027200000"
}
```

### Email Ricevuta da Esterno
```json
{
  "message_id": "msg-002",
  "user_email": "user@company.com",
  "is_sent": false,
  "reply_to_id": "no",
  "from": "client@external.com",
  "to": "user@company.com",
  "subject": "Question about services",
  "body": "Hello, I have a question...",
  "timestamp": "1699027260000"
}
```

### Risposta in Thread
```json
{
  "message_id": "msg-003",
  "user_email": "user@company.com",
  "is_sent": true,
  "reply_to_id": "msg-002",
  "from": "user@company.com",
  "to": "client@external.com",
  "subject": "Re: Question about services",
  "body": "Thanks for your question...",
  "timestamp": "1699027320000"
}
```