#!/bin/bash

# Daily Pipeline Health Check
# Run this to verify everything is working

set -e

echo "🔍 Checking Pipeline Health..."
echo ""

# 1. Services status
echo "📦 Services Status:"
docker-compose ps
echo ""

# 2. Latest data
echo "📊 Latest Data:"
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "
SELECT 
    CURRENT_DATE as today,
    MAX(date) as latest_data,
    CURRENT_DATE - MAX(date) as days_behind,
    COUNT(*) as total_records,
    COUNT(DISTINCT symbol) as symbols
FROM stocks_daily;
"
echo ""

# 3. Data freshness by date
echo "📅 Recent Data (Last 7 Days):"
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "
SELECT 
    date,
    COUNT(*) as symbols,
    ROUND(AVG(daily_return)::numeric, 2) as avg_return
FROM stocks_daily
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY date
ORDER BY date DESC;
"
echo ""

# 4. Airflow DAG status
echo "🌊 Airflow DAG Status:"
docker-compose exec airflow-webserver airflow dags list | grep financial_pipeline_dag || echo "DAG not found"
echo ""

# 5. Last 3 runs
echo "📝 Last 3 DAG Runs:"
docker-compose exec airflow-webserver airflow dags list-runs -d financial_pipeline_dag 2>/dev/null | head -6
echo ""

# 6. Next execution
echo "⏰ Next Scheduled Run:"
docker-compose exec airflow-webserver airflow dags next-execution financial_pipeline_dag 2>/dev/null || echo "No next execution scheduled"
echo ""

# 7. Environment check
echo "🔑 Environment Variables:"
docker-compose exec airflow-scheduler printenv POLYGON_API_KEY >/dev/null 2>&1 && echo "✅ POLYGON_API_KEY: Set" || echo "❌ POLYGON_API_KEY: Not set"
echo ""

echo "✅ Health check complete!"
echo ""
echo "📌 Quick Actions:"
echo "  - Trigger DAG now: docker-compose exec airflow-webserver airflow dags trigger financial_pipeline_dag"
echo "  - View UI: open http://localhost:8081"
echo "  - View data: open http://localhost:8888"

