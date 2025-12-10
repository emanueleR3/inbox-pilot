#!/bin/bash
# Deploy script per Corretto su k3s
# Eseguire con: ./k8s/deploy.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="corretto"

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
echo "=========================================="
echo ""

# 1. Crea namespace
log_info "Creazione namespace..."
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
log_success "Namespace creato"

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
if [ -f "$SCRIPT_DIR/../.env" ]; then
    # Rimuovi secret esistente se presente
    kubectl delete secret corretto-secrets -n $NAMESPACE --ignore-not-found
    
    # Crea nuovo secret dal file .env
    kubectl create secret generic corretto-secrets \
        --from-env-file="/home/deploy/corretto/.env" \
        -n $NAMESPACE
    
    log_success "Secrets creati dal file .env"
else
    log_warning "File .env non trovato in /home/deploy/corretto"
    log_info "Puoi creare i secrets manualmente con:"
    echo "  kubectl create secret generic corretto-secrets --from-env-file=.env -n $NAMESPACE"
    
    # Applica il template secrets.yaml se esiste
    if [ -f "$SCRIPT_DIR/secrets.yaml" ]; then
        log_info "Applico template secrets.yaml..."
        kubectl apply -f "$SCRIPT_DIR/secrets.yaml"
    fi
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

# 5. Applica PVC condivisi
log_info "Creazione Persistent Volume Claims..."
kubectl apply -f "$SCRIPT_DIR/shared/"
log_success "PVCs creati"

# 6. Deploy RabbitMQ
log_info "Deploy RabbitMQ..."
kubectl apply -f "$SCRIPT_DIR/rabbitmq/"
log_success "RabbitMQ deployato"

log_info "Attesa avvio RabbitMQ..."
kubectl wait --for=condition=ready pod -l app=rabbitmq -n $NAMESPACE --timeout=180s || {
    log_warning "RabbitMQ non pronto entro il timeout, continuo comunque..."
}

# 7. Deploy Qdrant
log_info "Deploy Qdrant..."
kubectl apply -f "$SCRIPT_DIR/qdrant/"
log_success "Qdrant deployato"

log_info "Attesa avvio Qdrant..."
kubectl wait --for=condition=ready pod -l app=qdrant -n $NAMESPACE --timeout=180s || {
    log_warning "Qdrant non pronto entro il timeout, continuo comunque..."
}

# 8. Deploy servizi base
log_info "Deploy Senders..."
kubectl apply -f "$SCRIPT_DIR/senders/"
log_success "Senders deployato"

# 9. Deploy altri servizi
log_info "Deploy API..."
kubectl apply -f "$SCRIPT_DIR/api/"
log_success "API deployato"

log_info "Deploy Automations..."
kubectl apply -f "$SCRIPT_DIR/automations/"
log_success "Automations deployato"

log_info "Deploy Listeners..."
kubectl apply -f "$SCRIPT_DIR/listeners/"
log_success "Listeners deployato"

log_info "Deploy Refreshers..."
kubectl apply -f "$SCRIPT_DIR/refreshers/"
log_success "Refreshers deployato"

log_info "Deploy Broker Worker..."
kubectl apply -f "$SCRIPT_DIR/broker-worker/"
log_success "Broker Worker deployato"

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
