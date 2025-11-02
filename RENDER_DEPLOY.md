# 🎨 Deploy Pipeline lên Render.com

Render.com là alternative tốt với **free tier** cho PostgreSQL và web services.

## ✅ Ưu điểm:
- **Free PostgreSQL** (90 ngày, sau đó $7/tháng)
- **Free Web Service** (auto-sleep sau 15 phút không dùng)
- **Docker support** đầy đủ
- **Auto-deploy** từ GitHub
- **Dễ setup**

## ⚠️ Lưu ý:
- Web service sẽ **sleep** sau 15 phút không có traffic
- Cần **wake-up service** trước khi chạy scheduled tasks
- Hoặc dùng **Cron Jobs** của Render (free tier)

## 📋 Bước 1: Chuẩn bị

### 1.1. Tạo `render.yaml`
```yaml
services:
  - type: web
    name: airflow-webserver
    runtime: docker
    dockerfilePath: ./Dockerfile.render
    dockerContext: .
    plan: free
    envVars:
      - key: AIRFLOW__CORE__EXECUTOR
        value: LocalExecutor
      - key: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        sync: false  # Sẽ set sau khi tạo PostgreSQL
      - key: FINNHUB_API_KEY
        sync: false
      - key: POLYGON_API_KEY
        sync: false
      - key: ALPHA_VANTAGE_KEY
        sync: false

  - type: pg
    name: realdata-postgres
    plan: free  # Free 90 ngày, sau đó $7/tháng
    databaseName: realdata_warehouse
    user: postgres

  - type: worker
    name: airflow-scheduler
    runtime: docker
    dockerfilePath: ./Dockerfile.render-scheduler
    plan: free
    envVars:
      - key: AIRFLOW__CORE__EXECUTOR
        value: LocalExecutor
      - key: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN
        fromDatabase:
          name: realdata-postgres
          property: connectionString
```

### 1.2. Tạo `Dockerfile.render` (cho webserver)
```dockerfile
FROM apache/airflow:2.7.1

USER root
RUN apt-get update && apt-get install -y docker.io docker-compose

USER airflow
RUN pip install --no-cache-dir yfinance==0.2.28 multitasking==0.0.10 pandas==2.0.3 numpy==1.24.4 requests psycopg2-binary

WORKDIR /opt/airflow

COPY airflow/dags ./dags
COPY jobs ./jobs

CMD ["airflow", "webserver"]
```

### 1.3. Tạo `Dockerfile.render-scheduler` (cho scheduler)
```dockerfile
FROM apache/airflow:2.7.1

USER airflow
RUN pip install --no-cache-dir yfinance==0.2.28 multitasking==0.0.10 pandas==2.0.3 numpy==1.24.4 requests psycopg2-binary

WORKDIR /opt/airflow

COPY airflow/dags ./dags
COPY jobs ./jobs

CMD ["airflow", "scheduler"]
```

**HOẶC đơn giản hơn:** Dùng Docker Compose nhưng Render không hỗ trợ trực tiếp, cần tách thành 2 services riêng.

## 📋 Bước 2: Deploy lên Render

### 2.1. Tạo tài khoản
1. Vào https://render.com
2. Đăng ký bằng GitHub
3. Verify email

### 2.2. Tạo PostgreSQL Database
1. Dashboard → **"+ New"** → **"PostgreSQL"**
2. Name: `realdata-postgres`
3. Plan: **Free** (hoặc Starter $7/tháng)
4. Region: Singapore (gần VN nhất)
5. Click **"Create Database"**
6. Copy **Internal Database URL** (dạng: `postgresql://user:pass@host:5432/dbname`)

### 2.3. Tạo Web Service (Airflow Webserver)
1. Dashboard → **"+ New"** → **"Web Service"**
2. Connect GitHub repo
3. Settings:
   - **Name**: `airflow-webserver`
   - **Runtime**: Docker
   - **Dockerfile Path**: `Dockerfile.render`
   - **Plan**: Free
4. **Environment Variables**:
   ```
   AIRFLOW__CORE__EXECUTOR=LocalExecutor
   AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<paste PostgreSQL connection string>
   AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
   FINNHUB_API_KEY=your_key
   POLYGON_API_KEY=your_key
   ALPHA_VANTAGE_KEY=your_key
   ```
5. Click **"Create Web Service"**

### 2.4. Tạo Background Worker (Airflow Scheduler)
1. Dashboard → **"+ New"** → **"Background Worker"**
2. Connect same GitHub repo
3. Settings:
   - **Name**: `airflow-scheduler`
   - **Runtime**: Docker
   - **Dockerfile Path**: `Dockerfile.render-scheduler`
   - **Plan**: Free
4. **Environment Variables** (giống webserver):
   ```
   AIRFLOW__CORE__EXECUTOR=LocalExecutor
   AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<same PostgreSQL connection string>
   AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
   FINNHUB_API_KEY=your_key
   POLYGON_API_KEY=your_key
   ALPHA_VANTAGE_KEY=your_key
   ```
5. Click **"Create Background Worker"**

### 2.5. Setup Auto-deploy
- Render tự động deploy khi push code lên GitHub
- Hoặc manual deploy từ dashboard

## 📋 Bước 3: Setup Cron Job (cho scheduled tasks)

Vì free tier web service sẽ sleep, cần dùng **Cron Jobs**:

1. Dashboard → **"+ New"** → **"Cron Job"**
2. Settings:
   - **Name**: `daily-stock-collection`
   - **Schedule**: `0 0 * * 1-5` (7 AM VN = 0:00 UTC, Mon-Fri)
   - **Command**: 
     ```bash
     docker run --rm \
       -e AIRFLOW__DATABASE__SQL_ALCHEMY_CONN="$AIRFLOW__DATABASE__SQL_ALCHEMY_CONN" \
       -e FINNHUB_API_KEY="$FINNHUB_API_KEY" \
       apache/airflow:2.7.1 \
       python /opt/airflow/jobs/data_processing/collect_finnhub.py --days_back 1
     ```

**HOẶC** đơn giản hơn: Dùng **Background Worker** chạy scheduler 24/7 (không sleep như web service).

## 📋 Bước 4: Verify

### Check logs
- Mỗi service có tab **"Logs"**
- Real-time logs và history

### Check Airflow UI
- Web service URL: `https://airflow-webserver.onrender.com`
- Login: `admin` / `admin` (cần setup user trước)

## 💰 Pricing

**Free Tier:**
- ✅ PostgreSQL: Free 90 ngày → $7/tháng
- ✅ Web Service: Free (sleep sau 15 phút)
- ✅ Background Worker: Free (không sleep)
- ✅ Cron Jobs: Free

**Total:** ~$7/tháng sau 90 ngày (nếu dùng PostgreSQL)

## 🚨 Troubleshooting

### Service sleep (web service)
- Background Worker không sleep
- Hoặc dùng Cron Job thay vì scheduled DAG

### Database connection failed
- Verify connection string đúng format
- Check PostgreSQL đã running

### DAG không chạy
- Verify scheduler (Background Worker) đã start
- Check logs của scheduler service

## 📚 Tài liệu tham khảo
- Render Docs: https://render.com/docs
- Docker on Render: https://render.com/docs/docker


