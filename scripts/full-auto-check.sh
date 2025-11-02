#!/bin/bash
# Script kiểm tra toàn bộ tự động chạy lúc 7h sáng

EC2_HOST="3.25.91.76"
EC2_USER="ec2-user"
KEY_PATH="$HOME/Downloads/financial-pipeline-key.pem"

echo "🔍 KIỂM TRA TỰ ĐỘNG CHẠY LÚC 7H SÁNG"
echo "=========================================="
echo ""

ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_SCRIPT'
cd ~/spark-realdata-pipeline

echo "✅ 1. Kiểm tra Docker containers đang chạy:"
echo "--------------------------------------------"
docker-compose ps
echo ""

echo "✅ 2. Kiểm tra Auto-start service (systemd):"
echo "--------------------------------------------"
if sudo systemctl is-enabled docker-compose.service 2>/dev/null; then
    echo "✅ Auto-start ENABLED - Containers sẽ tự khởi động khi EC2 reboot"
    sudo systemctl status docker-compose.service --no-pager | head -10
else
    echo "⚠️  Auto-start NOT ENABLED - Cần setup systemd service"
    echo "   Chạy lệnh sau để enable:"
    echo "   sudo systemctl enable docker-compose.service"
fi
echo ""

echo "✅ 3. Kiểm tra Airflow DAG schedule:"
echo "--------------------------------------------"
echo "Đợi 10 giây để scheduler load DAG..."
sleep 10

DAG_INFO=$(docker-compose exec -T airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag || \
    docker exec airflow-webserver airflow dags list 2>/dev/null | grep financial_pipeline_dag)

if [ -n "$DAG_INFO" ]; then
    echo "✅ DAG found:"
    echo "$DAG_INFO"
    echo ""
    
    # Check DAG schedule
    SCHEDULE=$(docker-compose exec -T airflow-webserver airflow dags show financial_pipeline_dag 2>/dev/null | grep -i "schedule" || \
        docker exec airflow-webserver airflow dags show financial_pipeline_dag 2>/dev/null | grep -i "schedule")
    
    if echo "$SCHEDULE" | grep -q "0 0 \* \* 1-5\|0 0 1-5"; then
        echo "✅ Schedule đúng: 0:00 UTC (7:00 AM VN) từ T2-T6"
    else
        echo "⚠️  Schedule: $SCHEDULE"
        echo "   Kiểm tra schedule_interval trong DAG file"
    fi
    
    # Check DAG is unpaused
    IS_PAUSED=$(docker-compose exec -T airflow-webserver airflow dags list-runs -d financial_pipeline_dag --output table 2>/dev/null | grep -i pause || \
        docker exec airflow-webserver airflow dags list-runs -d financial_pipeline_dag --output table 2>/dev/null | grep -i pause)
    
    if echo "$IS_PAUSED" | grep -qi "false\|unpause"; then
        echo "✅ DAG is UNPAUSED (sẽ tự chạy)"
    else
        echo "⚠️  DAG có thể bị PAUSED - cần unpause trong Airflow UI"
    fi
else
    echo "⚠️  DAG chưa load - kiểm tra scheduler logs"
fi
echo ""

echo "✅ 4. Kiểm tra Airflow Scheduler logs:"
echo "--------------------------------------------"
echo "Latest logs (last 20 lines):"
docker-compose logs airflow-scheduler --tail 20 2>/dev/null | tail -20
echo ""

echo "✅ 5. Kiểm tra Database connection:"
echo "--------------------------------------------"
if docker-compose exec -T postgres pg_isready -U postgres 2>/dev/null | grep -q "accepting"; then
    echo "✅ PostgreSQL đang chạy và sẵn sàng"
    
    # Check if Airflow DB is initialized
    DB_EXISTS=$(docker-compose exec -T postgres psql -U postgres -d realdata_warehouse -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='dag' LIMIT 1;" 2>/dev/null || echo "0")
    
    if [ "$DB_EXISTS" = "1" ]; then
        echo "✅ Airflow database đã được init"
    else
        echo "⚠️  Airflow database chưa init - cần chạy: docker exec airflow-scheduler airflow db init"
    fi
else
    echo "⚠️  PostgreSQL không sẵn sàng"
fi
echo ""

echo "✅ 6. Kiểm tra DAG runs gần đây:"
echo "--------------------------------------------"
RECENT_RUNS=$(docker-compose exec -T airflow-webserver airflow dags list-runs -d financial_pipeline_dag --output table 2>/dev/null | head -15 || \
    docker exec airflow-webserver airflow dags list-runs -d financial_pipeline_dag --output table 2>/dev/null | head -15)

if [ -n "$RECENT_RUNS" ]; then
    echo "$RECENT_RUNS"
else
    echo "⚠️  Không có runs nào - DAG có thể chưa được trigger hoặc chưa chạy lần nào"
fi
echo ""

echo "✅ 7. Kiểm tra Environment variables (API keys):"
echo "--------------------------------------------"
if [ -f .env ]; then
    echo "✅ File .env tồn tại"
    if grep -q "FINNHUB_API_KEY" .env && ! grep -q "FINNHUB_API_KEY=$" .env; then
        echo "✅ FINNHUB_API_KEY đã được set"
    else
        echo "⚠️  FINNHUB_API_KEY chưa được set trong .env"
    fi
else
    echo "⚠️  File .env không tồn tại"
fi
echo ""

echo "✅ 8. Tổng kết:"
echo "--------------------------------------------"
echo "📋 Để đảm bảo tự động chạy lúc 7h sáng (không cần mở máy):"
echo ""
echo "✓ Docker containers phải chạy (đã check)"
echo "✓ Auto-start service phải ENABLED (đã check)"
echo "✓ Airflow DAG schedule = '0 0 * * 1-5' (đã check)"
echo "✓ DAG phải UNPAUSED (đã check)"
echo "✓ Database phải sẵn sàng (đã check)"
echo ""
echo "🌐 Truy cập Airflow UI để kiểm tra thêm:"
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
echo "   http://${PUBLIC_IP}:8081"
echo "   Username: admin | Password: admin"
echo ""
echo "⏰ DAG sẽ tự động chạy lúc 0:00 UTC (7:00 AM VN) từ Thứ 2 - Thứ 6"
echo "   Lần chạy tiếp theo: $(date -u -d 'tomorrow 00:00' '+%Y-%m-%d %H:%M UTC' 2>/dev/null || date -u -v+1d -v0H -v0M '+%Y-%m-%d %H:%M UTC' 2>/dev/null || echo 'Tomorrow 00:00 UTC')"

REMOTE_SCRIPT

echo ""
echo "✅ Kiểm tra hoàn tất!"




