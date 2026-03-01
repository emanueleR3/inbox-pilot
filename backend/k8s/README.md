# Kubernetes Deployment per Corretto

Questa directory contiene tutte le configurazioni Kubernetes per deployare Corretto su k3s.

## Prerequisiti

### 1. Installazione k3s (singola macchina)

```bash
# Installa k3s
curl -sfL https://get.k3s.io | sh -

# Verifica installazione
sudo k3s kubectl get nodes

# Configura kubectl per l'utente corrente
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config
```

### 2. Configura accesso a GHCR (GitHub Container Registry)

```bash
# Crea il secret per pull delle immagini private
kubectl create namespace corretto

kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_PAT \
  -n corretto
```

### 3. File .env

Assicurati che il file `.env` nella root del progetto contenga tutte le variabili necessarie.

## Struttura (Kustomize)

Questa directory usa Kustomize per separare **base** e **ambienti** (staging/production).

```
k8s/
├── base/                       # Manifests condivisi (no namespace hardcoded)
│   ├── kustomization.yaml
│   ├── api/...
│   ├── automations/...
│   ├── broker-worker/...
│   ├── listeners/...
│   ├── qdrant/...
│   ├── rabbitmq/...
│   ├── redis/...
│   ├── refreshers/...
│   ├── senders/...
│   └── shared/...
├── overlays/
│   ├── production/             # Namespace corretto, hostnames prod
│   │   ├── kustomization.yaml
│   │   └── namespace.yaml
│   └── staging/                # Namespace corretto-staging, hostnames staging
│       ├── kustomization.yaml
│       ├── namespace.yaml
│       ├── resource-quota.yaml
│       ├── network-policy.yaml
│       └── patches/...
└── *.sh                         # Script di gestione (usa overlays)
```

## Script Disponibili

### Deploy completo
```bash
chmod +x k8s/*.sh
./k8s/deploy.sh production
./k8s/deploy.sh staging
```

### Visualizza stato
```bash
./k8s/status.sh
```

### Aggiorna servizi
```bash
# Applica tutti i manifests di un ambiente
./k8s/update.sh production
./k8s/update.sh staging

# Applica + restart di un singolo deployment
./k8s/update.sh production api
./k8s/update.sh staging api
```

### Visualizza logs
```bash
./k8s/logs.sh api
./k8s/logs.sh api --follow
```

### Rimuovi tutto
```bash
./k8s/teardown.sh
```

## Autoscaling (HPA)

L'autoscaling è configurato per:
- **api**: 2-10 repliche (CPU 70%, Memory 80%)
- **automations**: 2-8 repliche (CPU 70%, Memory 80%)
- **broker-worker**: 2-10 repliche (CPU 60%, Memory 70%)
- **senders**: 1-5 repliche (CPU 70%)

Per verificare lo stato HPA:
```bash
kubectl get hpa -n corretto
```

Per modificare i limiti:
```bash
kubectl edit hpa api-hpa -n corretto
```

## Comandi Utili

```bash
# Visualizza tutti i pod
kubectl get pods -n corretto

# Descrivi un pod (per debug)
kubectl describe pod <pod-name> -n corretto

# Esegui comando in un pod
kubectl exec -it <pod-name> -n corretto -- /bin/sh

# Port forward per accesso locale
kubectl port-forward svc/api 8000:8000 -n corretto
kubectl port-forward svc/rabbitmq 15672:15672 -n corretto

# Scala manualmente
kubectl scale deployment/api --replicas=5 -n corretto

# Visualizza risorse usate
kubectl top pods -n corretto

# Visualizza eventi
kubectl get events -n corretto --sort-by='.lastTimestamp'
```

## Rete e Accesso

- **API**: Accessibile via Ingress su `/api`
- **Listeners**: Esposto su NodePort 30001 per webhook esterni
- **RabbitMQ Management**: Port forward `kubectl port-forward svc/rabbitmq 15672:15672 -n corretto`

## Troubleshooting

### Pod in CrashLoopBackOff
```bash
kubectl logs <pod-name> -n corretto --previous
kubectl describe pod <pod-name> -n corretto
```

### ImagePullBackOff
```bash
# Verifica il secret GHCR
kubectl get secret ghcr-secret -n corretto -o yaml

# Ricrea il secret
kubectl delete secret ghcr-secret -n corretto
kubectl create secret docker-registry ghcr-secret ...
```

### HPA non scala
```bash
# Verifica metrics-server
kubectl get deployment metrics-server -n kube-system

# Verifica metriche
kubectl top pods -n corretto
```

## Migrazione da Docker Compose

1. Aggiorna i riferimenti agli host nei tuoi servizi:
   - `localhost` → nome del Service Kubernetes (es. `rabbitmq`, `senders`)
   - Le porte rimangono le stesse

2. Le variabili d'ambiente vengono ora gestite tramite Secrets Kubernetes

3. I volumi sono gestiti tramite PersistentVolumeClaims

## Redis

Redis è esposto nel namespace `corretto` come Service `redis` sulla porta `6379`.

Se vuoi Redis protetto da password, aggiungi queste variabili nel file `.env` (che viene importato in `corretto-secrets`):

```bash
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your-strong-password
```
