#!/bin/bash
# Script per visualizzare i logs di un servizio
# Uso: ./k8s/logs.sh <service-name> [--follow]
# Esempi:
#   ./k8s/logs.sh api
#   ./k8s/logs.sh api --follow
#   ./k8s/logs.sh api -f

NAMESPACE="corretto"
SERVICE=$1
FOLLOW=$2

if [ -z "$SERVICE" ]; then
    echo "Uso: $0 <service-name> [--follow|-f]"
    echo ""
    echo "Servizi disponibili:"
    echo "  - api"
    echo "  - automations"
    echo "  - senders"
    echo "  - listeners"
    echo "  - refreshers"
    echo "  - broker-worker"
    echo "  - rabbitmq"
    exit 1
fi

FOLLOW_FLAG=""
if [ "$FOLLOW" == "--follow" ] || [ "$FOLLOW" == "-f" ]; then
    FOLLOW_FLAG="-f"
fi

kubectl logs $FOLLOW_FLAG deployment/$SERVICE -n $NAMESPACE --all-containers=true
