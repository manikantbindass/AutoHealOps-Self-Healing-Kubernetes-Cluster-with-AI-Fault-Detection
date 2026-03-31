# 🏗️ AutoHealOps — System Architecture

## Overview

AutoHealOps follows a **microservices architecture** with 5 core services communicating via REST APIs and WebSockets, all orchestrated on Kubernetes.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AutoHealOps Platform                         │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Frontend    │    │   Backend    │    │    AI Engine      │   │
│  │  React +      │◄──►│   FastAPI    │◄──►│  Python          │   │
│  │  TailwindCSS  │    │  WebSockets  │    │  Isolation Forest │   │
│  │  Port: 3000   │    │  Port: 8000  │    │  LSTM Model       │   │
│  └──────────────┘    └──────┬───────┘    └──────────────────┘   │
│                              │                                    │
│                    ┌─────────▼─────────┐                         │
│                    │     MongoDB        │                         │
│                    │   Metrics & Logs   │                         │
│                    │   Port: 27017      │                         │
│                    └─────────┬─────────┘                         │
│                              │                                    │
│  ┌──────────────┐    ┌───────▼──────────┐                       │
│  │   Grafana     │    │   Prometheus      │                       │
│  │  Port: 3001   │◄───│   Port: 9090      │                       │
│  └──────────────┘    └───────┬───────────┘                       │
│                              │ Scrapes metrics                    │
│                    ┌─────────▼─────────────────┐                 │
│                    │     Kubernetes Cluster      │                 │
│                    │  ┌────────┐  ┌──────────┐  │                 │
│                    │  │  Pods  │  │  Nodes   │  │                 │
│                    │  └────────┘  └──────────┘  │                 │
│                    └───────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
1. Kubernetes metrics → Prometheus (every 15s)
2. Prometheus → AI Engine (pull every 30s)
3. AI Engine → Anomaly detected? → Backend API
4. Backend API → MongoDB (store) + Frontend (WebSocket push)
5. Backend API → Self-Healing Script (if CRITICAL)
6. Self-Healing Script → Kubernetes API (restart/scale)
7. Backend API → Email/Slack (alert)
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|----------|
| Frontend | React.js + TailwindCSS | Dashboard UI |
| Charts | Chart.js / Recharts | Metric visualization |
| Backend | FastAPI + WebSockets | REST API + realtime |
| AI Engine | Python + Scikit-learn + TensorFlow | ML models |
| Database | MongoDB | Metrics & incident logs |
| Metrics | Prometheus | Time-series collection |
| Visualization | Grafana | Ops dashboard |
| Orchestration | Kubernetes (Minikube) | Container orchestration |
| Messaging | Kafka | Event streaming |
| Auth | JWT | API security |
| Deployment | Docker Compose | Local dev setup |

---

## AI Models

### Model 1: Isolation Forest (Anomaly Detection)
```
Input:  [cpu_usage, memory_usage, pod_restarts, network_latency]
Output: anomaly_score (-1 = anomaly, 1 = normal)
Train:  Unsupervised on 30 days of historical metrics
```

### Model 2: LSTM (Failure Prediction)
```
Input:  Time-series sequence (last 60 data points, 4 features)
Output: [failure_probability, minutes_to_failure]
Train:  Supervised on labeled failure events
Window: 60 timesteps × 4 features
```

---

## Healing Decision Logic

```python
if anomaly_score == -1:
    if metric == "pod_restarts" and value > 5:
        action = "restart_pod"
    elif metric == "cpu_usage" and value > 0.9:
        action = "scale_deployment"
    elif metric == "memory_usage" and value > 0.85:
        action = "scale_deployment"
    elif node_health < 0.3:
        action = "reschedule_pods"
```

---

## Security Architecture

- **Network Policies**: Restrict pod-to-pod communication
- **RBAC**: Kubernetes roles with least-privilege access
- **JWT**: 24-hour token expiry, RS256 signing
- **Secrets**: Kubernetes Secrets for DB credentials, API keys
- **TLS**: Ingress with cert-manager for HTTPS
