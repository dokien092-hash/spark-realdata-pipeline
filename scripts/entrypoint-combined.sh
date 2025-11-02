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

echo "🚀 Starting Airflow webserver and scheduler..."

# Start scheduler in background
airflow scheduler &
SCHEDULER_PID=$!

# Start webserver in foreground (Render needs a main process)
exec airflow webserver

