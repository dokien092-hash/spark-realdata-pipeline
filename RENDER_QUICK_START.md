# 🚀 Render.com Quick Start - Deploy trong 15 phút

## ⚡ Checklist nhanh

### ✅ Bước 1: Push code lên GitHub (2 phút)
```bash
cd /Users/kiendo/Downloads/Cole-mini-projects-develop/spark-mini-projects/spark-realdata-pipeline
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### ✅ Bước 2: Tạo PostgreSQL trên Render (3 phút)
1. Vào https://render.com → Login
2. **"+ New"** → **"PostgreSQL"**
3. Name: `realdata-postgres`
4. Region: **Singapore**
5. Plan: **Free** (90 ngày) hoặc **Starter** ($7/tháng)
6. Click **"Create"**
7. ⚠️ **Copy Internal Database URL** (lưu lại!)

### ✅ Bước 3: Init Database Schema (2 phút)
Trên Mac terminal:
```bash
# Install psql nếu chưa có
brew install postgresql

# Set DATABASE_URL (paste từ Render)
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Run init
psql "$DATABASE_URL" -f sql/init.sql
```

### ✅ Bước 4: Tạo Airflow Webserver (3 phút)
1. Render Dashboard → **"+ New"** → **"Web Service"**
2. Connect GitHub repo: `spark-realdata-pipeline`
3. Settings:
   - Name: `airflow-webserver`
   - Runtime: **Docker**
   - Dockerfile Path: `Dockerfile.render.webserver`
   - Plan: **Free**
4. **Environment Variables**:
   ```
   AIRFLOW__CORE__EXECUTOR=LocalExecutor
   AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<paste Internal Database URL>
   AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
   AIRFLOW__CORE__LOAD_EXAMPLES=false
   FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
   POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
   ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
   ```
5. Click **"Create Web Service"**
6. Đợi build (~5-10 phút)

### ✅ Bước 5: Tạo Airflow Scheduler (3 phút)
1. Render Dashboard → **"+ New"** → **"Background Worker"**
2. Connect cùng GitHub repo
3. Settings:
   - Name: `airflow-scheduler`
   - Runtime: **Docker**
   - Dockerfile Path: `Dockerfile.render.scheduler`
   - Plan: **Free**
4. **Environment Variables** (GIỐNG webserver):
   ```
   AIRFLOW__CORE__EXECUTOR=LocalExecutor
   AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<same Internal Database URL>
   AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=false
   AIRFLOW__CORE__LOAD_EXAMPLES=false
   FINNHUB_API_KEY=d412e99r01qr2l0c96sgd412e99r01qr2l0c96t0
   POLYGON_API_KEY=MKtaIeJgaIVQCxwr_HskC4NhLndLPZXR
   ALPHA_VANTAGE_KEY=VWR51RQTVFTSBEL7
   ```
5. Click **"Create Background Worker"**
6. Đợi build (~5-10 phút)

### ✅ Bước 6: Verify (2 phút)
1. Vào Airflow UI: `https://airflow-webserver.onrender.com`
2. Login: `admin` / `admin`
3. Unpause DAG: `financial_pipeline_dag`
4. Check logs của scheduler service

---

## 🎯 Kết quả

✅ Pipeline chạy tự động **lúc 7 AM VN** (0:00 UTC) từ T2-T6
✅ Scheduler chạy **24/7** (không sleep)
✅ Webserver có thể sleep nhưng scheduler vẫn execute DAGs

---

## 📚 Chi tiết đầy đủ

Xem file: **`RENDER_DEPLOY_STEP_BY_STEP.md`**

---

## 💰 Cost

- **90 ngày đầu**: $0 (hoàn toàn free)
- **Sau 90 ngày**: ~$7/tháng (chỉ PostgreSQL, services khác vẫn free)

