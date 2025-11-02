#!/bin/bash
# Script tắt Grafana trên EC2 để tiết kiệm tài nguyên

cd ~/spark-realdata-pipeline || exit

echo "🛑 Đang dừng Grafana container..."
docker-compose stop grafana 2>/dev/null || echo "Grafana đã dừng hoặc không chạy"

echo "🗑️  Đang xóa Grafana container..."
docker-compose rm -f grafana 2>/dev/null || echo "Không có container để xóa"

echo "🔄 Đang reload docker-compose (Grafana đã được comment out)..."
docker-compose up -d

echo "⏳ Chờ 10 giây để containers khởi động..."
sleep 10

echo "📊 Trạng thái containers:"
docker-compose ps

echo ""
echo "✅ Hoàn thành! Grafana đã được tắt."
echo "💾 Tiết kiệm được: ~100-200 MB RAM"
echo ""
echo "📋 Containers đang chạy:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"



