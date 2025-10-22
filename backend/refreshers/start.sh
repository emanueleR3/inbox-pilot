#!/usr/bin/env sh
set -e  # Exit on error

# Forward SIGTERM/SIGINT to children so docker stop exits cleanly
term_handler() {
  echo "Caught termination signal, stopping children..."
  [ -n "$google_pid" ] && kill -TERM "$google_pid" 2>/dev/null || true
  [ -n "$ms_token_pid" ] && kill -TERM "$ms_token_pid" 2>/dev/null || true
  [ -n "$ms_sub_pid" ] && kill -TERM "$ms_sub_pid" 2>/dev/null || true
}
trap term_handler TERM INT

# Default intervals if not provided
: "${REFRESH_INTERVAL_MINUTES_TOKENS:=15}"
: "${REFRESH_INTERVAL_HOURS_SUBSCRIPTIONS:=3}"

# Start the three refreshers in background in their own subshells (so cd doesn't leak)
(
  cd /app/google_token_refresher && \
  PYTHONPATH="/app/google_token_refresher:/app" exec python -u -m src.main
) &
google_pid=$!

(
  cd /app/microsoft_token_refresher && \
  PYTHONPATH="/app/microsoft_token_refresher:/app" exec python -u -m src.main
) &
ms_token_pid=$!

(
  cd /app/microsoft_subscription_refresher && \
  PYTHONPATH="/app/microsoft_subscription_refresher:/app" exec python -u -m src.main
) &
ms_sub_pid=$!

# Monitor children: if any exits, terminate the rest
while :; do
  if ! kill -0 "$google_pid" 2>/dev/null; then break; fi
  if ! kill -0 "$ms_token_pid" 2>/dev/null; then break; fi
  if ! kill -0 "$ms_sub_pid" 2>/dev/null; then break; fi
  sleep 1
done

# Someone exited, stop others
kill -TERM "$google_pid" "$ms_token_pid" "$ms_sub_pid" 2>/dev/null || true
wait
