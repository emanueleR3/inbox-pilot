#!/usr/bin/env sh
set -e

sleep 15 # Wait for RabbitMQ to be ready

# Forward SIGTERM/SIGINT to children so docker stop exits cleanly
term_handler() {
  echo "Caught termination signal, stopping children..."
  kill -TERM "$gmail_pid" 2>/dev/null || true
  kill -TERM "$imap_pid" 2>/dev/null || true
  kill -TERM "$ms_pid" 2>/dev/null || true
}
trap term_handler TERM INT

# Defaults
: "${POLL_INTERVAL_MINUTES_IMAP:=2}"
: "${MICROSOFT_WEBHOOK_PORT:=8001}"

# Start Gmail Pub/Sub listener
( cd gmail_listener && PYTHONPATH="/app/gmail_listener:/app" python -u -m src.main ) &
gmail_pid=$!

# Start IMAP poller
( cd imap_poller && PYTHONPATH="/app/imap_poller:/app" python -u -m src.main ) &
imap_pid=$!

# Start Microsoft webhook (FastAPI via uvicorn)
( cd microsoft_listener && PYTHONPATH="/app/microsoft_listener:/app" python -u -m src.main ) &
ms_pid=$!

# Monitor children: if any exits, terminate the rest
while :; do
  if ! kill -0 "$gmail_pid" 2>/dev/null; then break; fi
  if ! kill -0 "$imap_pid" 2>/dev/null; then break; fi
  if ! kill -0 "$ms_pid" 2>/dev/null; then break; fi
  sleep 1
done

kill -TERM "$gmail_pid" "$imap_pid" "$ms_pid" 2>/dev/null || true
wait
