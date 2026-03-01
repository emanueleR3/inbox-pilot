#!/bin/bash
# Deploy script per Corretto su k3s
# Eseguire con: ./k8s/deploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT="${1:-production}"

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
        echo "Usage: $0 [production|staging]"
        exit 1
        ;;
esac

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verifica che kubectl sia disponibile
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl non trovato. Assicurati che k3s sia installato."
    exit 1
fi

# Verifica connessione al cluster
if ! kubectl cluster-info &> /dev/null; then
    log_error "Impossibile connettersi al cluster Kubernetes."
    log_info "Se usi k3s, prova: export KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
    exit 1
fi

echo ""
echo "=========================================="
echo "🚀 Deploying Corretto to Kubernetes (k3s)"
echo "Environment: $ENVIRONMENT"
echo "=========================================="
echo ""

# 1. Crea namespace (via overlay)
log_info "Creazione namespace ($NAMESPACE)..."
kubectl apply -k "$KUSTOMIZE_DIR" --server-side=false --dry-run=client >/dev/null 2>&1 || true
kubectl apply -f "$KUSTOMIZE_DIR/namespace.yaml"
log_success "Namespace pronto"

# 2. Verifica/crea secret per GHCR
if ! kubectl get secret ghcr-secret -n $NAMESPACE &> /dev/null; then
    log_warning "Secret 'ghcr-secret' non trovato!"
    echo ""
    echo "Per creare il secret per GitHub Container Registry, esegui:"
    echo ""
    echo "  kubectl create secret docker-registry ghcr-secret \\"
    echo "    --docker-server=ghcr.io \\"
    echo "    --docker-username=YOUR_GITHUB_USERNAME \\"
    echo "    --docker-password=YOUR_GITHUB_PAT \\"
    echo "    -n $NAMESPACE"
    echo ""
    read -p "Vuoi continuare senza il secret GHCR? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    log_success "Secret GHCR già presente"
fi

# 3. Crea secrets dal file .env
log_info "Creazione secrets dal file .env..."
ENV_FILE="/home/deploy/corretto/.env"
if [ -f "$ENV_FILE" ]; then
    # Rimuovi secret esistente se presente
    kubectl delete secret corretto-secrets -n $NAMESPACE --ignore-not-found
    
    # Crea nuovo secret dal file .env
    kubectl create secret generic corretto-secrets \
        --from-env-file="$ENV_FILE" \
        -n $NAMESPACE
    
    log_success "Secrets creati dal file .env"
else
    log_warning "File .env non trovato in $ENV_FILE"
    log_info "Crea i secrets manualmente con:"
    echo "  kubectl create secret generic corretto-secrets --from-env-file=.env -n $NAMESPACE"
fi

# 4. Crea secret per Google Service Account (se esiste il file)
if [ -f "/home/deploy/corretto/listeners/service-account-key.json" ]; then
    log_info "Creazione secret Google Service Account..."
    kubectl create secret generic google-service-account \
        --from-file=service-account-key.json="/home/deploy/corretto/listeners/service-account-key.json" \
        -n $NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    log_success "Secret Google creato"
else
    log_warning "File service-account-key.json non trovato, skippo..."
fi

# 5. Deploy completo via Kustomize overlay
log_info "Applico overlay Kustomize ($KUSTOMIZE_DIR)..."
kubectl apply -k "$KUSTOMIZE_DIR"
log_success "Overlay applicato"

# 6. Attendi rollout dei deployment principali
log_info "Attesa rollout deployments..."
for deploy in api automations broker-worker listeners refreshers senders redis rabbitmq qdrant; do
    kubectl rollout status deployment/$deploy -n $NAMESPACE --timeout=180s || {
        log_warning "$deploy non pronto entro il timeout, continuo comunque..."
    }
done

echo ""
echo "=========================================="
echo "🎉 Deployment completato!"
echo "=========================================="
echo ""

# Mostra stato
log_info "Stato dei pod:"
kubectl get pods -n $NAMESPACE

echo ""
log_info "Stato HPA:"
kubectl get hpa -n $NAMESPACE

echo ""
log_info "Servizi:"
kubectl get svc -n $NAMESPACE

echo ""
log_info "Comandi utili:"
echo "  - Visualizza pod:      kubectl get pods -n $NAMESPACE"
echo "  - Visualizza logs:     kubectl logs -f deployment/api -n $NAMESPACE"
echo "  - Descrivi pod:        kubectl describe pod <pod-name> -n $NAMESPACE"
echo "  - Port forward API:    kubectl port-forward svc/api 8000:8000 -n $NAMESPACE"
echo "  - Scala deployment:    kubectl scale deployment/api --replicas=5 -n $NAMESPACE"
echo "  - Elimina tutto:       kubectl delete namespace $NAMESPACE"
