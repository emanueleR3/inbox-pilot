#!/bin/bash
# Script per aggiornare un singolo servizio o tutti i servizi
# Uso: ./k8s/update.sh [service-name]
# Esempi:
#   ./k8s/update.sh api         # Aggiorna solo api
#   ./k8s/update.sh             # Aggiorna tutti i servizi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="corretto"
SERVICE=$1

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

update_service() {
    local svc=$1
    echo -e "${BLUE}🔄 Aggiornamento $svc...${NC}"
    
    if [ -d "$SCRIPT_DIR/$svc" ]; then
        kubectl apply -f "$SCRIPT_DIR/$svc/"
        kubectl rollout restart deployment/$svc -n $NAMESPACE 2>/dev/null || true
        echo -e "${GREEN}✅ $svc aggiornato${NC}"
    else
        echo "⚠️  Directory $svc non trovata"
    fi
}

if [ -n "$SERVICE" ]; then
    # Aggiorna singolo servizio
    update_service "$SERVICE"
else
    # Aggiorna tutti i servizi
    echo "🔄 Aggiornamento di tutti i servizi..."
    echo ""
    
    for dir in api automations senders listeners refreshers broker-worker redis; do
        update_service "$dir"
    done
fi

echo ""
echo -e "${GREEN}✅ Aggiornamento completato!${NC}"
echo ""

kubectl get pods -n $NAMESPACE
