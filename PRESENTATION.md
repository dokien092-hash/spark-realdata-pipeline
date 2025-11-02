# Financial Data Pipeline - Giải Thích Dự Án

## 📋 TỔNG QUAN DỰ ÁN

### Mục Tiêu
Thu thập dữ liệu cổ phiếu tự động hàng ngày, lưu trữ vào database, và phân tích/visualize.

### Kết Quả
- **2,396 records** từ **63 stocks** khác nhau
- **66 ngày giao dịch** (3 tháng: Jul - Oct 2025)
- Tự động cập nhật **mỗi sáng 7h**
- Có fallback khi nguồn chính bị lỗi

---

## 🏗️ KIẾN TRÚC TỔNG THỂ

```
┌──────────────────────┐
│   Data Sources       │
│                      │
│ 1. Alpha Vantage ────┼─── 15 stocks, ~15 giây
│ 2. Polygon.io    ────┼─── 30 stocks, ~6 phút (fallback)
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│  Apache Airflow      │  ← Tự động chạy @daily 7h sáng
│  (Scheduler)         │
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│  PostgreSQL          │
│                      │
│ 3 Tables:            │
│ - stocks_daily_polygon       (2,385 records)
│ - stocks_daily_alphavantage  (11 records)
│ - stocks_daily_yahoo         (0 records)
│                      │
│ 1 View:              │
│ - stocks_daily_all   (2,396 records - tự động merge)
└──────────┬───────────┘
           │
           ↓
┌──────────────────────┐
│  Phân Tích           │
│                      │
│ - Jupyter Notebook   │  ← Biểu đồ, analysis
│ - Grafana Dashboard  │  ← Real-time monitoring
│ - SQL Queries        │  ← Truy vấn trực tiếp
└──────────────────────┘
```

---

## 🔄 QUY TRÌNH HOẠT ĐỘNG

### 1. Thu Thập Dữ Liệu (Data Collection)

**Chạy tự động mỗi ngày 7h sáng:**

```
Bước 1: Airflow Scheduler trigger DAG
  ↓
Bước 2: Thử Alpha Vantage API
  ├─ Gọi API lấy 15 stocks (AAPL, GOOGL, MSFT...)
  ├─ Mỗi stock delay 0.5 giây
  ├─ Tổng: ~15 giây
  ├─ Nếu có data → Lưu vào stocks_daily_alphavantage → DONE ✅
  └─ Nếu 0 data (hết quota) → Chuyển Bước 3
  
Bước 3: Fallback - Polygon.io API
  ├─ Gọi API lấy 30 stocks
  ├─ Rate limit: 5 calls/phút (chờ 60s mỗi 5 stocks)
  ├─ Tổng: ~6 phút
  └─ Lưu vào stocks_daily_polygon → DONE ✅

Bước 4: Database Maintenance
  ├─ Xóa dữ liệu cũ hơn 90 ngày
  ├─ Cập nhật thống kê (ANALYZE)
  └─ DONE ✅
```

### 2. Lưu Trữ Dữ Liệu (Data Storage)

**PostgreSQL Database:**

```sql
-- 3 Bảng nguồn (raw data)
stocks_daily_polygon       -- Data từ Polygon.io
stocks_daily_alphavantage  -- Data từ Alpha Vantage (ưu tiên cao)
stocks_daily_yahoo         -- Backup (hiện không dùng)

-- 1 View tổng hợp (auto merge)
stocks_daily_all           -- Tự động loại trùng, ưu tiên Alpha > Polygon
```

**Ví dụ data trùng:**
```
AAPL ngày 17/10:
├─ stocks_daily_alphavantage: $247.45 (created 19/10) ← CHỌN (priority 1)
└─ stocks_daily_polygon: $247.40 (created 17/10)     ← Bỏ qua

→ View stocks_daily_all chỉ hiện 1 record: $247.45 từ Alpha Vantage
```

### 3. Phân Tích & Visualization

**Jupyter Notebook (`stock_analysis.ipynb`):**

```python
# Kết nối database
conn = psycopg2.connect(host="postgres", ...)

# Lấy dữ liệu
df = pd.read_sql("SELECT * FROM stocks_daily_all", conn)

# Vẽ biểu đồ
1. Top 10 stocks tăng/giảm giá
2. Price trends 30 ngày
3. Heatmap daily returns
4. Sector performance
5. Volatility analysis
6. Candlestick chart
7. Correlation matrix
...
```

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

