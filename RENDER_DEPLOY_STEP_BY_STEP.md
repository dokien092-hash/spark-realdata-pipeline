# 🎨 Hướng dẫn Deploy lên Render.com - Từng bước chi tiết

## 📋 Tổng quan

Render.com sẽ host:
- **PostgreSQL** (free 90 ngày → $7/tháng sau đó)
- **Airflow Webserver** (Web Service - free, sẽ sleep)
- **Airflow Scheduler** (Background Worker - free, KHÔNG sleep, chạy 24/7)

## ✅ Bước 1: Chuẩn bị code (5 phút)

### 1.1. Push code lên GitHub (nếu chưa có)

```bash
cd /Users/kiendo/Downloads/Cole-mini-projects-develop/spark-mini-projects/spark-realdata-pipeline

# Kiểm tra git status
git status

# Nếu chưa có repo, init:
git init
git add .
git commit -m "Prepare for Render deployment"

# Tạo repo trên GitHub và push:
# 1. Vào https://github.com/new
# 2. Tạo repo: spark-realdata-pipeline
# 3. Chạy lệnh:
git remote add origin https://github.com/your-username/spark-realdata-pipeline.git
git push -u origin main
```

### 1.2. Verify các file đã có:
- ✅ `Dockerfile.render.webserver`
- ✅ `Dockerfile.render.scheduler`
- ✅ `sql/init.sql`
- ✅ `airflow/dags/financial_pipeline_dag.py`
- ✅ `jobs/` folder

---

## ✅ Bước 2: Tạo PostgreSQL Database trên Render (2 phút)

### 2.1. Đăng ký Render
1. Vào https://render.com
2. Click **"Get Started for Free"**
3. Đăng ký bằng **GitHub account** (khuyến nghị)

### 2.2. Tạo PostgreSQL Database
1. Dashboard → Click **"+ New"** → **"PostgreSQL"**
2. Điền thông tin:
   - **Name**: `realdata-postgres`
   - **Database**: `realdata_warehouse`
   - **User**: `postgres` (hoặc để Render tự tạo)
   - **Region**: **Singapore** (gần VN nhất)
   - **PostgreSQL Version**: `15`
   - **Plan**: **Free** (90 ngày) hoặc **Starter** ($7/tháng)
3. Click **"Create Database"**
4. ⚠️ **QUAN TRỌNG**: Copy **Internal Database URL**
   - Format: `postgresql://user:password@host:5432/dbname`
   - Lưu lại, sẽ cần cho các bước sau

### 2.3. Init Database Schema
1. Trên **local machine** (Mac của bạn), chạy:
```bash
cd /Users/kiendo/Downloads/Cole-mini-projects-develop/spark-mini-projects/spark-realdata-pipeline

# Set DATABASE_URL (paste Internal Database URL từ Render)
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Chạy init script
bash scripts/init-render-db.sh
```

Hoặc manual:
```bash
# Install psql nếu chưa có
brew install postgresql

# Connect và chạy init.sql
psql "$DATABASE_URL" -f sql/init.sql
```

---

## ✅ Bước 3: Tạo Airflow Webserver (Web Service) (3 phút)

### 3.1. Tạo Web Service
1. Render Dashboard → **"+ New"** → **"Web Service"**
2. **Connect** GitHub repo: `spark-realdata-pipeline`
3. Điền thông tin:
   - **Name**: `airflow-webserver`
   - **Region**: **Singapore**
   - **Branch**: `main`
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `Dockerfile.render.webserver`
   - **Docker Context**: `.` (root)
   - **Plan**: **Free** (hoặc Starter $7/tháng)
   - **Health Check Path**: `/health` (Airflow có endpoint này)

### 3.2. Environment Variables
Click **"Advanced"** → **"Environment Variables"**, thêm:

```bash
# Airflow Config
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<paste Internal Database URL từ PostgreSQL>
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
AIRFLOW__CORE__LOAD_EXAMPLES=false
AIRFLOW__API__AUTH_BACKENDS=airflow.api.auth.backend.basic_auth

# API Keys
FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
```

**Lưu ý**: Thay `<paste Internal Database URL>` bằng Internal Database URL từ PostgreSQL service.

### 3.3. Deploy
1. Click **"Create Web Service"**
2. Render sẽ tự động build và deploy
3. Đợi ~5-10 phút để build xong
4. Lấy URL: `https://airflow-webserver.onrender.com`

