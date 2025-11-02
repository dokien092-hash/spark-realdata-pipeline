#!/bin/bash
# Script fix và khởi động lại pipeline

EC2_HOST="3.25.91.76"
EC2_USER="ec2-user"
KEY_PATH="$HOME/Downloads/financial-pipeline-key.pem"

echo "🔧 Fixing and restarting pipeline..."
echo ""

ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
cd ~/spark-realdata-pipeline

echo "🛑 Stopping all containers..."
docker-compose down

echo ""
echo "🌐 Checking network..."
docker network ls | grep data-network || docker-compose create network

echo ""
echo "🚀 Starting all containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting 30 seconds for containers to initialize..."
sleep 30

echo ""
echo "📦 Container status:"
docker-compose ps

echo ""
echo "🔧 Initializing Airflow database..."
docker-compose exec -T airflow-scheduler airflow db init 2>&1 | tail -10 || \
    docker exec airflow-scheduler airflow db init 2>&1 | tail -10

echo ""
echo "📋 Latest scheduler logs (last 20 lines):"
docker-compose logs airflow-scheduler --tail 20

echo ""
echo "✅ Pipeline restarted!"
echo ""
echo "📊 Check DAGs:"
docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial || \
    echo "⚠️  Scheduler still initializing, wait 1-2 minutes then check Airflow UI"

REMOTE_SCRIPT

echo ""
echo "✅ Fix completed!"
echo ""
echo "🌐 Check Airflow UI: http://3.25.91.76:8081"
echo "   Username: admin | Password: admin"