| Công Nghệ | Vai Trò | Lý Do Chọn |
|-----------|---------|------------|
| **Alpha Vantage API** | Data source chính | Ổn định, 25 calls/day miễn phí |
| **Polygon.io API** | Data source dự phòng | 5 calls/phút, không giới hạn ngày |
| **PostgreSQL** | Database | RDBMS phổ biến, view mạnh |
| **Apache Airflow** | Workflow scheduler | Tự động hóa, retry, monitoring |
| **Python** | Data processing | Dễ code, nhiều thư viện |
| **Jupyter** | Analysis | Interactive, visualization |
| **Grafana** | Dashboard | Real-time monitoring |
| **Docker** | Deploy | Đóng gói, dễ chạy |

---

## 💡 ĐIỂM NỔI BẬT

### 1. **Multi-Source với Fallback Thông Minh**
```
Alpha Vantage (chính) → Nếu fail → Polygon.io (dự phòng)
→ Đảm bảo luôn có data mỗi ngày
```

### 2. **Tự Động Loại Trùng**
```sql
-- SQL View với ROW_NUMBER() và PARTITION BY
-- Tự động chọn data tốt nhất khi có trùng
Priority: Alpha Vantage (1) > Polygon (2) > Yahoo (3)
```

### 3. **Xử Lý Cuối Tuần**
```
days_back = 3 (thay vì 1)
→ Lấy 3 ngày để cover weekend
→ Không bỏ sót data thứ 6
```

### 4. **Tối Ưu Tốc Độ**
```
Alpha: 0.5s delay (15 stocks = 15 giây)
Polygon: 5 calls/phút (tự động chờ)
→ Nhanh nhưng tôn trọng API limits
```

### 5. **Production Ready**
```
- Retry logic (2 lần, delay 10 phút)
- Error handling
- Logging đầy đủ
- Data retention (90 ngày)
```

---

## 📊 DỮ LIỆU THU THẬP

### Stocks (63 symbols)

**Tech (14):**
AAPL, GOOGL, MSFT, AMZN, META, NVDA, TSLA, NFLX, AMD, INTC, CRM, ORCL, ADBE, AVGO

**ETFs (7):**
SPY, QQQ, VTI, IWM, DIA, VEA, VWO

**Finance (8):**
JPM, BAC, WFC, GS, V, MA, C, AXP

**Healthcare (6):**
JNJ, UNH, PFE, ABBV, MRK, LLY

**Consumer (7):**
WMT, HD, PG, KO, MCD, NKE, COST

**Others (21):**
Energy, Industrial, Communications...

### Thông Tin Lưu Trữ

**Mỗi record chứa:**
- Symbol, Date
- Open, High, Low, Close (OHLC)
- Volume
- Daily Return (%)
- Source (alpha/polygon/yahoo)

---

## 🎯 WORKFLOW DEMO

### 1. Chạy Pipeline
```bash
docker-compose up -d
# Chờ 60s khởi động
```

### 2. Kiểm Tra Data
```bash
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "
SELECT date, COUNT(*) as symbols 
FROM stocks_daily_all 
ORDER BY date DESC LIMIT 5;
"
```

### 3. Xem Airflow UI
```
http://localhost:8081
Login: admin/admin
→ Xem DAG runs, logs, schedule
```

### 4. Jupyter Analysis
```
http://localhost:8888
→ Mở stock_analysis.ipynb
→ Run cells → Xem biểu đồ
```

---

## 🔧 TÍNH NĂNG KỸ THUẬT

### 1. **Rate Limiting**
```python
# Alpha Vantage: 25 calls/day
time.sleep(0.5)  # Delay nhỏ tránh spam

# Polygon: 5 calls/minute
if calls >= 5:
    wait 60 seconds
```

### 2. **Deduplication Logic**
```sql
-- SQL View với window function
ROW_NUMBER() OVER (
    PARTITION BY symbol, date 
    ORDER BY priority ASC, created_at DESC
) 
WHERE rn = 1  -- Chỉ lấy record tốt nhất
```

