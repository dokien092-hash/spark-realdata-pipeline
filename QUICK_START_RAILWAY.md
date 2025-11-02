# 🚂 Quick Start - Deploy lên Railway trong 10 phút

## ✅ Yêu cầu:
- GitHub account (miễn phí)
- Code đã push lên GitHub repo

## 📋 Bước 1: Push code lên GitHub (5 phút)

### 1.1. Kiểm tra repo hiện tại
```bash
cd /Users/kiendo/Downloads/Cole-mini-projects-develop/spark-mini-projects/spark-realdata-pipeline
git status
```

### 1.2. Nếu chưa có git repo, tạo mới:
```bash
# Khởi tạo git
git init

# Tạo .gitignore
cat > .gitignore << 'EOF'
airflow/logs/**
*.log
__pycache__/**
.pytest_cache/**
data/**
*.ipynb_checkpoints
.DS_Store
.env
*.pem
EOF

# Add và commit
git add .
git commit -m "Initial commit for Railway deployment"
```

### 1.3. Tạo GitHub repo và push:
1. Vào https://github.com/new
2. Tạo repo mới: `spark-realdata-pipeline`
3. **KHÔNG** check "Initialize with README" (repo đã có code)
4. Copy URL repo (ví dụ: `https://github.com/your-username/spark-realdata-pipeline.git`)

```bash
# Thêm remote và push
git remote add origin https://github.com/your-username/spark-realdata-pipeline.git
git branch -M main
git push -u origin main
```

## 📋 Bước 2: Setup Railway (5 phút)

### 2.1. Tạo tài khoản Railway
1. Vào https://railway.app
2. Click **"Start a New Project"**
3. Chọn **"Login with GitHub"**
4. Authorize Railway access GitHub repos

### 2.2. Deploy từ GitHub
1. Click **"+ New Project"**
2. Chọn **"Deploy from GitHub repo"**
3. Chọn repo `spark-realdata-pipeline`
4. Railway sẽ tự detect `docker-compose.yml` ✅

### 2.3. Add Environment Variables
1. Trong Railway project → **Variables** tab
2. Click **"+ New Variable"**
3. Thêm từng biến:
   ```
   FINNHUB_API_KEY=your_key_here
   POLYGON_API_KEY=your_key_here  
   ALPHA_VANTAGE_KEY=your_key_here
   ```

### 2.4. Railway tự động:
- ✅ Build Docker images
- ✅ Start containers (postgres, airflow-webserver, airflow-scheduler)
- ✅ Generate public URLs

## 📋 Bước 3: Cấu hình Ports (2 phút)

### 3.1. Expose Airflow Webserver
1. Click vào service **"airflow-webserver"**
2. Tab **Settings** → **Networking**
3. Click **"+ Add Public Port"**
4. Port: `8080`
5. Railway tạo URL: `https://airflow-webserver-production.up.railway.app`

### 3.2. Kiểm tra services
- **postgres**: Chạy internal (không cần public port)
- **airflow-scheduler**: Chạy background (không cần port)
- **airflow-webserver**: Có public URL để access UI

## 📋 Bước 4: Verify (3 phút)

### 4.1. Check logs
1. Click vào mỗi service → tab **"Logs"**
2. Xem logs để đảm bảo containers đã start OK

### 4.2. Access Airflow UI
1. Mở URL từ Railway (airflow-webserver)
2. Login: 
   - Username: `admin`
   - Password: `admin`

### 4.3. Unpause DAG
1. Trong Airflow UI → **DAGs**
2. Tìm `financial_pipeline_dag`
3. Toggle **OFF** (unpause) nếu đang pause

## ✅ Xong! Pipeline đã chạy tự động

### Railway tự động:
- ✅ Containers chạy 24/7
- ✅ Auto-restart khi crash
- ✅ Auto-deploy khi push code mới
- ✅ Scheduled DAG chạy đúng giờ (7 AM VN)

## 🎯 Tiếp theo

### Check DAG runs:
- Vào Airflow UI → `financial_pipeline_dag` → **Graph View**
- Xem các runs đã chạy

### Check data:
```bash
# Railway có thể SSH vào container nếu cần
railway shell

# Hoặc dùng Railway CLI để exec commands
railway run psql -U postgres -d realdata_warehouse -c "SELECT COUNT(*) FROM stocks.stocks_daily_all;"
```

## 🚨 Troubleshooting

### Containers không start
- Check logs trong Railway dashboard
- Verify environment variables đã set đúng

### Airflow UI không accessible
- Verify đã expose port 8080
- Check service đã running trong logs

### DAG không chạy
- Check scheduler service logs
- Verify DAG đã unpause trong Airflow UI

## 💰 Pricing

- **Free**: $5 credit/tháng (hết hạn sau 30 ngày)
- **Hobby**: $5/tháng cho $5 credit không hết hạn
- Với pipeline nhỏ, có thể chỉ dùng ~$2-3/tháng → **VẪN FREE**

---

**✨ Tổng thời gian: ~10-15 phút setup, sau đó tự động chạy!**


