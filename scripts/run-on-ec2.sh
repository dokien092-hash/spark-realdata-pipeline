#!/bin/bash
# Script chạy lệnh trên EC2 từ xa

EC2_HOST="3.25.91.76"
EC2_USER="ec2-user"
KEY_PATH="$HOME/Downloads/financial-pipeline-key.pem"

echo "🔌 Connecting to EC2 and running command..."
echo ""

# Chạy lệnh fix Airflow DB
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
cd ~/spark-realdata-pipeline

echo "🔧 Fixing Airflow database initialization..."

# Check if containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  Containers not running, starting..."
    docker-compose up -d
    sleep 20
fi

# Init database
echo "📊 Initializing Airflow database..."
docker exec airflow-scheduler airflow db init 2>&1 | tail -10

# Restart scheduler
echo ""
echo "🔄 Restarting scheduler..."
docker-compose restart airflow-scheduler

# Wait and check logs
echo ""
echo "⏳ Waiting 15 seconds..."
sleep 15

echo ""
echo "📋 Recent scheduler logs:"
docker-compose logs airflow-scheduler --tail 20

echo ""
echo "✅ Check status:"
docker-compose ps

echo ""
echo "🌐 Airflow UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8081"
REMOTE_SCRIPT

echo ""
echo "✅ Command completed!"




