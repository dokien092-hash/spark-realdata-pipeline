#!/bin/bash

# Start Financial Data Pipeline
# Simplified script for financial data processing

set -e

echo "🚀 Starting Financial Data Pipeline..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start all services
echo "📦 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

# Ensure Airflow DAG is unpaused
echo "📅 Ensuring Airflow DAG is unpaused..."
docker-compose exec airflow-webserver airflow dags unpause financial_pipeline_dag || true

# Optional backfill: set START_DATE=YYYY-MM-DD END_DATE=YYYY-MM-DD before running this script
if [ -n "$START_DATE" ] && [ -n "$END_DATE" ]; then
    echo "⏪ Backfilling data from $START_DATE to $END_DATE (inclusive)..."
    docker-compose exec airflow-webserver python /opt/airflow/jobs/data_processing/collect_monthly_data.py --start_date "$START_DATE" --end_date "$END_DATE"
else
    echo "📡 Starting daily scheduler-driven pipeline (no manual backfill requested)"
fi

echo ""
echo "✅ Financial Data Pipeline Started!"
echo ""
echo "🌐 Access Points:"
echo "  - Jupyter Lab: http://localhost:8888"
echo "  - Airflow: http://localhost:8081 (admin/admin)"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "📊 Pipeline Components:"
echo "  ✅ Data Ingestion (Yahoo Finance → Kafka)"
echo "  ✅ Data Processing (Kafka → PostgreSQL)"
echo "  ✅ Airflow DAG (Workflow orchestration)"
echo "  ✅ Grafana Dashboard (Monitoring)"
echo ""
echo "🔍 Check pipeline status:"
echo "  - Kafka topics: docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092"
echo "  - PostgreSQL data: docker-compose exec postgres psql -U postgres -d realdata_warehouse -c 'SELECT COUNT(*) FROM stocks_daily;'"
echo "  - Airflow DAGs: curl -s http://localhost:8081/api/v1/dags"
echo ""
echo "📋 Next steps:"
echo "  1. Open Jupyter Lab to run financial analysis"
echo "  2. Check Grafana dashboard for monitoring"
echo "  3. Monitor Airflow DAG for workflow status"

