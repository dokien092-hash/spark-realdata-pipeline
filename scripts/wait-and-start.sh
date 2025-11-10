#!/bin/bash
# Chờ Docker sẵn sàng và khởi động pipeline

echo "⏳ Đang chờ Docker Desktop khởi động..."
echo "   (Vui lòng mở Docker Desktop nếu chưa mở)"

# Đợi Docker sẵn sàng (tối đa 2 phút)
for i in {1..24}; do
    if docker info > /dev/null 2>&1; then
        echo "✅ Docker đã sẵn sàng!"
        echo ""
        bash scripts/start-local-pipeline.sh
        exit 0
    fi
    echo "   Đang đợi... ($i/24)"
    sleep 5
done

echo "❌ Docker không khởi động được sau 2 phút"
echo "   Vui lòng mở Docker Desktop thủ công và chạy:"
echo "   bash scripts/start-local-pipeline.sh"


