#!/bin/bash
# Script per aggiornare un singolo servizio o tutti i servizi
# Uso: ./k8s/update.sh [service-name]
# Esempi:
#   ./k8s/update.sh api         # Aggiorna solo api
#   ./k8s/update.sh             # Aggiorna tutti i servizi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT="${1:-production}"
SERVICE=$2

case "$ENVIRONMENT" in
    production)
        NAMESPACE="corretto"
        KUSTOMIZE_DIR="$SCRIPT_DIR/overlays/production"
        ;;
    staging)
        NAMESPACE="corretto-staging"
        KUSTOMIZE_DIR="$SCRIPT_DIR/overlays/staging"
        ;;
    *)
        echo "Usage: $0 [production|staging] [deployment-name]"
        echo "Examples:"
        echo "  $0 staging            # apply all staging manifests"
        echo "  $0 production api     # apply + restart api (prod)"
        exit 1
        ;;
esac

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

update_service() {
    local svc=$1
    echo -e "${BLUE}🔄 Aggiornamento $svc...${NC}"

    kubectl rollout restart deployment/$svc -n $NAMESPACE 2>/dev/null || true
    echo -e "${GREEN}✅ $svc riavviato${NC}"
}

echo -e "${BLUE}📦 Applicazione overlay Kustomize ($ENVIRONMENT)...${NC}"
kubectl apply -k "$KUSTOMIZE_DIR"

if [ -n "$SERVICE" ]; then
    update_service "$SERVICE"
fi

echo ""
echo -e "${GREEN}✅ Aggiornamento completato!${NC}"
echo ""

kubectl get pods -n $NAMESPACE
