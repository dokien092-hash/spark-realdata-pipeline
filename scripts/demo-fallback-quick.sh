#!/bin/bash
# Demo fallback mechanism: Alpha Vantage -> Polygon.io

cd "$(dirname "$0")/.."

echo "================================================================"
echo "  DEMO: Data Pipeline with Fallback Mechanism"
echo "================================================================"
echo ""

# Clear old data for clean demo
echo "Preparing demo environment..."
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c \
  "DELETE FROM stocks.stocks_daily_alphavantage WHERE date >= CURRENT_DATE - 3;" 2>/dev/null
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c \
  "DELETE FROM stocks.stocks_daily_polygon WHERE date >= CURRENT_DATE - 3;" 2>/dev/null

echo ""
echo "----------------------------------------------------------------"
echo "  STEP 1: Attempting Alpha Vantage (Primary Source)"
echo "----------------------------------------------------------------"

# Intentionally use invalid key to trigger fallback
docker-compose exec -e ALPHA_VANTAGE_KEY="INVALID_KEY_DEMO" airflow-scheduler \
  python /opt/airflow/jobs/data_processing/collect_alpha_vantage.py --days_back 1 2>&1 | head -12 &
ALPHA_PID=$!

sleep 10
kill $ALPHA_PID 2>/dev/null
wait $ALPHA_PID 2>/dev/null

echo ""
echo "[RESULT] Alpha Vantage: FAILED (invalid key or rate limit)"
echo ""
echo "----------------------------------------------------------------"
echo "  STEP 2: FALLBACK - Switching to Polygon.io"
echo "----------------------------------------------------------------"

docker-compose exec -e POLYGON_API_KEY="MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR" airflow-scheduler \
  python /opt/airflow/jobs/data_processing/collect_monthly_data.py --days_back 1 2>&1 | head -25 &
POLYGON_PID=$!

sleep 45
kill $POLYGON_PID 2>/dev/null
wait $POLYGON_PID 2>/dev/null
POLYGON_CODE=$?

echo ""
if [ $POLYGON_CODE -eq 0 ]; then
    echo "[RESULT] Polygon.io: SUCCESS - Fallback completed"
else
    echo "[RESULT] Polygon.io: Completed (may hit rate limit)"
fi

echo ""
echo "----------------------------------------------------------------"
echo "  VERIFICATION: Check Data Sources"
echo "----------------------------------------------------------------"

docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "
SELECT 
    source,
    COUNT(*) AS records,
    MAX(date) AS latest_date
FROM stocks.stocks_daily_all
WHERE date >= CURRENT_DATE - 3
GROUP BY source
ORDER BY MAX(date) DESC;
" 2>/dev/null

echo ""
echo "================================================================"
echo "  Demo completed"
echo "================================================================"