### 3.4. Setup Airflow Admin User
Sau khi deploy xong, cần tạo admin user. Có 2 cách:

**Cách 1: Dùng Render Shell**
1. Vào webserver service → **"Shell"** tab
2. Chạy:
```bash
airflow users create \
  --role Admin \
  --username admin \
  --password admin \
  --email admin@example.com \
  --firstname admin \
  --lastname admin
```

**Cách 2: Thêm vào Dockerfile** (đã có trong entrypoint của docker-compose, nhưng trên Render cần thêm)

---

## ✅ Bước 4: Tạo Airflow Scheduler (Background Worker) (3 phút)

### 4.1. Tạo Background Worker
1. Render Dashboard → **"+ New"** → **"Background Worker"**
2. **Connect** cùng GitHub repo: `spark-realdata-pipeline`
3. Điền thông tin:
   - **Name**: `airflow-scheduler`
   - **Region**: **Singapore**
   - **Branch**: `main`
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `Dockerfile.render.scheduler`
   - **Docker Context**: `.` (root)
   - **Plan**: **Free** (Background Worker không sleep)

### 4.2. Environment Variables
**GIỐNG HỆT** webserver:

```bash
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<same Internal Database URL>
AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
AIRFLOW__CORE__LOAD_EXAMPLES=false
FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
```

### 4.3. Deploy
1. Click **"Create Background Worker"**
2. Đợi build xong (~5-10 phút)

**Lưu ý**: Background Worker sẽ chạy **24/7**, không sleep như Web Service.

---

## ✅ Bước 5: Setup Airflow Admin User

Sau khi cả 2 services đã deploy xong:

1. Vào **airflow-webserver** service → **"Shell"** tab
2. Chạy:
```bash
airflow db init
airflow users create \
  --role Admin \
  --username admin \
  --password admin \
  --email admin@example.com \
  --firstname admin \
  --lastname admin
```

3. Restart webserver service (từ dashboard)

---

## ✅ Bước 6: Verify và Test

### 6.1. Access Airflow UI
1. Mở URL: `https://airflow-webserver.onrender.com`
2. Login: `admin` / `admin`
3. Verify DAG `financial_pipeline_dag` đã xuất hiện

### 6.2. Unpause DAG
1. Trong Airflow UI → **DAGs**
2. Tìm `financial_pipeline_dag`
3. Toggle **OFF** (unpause)

### 6.3. Check Scheduler Logs
1. Vào **airflow-scheduler** service → **"Logs"** tab
2. Xem logs để đảm bảo scheduler đang chạy DAGs

### 6.4. Test Manual Trigger
1. Trong Airflow UI → Click vào DAG `financial_pipeline_dag`
2. Click **"Play"** button → **"Trigger DAG"**
3. Xem logs để verify DAG chạy OK

---

## 🔧 Troubleshooting

### Webserver sleep sau 15 phút
- **Normal behavior**: Free tier web service sẽ sleep
- **Solution**: Scheduler (Background Worker) vẫn chạy 24/7 và execute DAGs
- **Workaround**: Dùng cron job hoặc monitoring service để ping webserver mỗi 10 phút

### Scheduler không chạy DAGs
- Check logs của scheduler service
- Verify `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` đúng
- Check DAG đã unpause chưa

### Database connection failed
- Verify Internal Database URL đúng format
- Check PostgreSQL service đã running
- Test connection từ local: `psql "$DATABASE_URL" -c "SELECT 1;"`

### DAG không xuất hiện
- Check logs của webserver và scheduler
- Verify `airflow/dags/` folder đã copy vào Docker image
- Check DAG file syntax không có lỗi

---

## 💰 Pricing Summary

**Free Tier:**
- ✅ PostgreSQL: Free 90 ngày
- ✅ Web Service: Free (sleep sau 15 phút)
- ✅ Background Worker: Free (không sleep, 24/7)

**After 90 days:**
- PostgreSQL: $7/tháng (Starter plan)
- Web Service: Free (nếu dùng free plan)
- Background Worker: Free

**Total: ~$7/tháng sau 90 ngày**

---

## 📚 Tài liệu tham khảo
- Render Docs: https://render.com/docs
- Docker on Render: https://render.com/docs/docker
- Airflow on Render: https://render.com/docs/airflow (community guides)

---

**✨ Hoàn tất! Pipeline sẽ tự động chạy lúc 7 AM VN (0:00 UTC) từ T2-T6**