### 3. **Caching**
```python
# Local file cache (/tmp/stock_data_cache)
# Tránh fetch lại data đã có
if cache_exists and cache_fresh:
    return cached_data
```

### 4. **Retry Strategy**
```python
# Airflow config
retries = 2
retry_delay = 10 minutes

# Nếu task fail → Retry sau 10 phút
```

---

## 📈 KẾT QUẢ PHÂN TÍCH

### Jupyter Notebook Có:

1. **Top Gainers/Losers** - Bar chart
2. **Price Trends** - Line chart 30 ngày
3. **Heatmap** - Daily returns 14 ngày
4. **Sector Performance** - Bar chart theo ngành
5. **Market Overview** - 2 subplots (return + volume)
6. **Volatility Analysis** - Scatter plot risk vs return
7. **Candlestick** - AAPL OHLC chart
8. **Data Sources** - Pie chart distribution
9. **Correlation Matrix** - Tech stocks correlation
10. **Summary Statistics** - Tổng quan toàn bộ

---

## 🎓 BÀI HỌC RÚT RA

### 1. **API Rate Limiting**
- Hiểu rõ limit của từng API (per second vs per day)
- Strategy khác nhau cho từng nguồn
- Fallback khi primary source fail

### 2. **Data Deduplication**
- Dùng SQL View thay vì manual merge
- Window functions mạnh mẽ
- Priority-based selection

### 3. **Workflow Orchestration**
- Airflow giúp tự động hóa
- Schedule, retry, monitoring tích hợp
- Logs đầy đủ để debug

### 4. **Database Design**
- Tách bảng theo nguồn (normalize)
- View cho query dễ (denormalize)
- Indexes cho performance

### 5. **Docker Deployment**
- Dễ setup (docker-compose up -d)
- Portable (chạy mọi nơi)
- Services tách biệt (microservices mindset)

---

## 🚀 HƯỚNG PHÁT TRIỂN

### Hiện Tại (MVP)
- ✅ Thu thập daily
- ✅ Multi-source
- ✅ Auto dedup
- ✅ Visualization

### Tương Lai
- [ ] Real-time streaming (Kafka)
- [ ] ML price prediction
- [ ] Alert notifications
- [ ] Mobile app
- [ ] Spark cho big data (>10GB)

---

## 📊 SỐ LIỆU DEMO

```
Total Records: 2,396
Unique Symbols: 63
Date Range: 2025-07-17 to 2025-10-17
Sources: Alpha Vantage (11), Polygon (2,385)
Collection Time: 15-20 giây (Alpha) hoặc 6 phút (Polygon fallback)
Database Size: ~1MB
Retention: 90 ngày
```

---

## 🎯 CÂU HỎI THƯỜNG GẶP

**Q: Tại sao dùng nhiều nguồn data?**
A: Redundancy - nếu 1 nguồn fail vẫn có nguồn khác. Alpha Vantage limit 25 calls/day nên cần fallback.

**Q: Làm sao xử lý data trùng?**
A: SQL View tự động loại trùng, ưu tiên nguồn đáng tin hơn (Alpha > Polygon).

**Q: Cuối tuần không có data sao?**
A: Thị trường chứng khoán đóng cửa cuối tuần. Pipeline vẫn chạy nhưng không có data mới.

**Q: Nếu cả 2 nguồn đều fail?**
A: Airflow retry 2 lần, mỗi lần cách 10 phút. Nếu vẫn fail thì báo lỗi.

