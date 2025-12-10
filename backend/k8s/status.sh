#!/bin/bash
# Script per visualizzare lo stato del cluster Corretto
# Eseguire con: ./k8s/status.sh

NAMESPACE="corretto"

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${BLUE}=========================================="
echo "📊 Stato Cluster Corretto"
echo "==========================================${NC}"
echo ""

echo -e "${GREEN}📦 PODS:${NC}"
kubectl get pods -n $NAMESPACE -o wide
echo ""

echo -e "${GREEN}📈 HORIZONTAL POD AUTOSCALERS:${NC}"
kubectl get hpa -n $NAMESPACE
echo ""

echo -e "${GREEN}🔗 SERVICES:${NC}"
kubectl get svc -n $NAMESPACE
echo ""

echo -e "${GREEN}🌐 INGRESS:${NC}"
kubectl get ingress -n $NAMESPACE
echo ""

echo -e "${GREEN}💾 PERSISTENT VOLUME CLAIMS:${NC}"
kubectl get pvc -n $NAMESPACE
echo ""

echo -e "${GREEN}🚀 DEPLOYMENTS:${NC}"
kubectl get deployments -n $NAMESPACE
echo ""

echo -e "${YELLOW}📊 RISORSE (se metrics-server è attivo):${NC}"
kubectl top pods -n $NAMESPACE 2>/dev/null || echo "  Metrics server non disponibile"
echo ""
