# 📋 Software Requirements Specification (SRS)
## AutoHealOps – Self-Healing Kubernetes Cluster with AI Fault Detection

**Version:** 1.0  
**Author:** Manikant Kumar  
**Date:** March 2026

---

## 1. Introduction

### 1.1 Purpose
This document defines the functional and non-functional requirements for AutoHealOps — an AI-powered Kubernetes self-healing platform.

### 1.2 Scope
AutoHealOps monitors Kubernetes clusters, detects anomalies using ML models, predicts failures, and automatically performs healing actions without human intervention.

### 1.3 Definitions
- **Anomaly**: Abnormal metric behavior deviating from baseline
- **Self-Healing**: Automated recovery from detected failures
- **LSTM**: Long Short-Term Memory neural network for time-series
- **Isolation Forest**: Unsupervised ML algorithm for anomaly detection

---

## 2. System Overview

```
Input: Kubernetes Metrics (CPU, Memory, Network, Pod status)
Process: Anomaly Detection → Failure Prediction → Healing Decision
Output: Automated recovery actions + Dashboard alerts
```

---

## 3. Functional Requirements

### 3.1 AI Fault Detection Engine
- FR-01: System SHALL collect metrics every 15 seconds via Prometheus
- FR-02: System SHALL apply Isolation Forest for real-time anomaly detection
- FR-03: System SHALL flag anomalies with severity: LOW / MEDIUM / HIGH / CRITICAL
- FR-04: System SHALL store all anomaly records in MongoDB

### 3.2 Predictive Failure System
- FR-05: System SHALL use LSTM to forecast metrics for next 30 minutes
- FR-06: System SHALL output: failure probability (0-1) and time-to-failure (minutes)
- FR-07: System SHALL retrain model weekly on latest data

### 3.3 Self-Healing Mechanism
- FR-08: System SHALL restart crashed pods automatically within 30 seconds
- FR-09: System SHALL scale deployments when CPU > 80% for 3 consecutive minutes
- FR-10: System SHALL reschedule pods when node health drops below threshold
- FR-11: System SHALL log all healing actions with timestamps

### 3.4 Monitoring Dashboard
- FR-12: Dashboard SHALL display real-time cluster health score (0-100)
- FR-13: Dashboard SHALL show live graphs updated via WebSocket
- FR-14: Dashboard SHALL display active alerts and AI predictions
- FR-15: Dashboard SHALL provide incident log with filtering

### 3.5 Alerting System
- FR-16: System SHALL send email alerts for CRITICAL anomalies
- FR-17: System SHALL send Slack notifications for HIGH/CRITICAL events
- FR-18: Alert thresholds SHALL be configurable via environment variables

---

## 4. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | API response < 200ms for 95th percentile |
| Availability | 99.9% uptime for monitoring service |
| Scalability | Support clusters up to 100 nodes |
| Security | JWT auth, RBAC, encrypted secrets |
| Latency | Anomaly detection < 5 seconds from metric collection |
| Storage | Metrics retained for 30 days |

---

## 5. System Constraints
- Requires Kubernetes 1.24+
- Python 3.9+ for AI engine
- Minimum 4GB RAM for Minikube
- Docker and Docker Compose required for local development

---

## 6. Assumptions
- Prometheus is the primary metrics source
- Users have basic Kubernetes knowledge for setup
- Internet connectivity for Docker image pulls
