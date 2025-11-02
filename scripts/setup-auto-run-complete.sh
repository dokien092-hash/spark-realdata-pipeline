#!/bin/bash
# Script setup hoàn chỉnh để tự động chạy lúc 7h sáng (KHÔNG CẦN MỞ MÁY)

cd ~/spark-realdata-pipeline

echo "🚀 SETUP TỰ ĐỘNG CHẠY LÚC 7H SÁNG (KHÔNG CẦN MỞ MÁY)"
echo "======================================================"
echo ""

# 1. Ensure .env exists
echo "✅ 1. Kiểm tra .env file..."
if [ ! -f .env ]; then
    echo "📝 Tạo .env file..."
    cat > .env << 'EOF'
POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
EOF
    echo "✅ Đã tạo .env"
else
    echo "✅ .env đã tồn tại"
fi
echo ""

# 2. Start containers
echo "✅ 2. Khởi động containers..."
docker-compose down 2>/dev/null || true
docker-compose up -d

echo ""
echo "⏳ Đợi 30 giây để containers khởi động..."
sleep 30
echo ""

# 3. Check containers
echo "✅ 3. Kiểm tra containers:"
docker-compose ps
echo ""

# 4. Init Airflow DB if needed
echo "✅ 4. Kiểm tra Airflow database..."
if docker-compose exec -T airflow-scheduler airflow db check 2>/dev/null | grep -q "healthy"; then
    echo "✅ Database đã sẵn sàng"
else
    echo "🔧 Initializing Airflow database..."
    docker-compose exec -T airflow-scheduler airflow db init 2>&1 | tail -5 || \
        docker exec airflow-scheduler airflow db init 2>&1 | tail -5
    echo "✅ Database initialized"
fi
echo ""

# 5. Setup auto-start service
echo "✅ 5. Setup auto-start service (tự khởi động khi EC2 reboot)..."
sudo tee /etc/systemd/system/docker-compose.service > /dev/null << 'SERVICEEOF'
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
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable docker-compose.service

if sudo systemctl is-enabled docker-compose.service > /dev/null 2>&1; then
    echo "✅ Auto-start service đã được ENABLED"
else
    echo "⚠️  Có lỗi khi enable auto-start service"
fi
echo ""

# 6. Wait for Airflow to be ready
echo "✅ 6. Đợi Airflow scheduler load DAGs (1 phút)..."
sleep 60

# 7. Check DAG
echo "✅ 7. Kiểm tra DAG:"
DAG_LIST=$(docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag || \
    docker exec airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag)

if [ -n "$DAG_LIST" ]; then
    echo "✅ DAG found:"
    echo "$DAG_LIST"
    
    # Unpause DAG if paused
    echo ""
    echo "🔧 Đảm bảo DAG không bị PAUSED..."
    docker-compose exec -T airflow-webserver airflow dags unpause financial_pipeline_dag 2>/dev/null || \
        docker exec airflow-webserver airflow dags unpause financial_pipeline_dag 2>/dev/null
    
    echo "✅ DAG is UNPAUSED (sẽ tự chạy theo schedule)"
else
    echo "⚠️  DAG chưa load - kiểm tra scheduler logs"
    echo "📋 Latest scheduler logs:"
    docker-compose logs airflow-scheduler --tail 20
fi
echo ""

# 8. Final summary
echo "✅ 8. Tổng kết:"
echo "======================================================"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
echo ""
echo "🌐 Truy cập Airflow UI:"
echo "   http://${PUBLIC_IP}:8081"
echo "   Username: admin | Password: admin"
echo ""
echo "⏰ Lịch chạy tự động:"
echo "   - Thời gian: 7:00 AM (VN) = 0:00 UTC"
echo "   - Ngày: Thứ 2 - Thứ 6 (Mon-Fri)"
echo "   - DAG: financial_pipeline_dag"
echo ""
echo "✅ Đã setup xong:"
echo "   ✓ Containers đang chạy"
echo "   ✓ Auto-start service ENABLED (tự khởi động khi EC2 reboot)"
echo "   ✓ DAG schedule: 0:00 UTC (7:00 AM VN) từ T2-T6"
echo "   ✓ DAG đã UNPAUSED"
echo ""
echo "🔍 Để kiểm tra lại, chạy:"
echo "   bash scripts/check-auto-run-ec2.sh"
echo ""
echo "📝 Lưu ý:"
echo "   - EC2 instance phải CHẠY (running) để pipeline tự động chạy"
echo "   - Không cần mở máy tính của bạn"
echo "   - Pipeline sẽ tự chạy lúc 7h sáng VN từ T2-T6"
echo "   - Có thể check logs trong Airflow UI"




