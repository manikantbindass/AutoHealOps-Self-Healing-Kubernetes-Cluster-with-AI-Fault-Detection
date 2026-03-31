# 🔧 AutoHealOps — Complete Setup Guide

## Prerequisites

Install the following tools before starting:

```bash
# 1. Docker (https://docs.docker.com/get-docker/)
docker --version  # Should be >= 24.x

# 2. Docker Compose
docker-compose --version  # Should be >= 2.x

# 3. Minikube (https://minikube.sigs.k8s.io/docs/start/)
minikube version  # Should be >= 1.30

# 4. kubectl (https://kubernetes.io/docs/tasks/tools/)
kubectl version --client  # Should be >= 1.27

# 5. Node.js (https://nodejs.org/)
node --version  # Should be >= 18.x

# 6. Python
python3 --version  # Should be >= 3.9
```

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/manikantbindass/AutoHealOps-Self-Healing-Kubernetes-Cluster-with-AI-Fault-Detection.git
cd AutoHealOps-Self-Healing-Kubernetes-Cluster-with-AI-Fault-Detection
```

---

## Step 2: Environment Configuration

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your values
nano .env
```

Required variables in `.env`:
```
MONGO_URI=mongodb://localhost:27017/autohealops
JWT_SECRET=your-super-secret-jwt-key-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
EMAIL_FROM=alerts@yourdomain.com
EMAIL_PASSWORD=your-email-app-password
PROMETHEUS_URL=http://localhost:9090
AI_ENGINE_URL=http://localhost:8001
```

---

## Step 3: Start with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Run in background (detached)
docker-compose up -d --build

# Check running services
docker-compose ps
```

Services started:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| AI Engine | http://localhost:8001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 |
| MongoDB | localhost:27017 |

---

## Step 4: Start Kubernetes Cluster

```bash
# Start Minikube
minikube start --memory=4096 --cpus=2 --driver=docker

# Verify cluster is running
kubectl cluster-info
kubectl get nodes

# Apply all Kubernetes manifests
kubectl apply -f k8s/

# Verify deployments
kubectl get pods
kubectl get services
```

---

## Step 5: Deploy Monitoring Stack

```bash
# Install Prometheus via Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack

# OR use the provided config
kubectl apply -f monitoring/

# Access Prometheus
kubectl port-forward service/prometheus-server 9090:80

# Access Grafana
kubectl port-forward service/grafana 3001:80
# Default credentials: admin / admin
```

---

## Step 6: Run AI Engine (Standalone)

```bash
cd ai-engine
pip install -r requirements.txt

# Generate training data
python ../scripts/data-generator.py

# Train the anomaly detection model
python training/train_anomaly.py

# Start AI engine server
python main.py
```

---

## Step 7: Simulate Failures (Testing)

```bash
# Simulate pod crash
kubectl delete pod <pod-name>

# Simulate high CPU
kubectl run stress-test --image=progrium/stress -- --cpu 4 --timeout 60s

# Simulate memory spike
kubectl run mem-test --image=progrium/stress -- --vm 2 --vm-bytes 512M --timeout 60s

# Watch auto-healing in action
kubectl get pods --watch
```

---

## Step 8: Access Dashboard

```bash
# Open browser
open http://localhost:3000

# Login with default credentials
# Username: admin
# Password: autohealops123
```

---

## Troubleshooting

```bash
# Check service logs
docker-compose logs backend
docker-compose logs ai-engine

# Check Kubernetes pod logs
kubectl logs <pod-name>

# Restart a specific service
docker-compose restart backend

# Reset Minikube
minikube delete && minikube start

# Check MongoDB connection
docker exec -it autohealops-mongo mongosh
```

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `Port 3000 already in use` | `lsof -ti:3000 \| xargs kill -9` |
| `Cannot connect to MongoDB` | Check `MONGO_URI` in `.env` |
| `Minikube not starting` | Increase Docker memory to 6GB |
| `kubectl not found` | Install kubectl and add to PATH |
| `Model not found` | Run `python training/train_anomaly.py` first |
