#!/bin/bash
set -e

echo "🔧 Initializing Airflow database..."
airflow db init || true

echo "👤 Creating admin user..."
airflow users create \
  --role Admin \
  --username admin \
  --password admin \
  --email admin@example.com \
  --firstname admin \
  --lastname admin || true

echo "🚀 Starting Airflow webserver in background..."
airflow webserver &
WEBSERVER_PID=$!

echo "📅 Starting Airflow scheduler..."
airflow scheduler &
SCHEDULER_PID=$!

# Wait for processes
wait $WEBSERVER_PID $SCHEDULER_PID