**Q: Làm sao biết pipeline chạy OK?**
A: Check Airflow UI (http://localhost:8081) hoặc chạy `./scripts/check-pipeline.sh`

---

## 💻 DEMO TRÌNH BÀY

### Phần 1: Kiến Trúc (2 phút)
- Vẽ diagram lên bảng
- Giải thích luồng data: API → Airflow → PostgreSQL → Jupyter

### Phần 2: Code Walkthrough (3 phút)
- Mở `collect_alpha_vantage.py` → Giải thích fetch logic
- Mở `financial_pipeline_dag.py` → Giải thích fallback
- Mở `sql/init.sql` → Giải thích View deduplication

### Phần 3: Demo Chạy (3 phút)
```bash
# 1. Show services đang chạy
docker-compose ps

# 2. Check data trong DB
docker-compose exec postgres psql -U postgres -d realdata_warehouse -c "
SELECT date, COUNT(*) as symbols FROM stocks_daily_all 
ORDER BY date DESC LIMIT 5;
"

# 3. Mở Airflow UI
open http://localhost:8081
→ Show DAG, schedule, logs

# 4. Mở Jupyter
open http://localhost:8888
→ Show notebook với biểu đồ
```

### Phần 4: Q&A (2 phút)

---

## 📝 SLIDE OUTLINE

**Slide 1: Title**
- Financial Data Pipeline
- Automated Stock Data Collection

**Slide 2: Problem**
- Cần thu thập data cổ phiếu hàng ngày
- Manual collection: Mất thời gian, dễ quên
- Single source: Không reliable (rate limit, downtime)

**Slide 3: Solution**
- Automated pipeline với Airflow
- Multi-source với intelligent fallback
- Auto deduplication

**Slide 4: Architecture**
- Diagram: API → Airflow → DB → Analysis
- Components: Alpha Vantage, Polygon, PostgreSQL, Airflow, Jupyter

**Slide 5: Key Features**
- Daily automation (7am)
- Smart fallback (Alpha → Polygon)
- Auto deduplication (SQL View)
- 2,396 records, 63 stocks

**Slide 6: Technical Highlights**
- Rate limiting strategies
- SQL window functions
- Docker deployment
- Error handling & retry

**Slide 7: Demo**
- Screenshot Airflow DAG
- Screenshot Jupyter charts
- Database query results

**Slide 8: Results**
- 3 tháng data collected
- 66 trading days
- 100% uptime với fallback
- Production-ready

**Slide 9: Lessons Learned**
- API rate limiting
- Data deduplication
- Workflow orchestration
- Docker best practices

**Slide 10: Future Work**
- Real-time streaming
- ML predictions
- Alerts
- Mobile app

---

## 🎤 SCRIPT TRÌNH BÀY (5-7 PHÚT)

**Phút 1: Giới thiệu**
"Xin chào thầy cô. Em xin trình bày dự án Financial Data Pipeline - một hệ thống tự động thu thập và phân tích dữ liệu chứng khoán."

**Phút 2: Vấn đề**
"Vấn đề em muốn giải quyết là thu thập dữ liệu cổ phiếu hàng ngày một cách tự động và đáng tin cậy. Thủ công thì tốn thời gian, dễ quên. Dùng 1 nguồn thì hay bị rate limit."

**Phút 3: Giải pháp**
"Em đã xây dựng pipeline với 3 thành phần chính:
1. Multi-source data collection với fallback thông minh
2. PostgreSQL để lưu trữ và tự động loại trùng
3. Airflow để tự động hóa mỗi sáng 7h"

**Phút 4: Kiến trúc**
"Luồng hoạt động: Mỗi sáng 7h, Airflow trigger task thu thập data. Thử Alpha Vantage trước (~15 giây), nếu fail thì fallback Polygon (~6 phút). Data lưu vào PostgreSQL với View tự động merge và loại trùng."

**Phút 5: Demo**
"Bây giờ em demo: [Mở Airflow UI] Đây là DAG đã chạy, có schedule daily. [Mở Jupyter] Đây là notebook phân tích với các biểu đồ. [Query DB] Đây là data đã thu thập."

**Phút 6: Kỹ thuật**
"Về mặt kỹ thuật, em đã implement:
- Rate limiting cho từng API
- SQL window functions để deduplicate
- Docker để deploy
- Retry logic khi lỗi"

**Phút 7: Kết luận**
"Kết quả: 2,396 records từ 63 stocks, 3 tháng data, chạy ổn định. Em đã học được về API integration, workflow orchestration, và database design. Cảm ơn thầy cô đã lắng nghe."

---

## 📸 SCREENSHOTS NÊN CHUẨN BỊ

1. Airflow DAG graph view
2. Airflow task logs (success run)
3. PostgreSQL query results
4. Jupyter notebook với biểu đồ đẹp
5. Grafana dashboard (nếu có)
6. Architecture diagram

---

**Chúc bạn trình bày tốt! 🎓**





