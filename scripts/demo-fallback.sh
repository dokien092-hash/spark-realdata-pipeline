#!/bin/bash
# Script demo fallback mechanism: Alpha Vantage → Polygon.io
# Để demo cho giáo viên

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "════════════════════════════════════════════════════════════════"
echo "  🚀 DEMO: Financial Data Pipeline với Fallback Mechanism"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Quy trình:"
echo "  1️⃣  Thử Alpha Vantage (nguồn chính)"
echo "  2️⃣  Nếu Alpha fail → Tự động fallback sang Polygon.io"
echo "  3️⃣  Lưu vào PostgreSQL"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Bước 1: Thử Alpha Vantage
echo "🔵 BƯỚC 1: Thử lấy dữ liệu từ Alpha Vantage..."
echo "─────────────────────────────────────────────────────────────"

ALPHA_EXIT_CODE=0
docker-compose exec -e ALPHA_VANTAGE_KEY="${ALPHA_VANTAGE_KEY:-VWR51RQTVFTSBEL7}" airflow-scheduler \
  python /opt/airflow/jobs/data_processing/collect_alpha_vantage.py --days_back 1 2>&1 | \
  tee /tmp/alpha_output.log || ALPHA_EXIT_CODE=$?

# Kiểm tra kết quả Alpha
ALPHA_RECORDS=$(grep -o "[0-9]* bản ghi" /tmp/alpha_output.log | head -1 | awk '{print $1}')
ALPHA_SUCCESS=false

if [ "$ALPHA_EXIT_CODE" -eq 0 ] && [ ! -z "$ALPHA_RECORDS" ] && [ "$ALPHA_RECORDS" -gt 0 ]; then
    ALPHA_SUCCESS=true
fi

echo ""
echo "─────────────────────────────────────────────────────────────"

if [ "$ALPHA_SUCCESS" = true ]; then
    echo "✅ Alpha Vantage: THÀNH CÔNG"
    echo "   📊 Đã lưu: $ALPHA_RECORDS bản ghi"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  ✅ Hoàn thành! Không cần fallback"
    echo "════════════════════════════════════════════════════════════════"
else
    echo "⚠️  Alpha Vantage: THẤT BẠI hoặc không có dữ liệu mới"
    if [ ! -z "$ALPHA_RECORDS" ]; then
        echo "   📊 Records: $ALPHA_RECORDS"
    fi
    echo ""
    
    # Bước 2: Fallback sang Polygon
    echo "🟢 BƯỚC 2: FALLBACK - Chuyển sang Polygon.io..."
    echo "─────────────────────────────────────────────────────────────"
    
    POLYGON_EXIT_CODE=0
    docker-compose exec -e POLYGON_API_KEY="${POLYGON_API_KEY:-MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR}" airflow-scheduler \
      python /opt/airflow/jobs/data_processing/collect_monthly_data.py --days_back 1 2>&1 | \
      tee /tmp/polygon_output.log || POLYGON_EXIT_CODE=$?
    
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    
    if [ "$POLYGON_EXIT_CODE" -eq 0 ]; then
        POLYGON_RECORDS=$(grep -o "[0-9]* records inserted" /tmp/polygon_output.log | head -1 | awk '{print $1}')
        echo "✅ Polygon.io: THÀNH CÔNG (Fallback)"
        if [ ! -z "$POLYGON_RECORDS" ]; then
            echo "   📊 Đã lưu: $POLYGON_RECORDS bản ghi"
        fi
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo "  ✅ Hoàn thành! Fallback Polygon thành công"
        echo "════════════════════════════════════════════════════════════════"
    else
        echo "❌ Polygon.io: THẤT BẠI"
        echo ""
        echo "════════════════════════════════════════════════════════════════"
        echo "  ❌ CẢ 2 NGUỒN THẤT BẠI (Alpha + Polygon)"
        echo "════════════════════════════════════════════════════════════════"
        exit 1
    fi
fi

# Bước 3: Kiểm tra dữ liệu trong DB
echo ""
echo "📊 BƯỚC 3: Kiểm tra dữ liệu trong PostgreSQL..."
echo "─────────────────────────────────────────────────────────────"

docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "
SELECT 
    source as 'Nguồn dữ liệu',
    COUNT(*) as 'Số bản ghi',
    MAX(date) as 'Ngày mới nhất'
FROM stocks.stocks_daily_all
WHERE date >= CURRENT_DATE - 7
GROUP BY source
ORDER BY MAX(date) DESC;
" 2>/dev/null || echo "⚠️  Không kết nối được database"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  🎉 DEMO HOÀN TẤT"
echo "════════════════════════════════════════════════════════════════"




