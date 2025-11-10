#!/bin/bash
# ============================================================
# SCRIPT KHỞI ĐỘNG PIPELINE TRÊN DOCKER LOCAL
# ============================================================

set -e

echo "🚀 KHỞI ĐỘNG PIPELINE LOCAL"
echo "=========================================="
echo ""

# Kiểm tra Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker chưa chạy!"
    echo ""
    echo "📋 Hãy mở Docker Desktop và đợi Docker sẵn sàng"
    echo "   Sau đó chạy lại script này"
    exit 1
fi

echo "✅ Docker đang chạy"
echo ""

# Vào thư mục project
cd "$(dirname "$0")/.."

# Tạo .env nếu chưa có
if [ ! -f .env ]; then
    echo "📝 Tạo file .env..."
    cat > .env << 'EOF'
POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
EOF
    echo "✅ Đã tạo .env"
fi

# Fix Airflow logs permissions
echo "🔧 Fixing Airflow logs permissions..."
mkdir -p airflow/logs/scheduler airflow/logs/webserver
chmod -R 777 airflow/logs 2>/dev/null || true

# Dừng containers cũ
echo "🛑 Dừng containers cũ..."
docker-compose down 2>/dev/null || true

# Khởi động containers
echo "🚀 Khởi động containers..."
echo "   (Lần đầu sẽ mất 3-5 phút để pull images)"
docker-compose up -d

# Đợi containers sẵn sàng
echo "⏳ Đợi containers khởi động (60 giây)..."
sleep 60

# Kiểm tra status
echo ""
echo "📊 Trạng thái containers:"
docker-compose ps

# Kiểm tra Airflow logs
echo ""
echo "📋 Kiểm tra Airflow logs..."
docker-compose logs airflow-scheduler --tail 10 2>&1 | grep -i error || echo "✅ Không có lỗi"

# Kiểm tra DAG
echo ""
echo "📋 Kiểm tra DAGs..."
sleep 10
docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial || echo "⏳ Đợi thêm vài giây để DAGs load..."

# Unpause DAG
echo ""
echo "📋 Unpausing financial_pipeline_dag..."
docker-compose exec -T airflow-webserver airflow dags unpause financial_pipeline_dag 2>/dev/null || echo "DAG sẽ được unpause khi sẵn sàng"

echo ""
echo "✅ PIPELINE ĐÃ KHỞI ĐỘNG!"
echo ""
echo "🌐 Airflow UI:"
echo "   URL: http://localhost:8081"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📝 Lệnh hữu ích:"
echo "   - Xem logs: docker-compose logs airflow-scheduler --tail 50"
echo "   - Check status: docker-compose ps"
echo "   - Dừng: docker-compose down"
echo "   - Restart: docker-compose restart"
echo ""



