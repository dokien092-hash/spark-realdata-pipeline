#!/bin/bash
# Script kiểm tra, sửa lỗi và tắt Grafana trên EC2

cd ~/spark-realdata-pipeline || exit

echo "📊 Kiểm tra trạng thái containers hiện tại:"
docker-compose ps

echo ""
echo "🔍 Kiểm tra containers đang chạy (bao gồm cả stopped):"
docker ps -a | grep -E "(postgres|airflow|grafana)" || echo "Không thấy containers"

echo ""
echo "🛑 Đang dừng Grafana nếu đang chạy..."
docker-compose stop grafana 2>/dev/null || echo "Grafana không chạy hoặc không tồn tại"

echo "🗑️  Đang xóa Grafana container..."
docker-compose rm -f grafana 2>/dev/null || echo "Không có Grafana container để xóa"

echo ""
echo "🔄 Đang khởi động lại tất cả containers..."
docker-compose down
docker-compose up -d

echo ""
echo "⏳ Chờ 30 giây để containers khởi động..."
sleep 30

echo ""
echo "📊 Trạng thái containers sau khi restart:"
docker-compose ps

echo ""
echo "📋 Logs của airflow-scheduler (10 dòng cuối):"
docker-compose logs --tail=10 airflow-scheduler 2>&1 | tail -10

echo ""
echo "📋 Logs của airflow-webserver (10 dòng cuối):"
docker-compose logs --tail=10 airflow-webserver 2>&1 | tail -10

echo ""
echo "✅ Hoàn thành!"
echo ""
echo "💡 Nếu containers không chạy, xem logs chi tiết:"
echo "   docker-compose logs airflow-scheduler"
echo "   docker-compose logs airflow-webserver"
echo "   docker-compose logs postgres"



