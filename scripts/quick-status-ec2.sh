#!/bin/bash
# Script nhanh để chạy TRÊN EC2 terminal

cd ~/spark-realdata-pipeline

echo "📦 Container Status:"
docker-compose ps

echo ""
echo "📊 Waiting for containers to be ready..."
sleep 5

echo ""
echo "🔍 Check Airflow Scheduler Logs (last 15 lines):"
docker-compose logs airflow-scheduler --tail 15

echo ""
echo "📋 Check if DAG is loaded:"
docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial || echo "⚠️  DAG chưa load (scheduler đang init... đợi 1-2 phút)"

echo ""
echo "💾 Check database connection:"
docker-compose exec -T postgres pg_isready -U postgres 2>/dev/null && echo "✅ Database OK" || echo "⚠️  Database not ready"

echo ""
echo "🌐 Airflow UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8081"
echo "   Username: admin | Password: admin"




