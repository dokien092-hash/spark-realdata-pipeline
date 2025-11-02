#!/bin/bash
# Script kiểm tra trạng thái pipeline trên EC2

EC2_HOST="3.25.91.76"
EC2_USER="ec2-user"
KEY_PATH="$HOME/Downloads/financial-pipeline-key.pem"

echo "🔍 Checking pipeline status on EC2..."
echo ""

ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
cd ~/spark-realdata-pipeline

echo "📦 Docker Containers Status:"
echo "================================"
docker-compose ps

echo ""
echo "📊 Airflow DAGs Status:"
echo "================================"
docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag || \
    docker exec airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag || \
    echo "⚠️  Cannot check DAGs (scheduler might be initializing)"

echo ""
echo "📅 Recent DAG Runs:"
echo "================================"
docker-compose exec -T airflow-webserver airflow dags list-runs -d financial_pipeline_dag --state running 2>/dev/null | head -5 || \
    docker exec airflow-webserver airflow dags list-runs -d financial_pipeline_dag --state running 2>/dev/null | head -5 || \
    echo "⚠️  Cannot check runs"

echo ""
echo "📋 Latest Airflow Scheduler Logs (last 30 lines):"
echo "================================"
docker-compose logs airflow-scheduler --tail 30 2>/dev/null | tail -30

echo ""
echo "💾 Database - Latest Finnhub Records:"
echo "================================"
docker-compose exec -T postgres psql -U airflow -d airflow -c "
SELECT COUNT(*) as total_records, 
       MAX(date) as latest_date, 
       COUNT(DISTINCT symbol) as unique_symbols
FROM stocks.stocks_daily_finnhub;
" 2>/dev/null || \
    docker exec postgres psql -U airflow -d airflow -c "
SELECT COUNT(*) as total_records, 
       MAX(date) as latest_date, 
       COUNT(DISTINCT symbol) as unique_symbols
FROM stocks.stocks_daily_finnhub;
" 2>/dev/null || \
    echo "⚠️  Cannot check database"

echo ""
echo "🌐 Access URLs:"
echo "================================"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
echo "Airflow UI: http://${PUBLIC_IP}:8081"
echo "  Username: admin | Password: admin"
echo "Grafana: http://${PUBLIC_IP}:3000"
echo ""
echo "⏰ Schedule: Daily at 7:00 AM VN time (0:00 UTC, Mon-Fri)"

REMOTE_SCRIPT

echo ""
echo "✅ Status check completed!"




