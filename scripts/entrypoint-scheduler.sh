#!/bin/bash
set -e

echo "🔧 Initializing Airflow database..."
airflow db init || true

echo "📅 Starting Airflow scheduler..."
exec airflow scheduler

