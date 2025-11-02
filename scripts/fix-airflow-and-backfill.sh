#!/bin/bash

# Fix Airflow services (deps + restart), unpause/clear DAG, and optionally backfill

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Repairing Airflow and optional backfill..."

START_DATE="${START_DATE:-}"
END_DATE="${END_DATE:-}"
DAYS_BACK="${DAYS_BACK:-1}"

echo "📦 Bringing up services (build to ensure pinned deps in entrypoints)..."
docker-compose up -d --build postgres airflow-webserver airflow-scheduler || true

echo "⏳ Waiting 20s for services to settle..."
sleep 20

echo "🔍 Current services:"
docker-compose ps

# In case entrypoint pip step failed earlier, install pinned deps directly
echo "📚 Ensuring Python deps inside Airflow containers..."
PINNED_PKGS=(
  "yfinance==0.2.28"
  "multitasking==0.0.10"
  "pandas==2.0.3"
  "numpy==1.24.4"
  "schedule"
  "kafka-python"
  "psycopg2-binary"
)

if docker-compose ps | grep -q "airflow-webserver"; then
  docker-compose exec airflow-webserver sh -lc "python -m pip install --no-cache-dir ${PINNED_PKGS[*]}" || true
fi

if docker-compose ps | grep -q "airflow-scheduler"; then
  docker-compose exec airflow-scheduler sh -lc "python -m pip install --no-cache-dir ${PINNED_PKGS[*]}" || true
fi

echo "📅 Unpausing DAG and clearing stuck runs (safe clear)..."
docker-compose exec airflow-webserver airflow dags unpause financial_pipeline_dag || true
docker-compose exec airflow-webserver airflow dags clear -y -c financial_pipeline_dag || true

echo "⏱️ Scheduler health (last 100 lines):"
docker-compose logs --no-color --tail=100 airflow-scheduler || true

echo "✅ Airflow repair done."

run_backfill() {
  if [[ -n "$START_DATE" && -n "$END_DATE" ]]; then
    echo "⏪ Backfilling range $START_DATE → $END_DATE (inclusive)"
    docker-compose exec airflow-webserver python /opt/airflow/jobs/data_processing/collect_monthly_data.py --start_date "$START_DATE" --end_date "$END_DATE"
  else
    echo "📡 Collecting last $DAYS_BACK day(s)"
    docker-compose exec airflow-webserver python /opt/airflow/jobs/data_processing/collect_monthly_data.py --days_back "$DAYS_BACK"
  fi
}

echo "🧪 Running data collection (on-demand)"
if ! run_backfill; then
  echo "⚠️ Webserver exec failed, retrying inside scheduler..."
  if [[ -n "$START_DATE" && -n "$END_DATE" ]]; then
    docker-compose exec airflow-scheduler python /opt/airflow/jobs/data_processing/collect_monthly_data.py --start_date "$START_DATE" --end_date "$END_DATE"
  else
    docker-compose exec airflow-scheduler python /opt/airflow/jobs/data_processing/collect_monthly_data.py --days_back "$DAYS_BACK"
  fi
fi

echo "🗄️ DB verification query:"
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "SELECT CURRENT_DATE AS today, MAX(date) AS latest_date, COUNT(*) FILTER (WHERE date=CURRENT_DATE) AS rows_today FROM stocks_daily;"

echo "🎉 Done. Daily Airflow schedule will run automatically going forward."


