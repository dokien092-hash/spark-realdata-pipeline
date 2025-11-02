#!/bin/bash
# Script fix Airflow database init issue

cd ~/spark-realdata-pipeline || exit 1

echo "🔧 Fixing Airflow database initialization..."

# Method 1: Try exec
if docker-compose exec -T airflow-scheduler airflow db init 2>/dev/null; then
    echo "✅ Database initialized via exec"
else
    echo "⚠️  Exec failed, trying direct docker exec..."
    # Method 2: Direct docker exec
    docker exec airflow-scheduler bash -c "airflow db init" || {
        echo "⚠️  Container not ready, restarting first..."
        docker-compose restart airflow-scheduler
        sleep 15
        docker exec airflow-scheduler bash -c "airflow db init"
    }
fi

echo ""
echo "🔄 Restarting scheduler..."
docker-compose restart airflow-scheduler

echo ""
echo "⏳ Waiting 15 seconds..."
sleep 15

echo ""
echo "📋 Checking scheduler logs:"
docker-compose logs airflow-scheduler --tail 30

echo ""
echo "✅ Done! Check logs above for any errors."





