#!/bin/bash
# Script per rimuovere completamente il deployment Corretto
# Eseguire con: ./k8s/teardown.sh

set -e

NAMESPACE="corretto"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${RED}=========================================="
echo "⚠️  ATTENZIONE: Rimozione completa Corretto"
echo "==========================================${NC}"
echo ""

read -p "Sei sicuro di voler eliminare TUTTO il namespace '$NAMESPACE'? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operazione annullata."
    exit 0
fi

echo ""
echo -e "${YELLOW}Eliminazione namespace $NAMESPACE...${NC}"

kubectl delete namespace $NAMESPACE --ignore-not-found

echo ""
echo -e "${GREEN}✅ Namespace '$NAMESPACE' eliminato completamente.${NC}"
echo ""
echo "I PersistentVolumes potrebbero rimanere. Per rimuoverli:"
echo "  kubectl get pv | grep $NAMESPACE"
echo "  kubectl delete pv <pv-name>"
