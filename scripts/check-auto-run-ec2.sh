#!/bin/bash
# Script chạy TRÊN EC2 để kiểm tra tự động chạy lúc 7h sáng

cd ~/spark-realdata-pipeline

echo "🔍 KIỂM TRA TỰ ĐỘNG CHẠY LÚC 7H SÁNG"
echo "=========================================="
echo ""

echo "✅ 1. Kiểm tra Docker containers:"
echo "--------------------------------------------"
docker-compose ps
echo ""

echo "✅ 2. Kiểm tra Auto-start service:"
echo "--------------------------------------------"
if sudo systemctl is-enabled docker-compose.service 2>/dev/null; then
    echo "✅ Auto-start ENABLED"
    sudo systemctl status docker-compose.service --no-pager | head -8
else
    echo "⚠️  Auto-start NOT ENABLED"
    echo ""
    echo "🔧 Setup auto-start (copy và chạy):"
    echo "sudo tee /etc/systemd/system/docker-compose.service > /dev/null << 'EOF'
[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/spark-realdata-pipeline
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ec2-user
Group=docker

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable docker-compose.service"
fi
echo ""

echo "✅ 3. Kiểm tra Airflow DAG:"
echo "--------------------------------------------"
sleep 5
DAG_STATUS=$(docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag || echo "")
if [ -n "$DAG_STATUS" ]; then
    echo "✅ DAG found:"
    echo "$DAG_STATUS"
    
    # Check schedule
    SCHEDULE_INFO=$(docker-compose exec -T airflow-webserver airflow dags show financial_pipeline_dag 2>/dev/null | grep -A 2 "schedule_interval" | head -3 || echo "")
    if [ -n "$SCHEDULE_INFO" ]; then
        echo ""
        echo "📅 Schedule info:"
        echo "$SCHEDULE_INFO"
    fi
else
    echo "⚠️  DAG chưa load - đợi scheduler init (1-2 phút)"
fi
echo ""

echo "✅ 4. Kiểm tra Database:"
echo "--------------------------------------------"
if docker-compose exec -T postgres pg_isready -U postgres 2>/dev/null | grep -q "accepting"; then
    echo "✅ PostgreSQL OK"
else
    echo "⚠️  PostgreSQL not ready"
fi
echo ""

echo "✅ 5. Kiểm tra Scheduler logs (errors only):"
echo "--------------------------------------------"
docker-compose logs airflow-scheduler --tail 30 2>/dev/null | grep -i "error\|exception\|failed" | tail -5 || echo "✅ No recent errors"
echo ""

echo "✅ 6. Kiểm tra .env file:"
echo "--------------------------------------------"
if [ -f .env ]; then
    echo "✅ .env exists"
    if grep -q "FINNHUB_API_KEY=" .env && ! grep -q "FINNHUB_API_KEY=$" .env; then
        echo "✅ FINNHUB_API_KEY configured"
    else
        echo "⚠️  FINNHUB_API_KEY missing in .env"
    fi
else
    echo "⚠️  .env missing - create it with API keys"
fi
echo ""

echo "✅ 7. Tổng kết:"
echo "--------------------------------------------"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
echo "🌐 Airflow UI: http://${PUBLIC_IP}:8081"
echo "   Username: admin | Password: admin"
echo ""
echo "⏰ DAG sẽ tự động chạy lúc 7:00 AM VN (0:00 UTC) từ T2-T6"
echo ""
echo "📝 Để đảm bảo tự động chạy:"
echo "   1. ✅ Containers đang chạy"
echo "   2. ⚠️  Auto-start service ENABLED (check trên)"
echo "   3. ⚠️  DAG schedule đúng (check trên)"
echo "   4. ⚠️  DAG không bị PAUSED (check trong Airflow UI)"




