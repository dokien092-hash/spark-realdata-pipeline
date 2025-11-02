#!/bin/bash
# Script tự động setup trên AWS EC2
# Chạy trên EC2 sau khi SSH vào

set -e

echo "🚀 Bắt đầu setup tự động trên EC2..."
echo ""

# 1. Vào thư mục project
cd ~/spark-realdata-pipeline || exit 1

# 2. Tạo file .env với API keys từ docker-compose.yml defaults
echo "📝 Tạo file .env với API keys..."
cat > .env << 'EOF'
POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
EOF

echo "✅ Đã tạo .env file"
echo ""

# 3. Set quyền cho scripts
echo "🔐 Set quyền cho scripts..."
chmod +x scripts/*.sh 2>/dev/null || true

# 4. Kiểm tra docker-compose
echo "🐳 Kiểm tra Docker và Docker Compose..."
docker --version
docker-compose --version
echo ""

# 5. Chạy Docker Compose
echo "🚀 Khởi động Docker Compose..."
echo "   (Lần đầu sẽ mất 3-5 phút để pull images)"
echo ""

docker-compose up -d

# 6. Chờ containers khởi động
echo "⏳ Đợi containers khởi động (30 giây)..."
sleep 30

# 7. Kiểm tra status
echo ""
echo "📊 Kiểm tra status containers..."
docker-compose ps

# 8. Kiểm tra logs Airflow scheduler
echo ""
echo "📋 Logs Airflow Scheduler (20 dòng cuối):"
docker-compose logs airflow-scheduler --tail 20

# 9. Kiểm tra DAG
echo ""
echo "🔍 Kiểm tra DAG status..."
docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag || echo "   (Chờ thêm vài giây để Airflow init xong)"

echo ""
echo "✅ Setup hoàn tất!"
echo ""
echo "🌐 Airflow UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8081"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📝 Lệnh hữu ích:"
echo "   - Xem logs: docker-compose logs airflow-scheduler --tail 50"
echo "   - Check containers: docker-compose ps"
echo "   - Stop: docker-compose down"
echo "   - Restart: docker-compose restart"





