#!/bin/bash
# Script fix dung lượng và setup auto-start cho EC2

set -e

cd ~/spark-realdata-pipeline || exit 1

echo "🧹 Dọn dẹp Docker để giải phóng dung lượng..."
docker-compose down 2>/dev/null || true
docker system prune -a -f

echo ""
echo "📝 Tạo file .env (nếu chưa có)..."
if [ ! -f .env ]; then
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
echo "🚀 Khởi động Docker Compose (không có Jupyter)..."
docker-compose up -d

echo ""
echo "⏳ Đợi containers khởi động (30 giây)..."
sleep 30

echo ""
echo "📊 Kiểm tra containers..."
docker-compose ps

echo ""
echo "🔍 Setup auto-start khi EC2 reboot..."
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

echo "✅ Đã setup auto-start service"
echo ""

echo "📋 Logs Airflow Scheduler:"
docker-compose logs airflow-scheduler --tail 20

echo ""
echo "✅ Hoàn tất!"
echo ""
echo "🌐 Airflow UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8081"
echo "   Username: admin | Password: admin"
echo ""
echo "⏰ DAG sẽ tự động chạy lúc 7:00 sáng VN (0:00 UTC) từ T2-T6"
echo ""
echo "📝 Lệnh hữu ích:"
echo "   - Xem logs: docker-compose logs airflow-scheduler --tail 50"
echo "   - Check DAG: docker-compose exec airflow-webserver airflow dags list"
echo "   - Restart: docker-compose restart"






