#!/bin/bash
set -e

echo "🚀 AutoHealOps - Full Setup Script"
echo "===================================="

# Check dependencies
check_cmd() {
  if ! command -v $1 &> /dev/null; then
    echo "❌ $1 is not installed. Please install it first."
    exit 1
  fi
  echo "✅ $1 found"
}

check_cmd docker
check_cmd docker-compose
check_cmd python3
check_cmd node
check_cmd kubectl
check_cmd minikube

# Copy env file
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env file created from .env.example"
fi

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend && npm install && cd ..

# Install Python AI engine dependencies
echo "🐍 Installing AI engine dependencies..."
cd ai-engine && pip3 install -r requirements.txt && cd ..

# Install Python backend dependencies  
echo "🐍 Installing backend dependencies..."
cd backend && pip3 install -r requirements.txt && cd ..

# Generate synthetic data
echo "📊 Generating training data..."
python3 scripts/data-generator.py

# Train AI model
echo "🧠 Training anomaly detection model..."
cd ai-engine && python3 training/train_anomaly.py && cd ..

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d --build

echo ""
echo "✅ AutoHealOps Setup Complete!"
echo "================================"
echo "🌐 Frontend:   http://localhost:3000"
echo "🔧 Backend:    http://localhost:8000"
echo "🧠 AI Engine:  http://localhost:8001"
echo "📊 Prometheus: http://localhost:9090"
echo "📈 Grafana:    http://localhost:3001"
echo ""
echo "Next: Run 'minikube start' and 'kubectl apply -f k8s/' for K8s"
