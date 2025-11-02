# 🚂 Deploy Pipeline lên Railway.app

Railway là cách **DỄ NHẤT** để deploy Docker Compose pipeline, không cần setup SSH hay config phức tạp.

## ✅ Ưu điểm:
- **Miễn phí $5 credit/tháng** (đủ cho pipeline nhỏ)
- **Không cần SSH** - deploy từ GitHub
- **Auto-deploy** khi push code
- **Built-in PostgreSQL** (hoặc dùng Docker Compose)
- **Dễ setup** - chỉ cần connect GitHub repo

## 📋 Bước 1: Chuẩn bị

### 1.1. Tạo file `.railwayignore`
```bash
# Bỏ qua các file không cần thiết
airflow/logs/**
*.log
__pycache__/**
.pytest_cache/**
data/**
*.ipynb_checkpoints
.DS_Store
```

### 1.2. Tạo `railway.json` (optional - config cho Railway)
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.railway"
  },
  "deploy": {
    "startCommand": "docker-compose up",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 1.3. Tạo `Dockerfile.railway` (nếu dùng Railway's build system)
```dockerfile
FROM docker/compose:latest

WORKDIR /app

COPY docker-compose.yml .
COPY . .

CMD ["docker-compose", "up"]
```

**HOẶC** đơn giản hơn: Railway sẽ tự detect `docker-compose.yml`

## 📋 Bước 2: Deploy lên Railway

### 2.1. Tạo tài khoản Railway
1. Vào https://railway.app
2. Đăng ký bằng **GitHub account** (khuyến nghị)
3. Verify email

### 2.2. Tạo Project mới
1. Click **"New Project"**
2. Chọn **"Deploy from GitHub repo"**
3. Chọn repo `spark-realdata-pipeline`
4. Railway sẽ tự detect `docker-compose.yml`

### 2.3. Setup Environment Variables
Trong Railway dashboard → **Variables** tab, thêm:

```
FINNHUB_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here
ALPHA_VANTAGE_KEY=your_key_here
```

### 2.4. Setup PostgreSQL (optional)
Railway có managed PostgreSQL, nhưng có thể dùng Docker Compose như hiện tại.

**Nếu dùng Railway PostgreSQL:**
1. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway sẽ tự tạo connection string
3. Update `docker-compose.yml` để dùng Railway DB:

```yaml
environment:
  - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=${{Postgres.PGDATABASE_URL}}
```

### 2.5. Deploy
Railway sẽ tự:
- Build Docker images
- Start containers
- Expose ports (tự động generate public URLs)

## 📋 Bước 3: Cấu hình Ports & Domains

1. Trong Railway dashboard → mỗi service (postgres, airflow-webserver) → **Settings** → **Networking**
2. Thêm **Public Port**:
   - **airflow-webserver**: Port `8080` (Railway map sang public URL)
3. Railway sẽ tạo URL dạng: `https://airflow-webserver-production.up.railway.app`

## 📋 Bước 4: Verify

### Check logs trong Railway dashboard
- Mỗi service có tab **"Logs"** để xem real-time logs

### SSH vào container (nếu cần)
```bash
railway shell
# Hoặc
railway run bash
```

### Check Airflow UI
- Mở URL từ Railway dashboard
- Login: `admin` / `admin`

## 📋 Bước 5: Setup Auto-start (Railway tự động làm)

Railway tự động:
- ✅ Restart containers khi crash
- ✅ Auto-deploy khi push code
- ✅ Keep services running 24/7

## 💰 Pricing

**Free Tier:**
- $5 credit/tháng (hết hạn sau 30 ngày)
- Đủ cho:
  - PostgreSQL small instance
  - Airflow containers
  - ~500MB RAM usage

**Paid:** $5/tháng cho $5 credit không hết hạn

## 🚨 Troubleshooting

### Containers không start
- Check logs trong Railway dashboard
- Verify environment variables đã set đúng

### Airflow không connect DB
- Nếu dùng Railway PostgreSQL, update connection string
- Nếu dùng Docker Compose PostgreSQL, verify network config

### Port không accessible
- Check **Networking** settings trong Railway
- Verify service đã expose port đúng

## 📚 Tài liệu tham khảo
- Railway Docs: https://docs.railway.app
- Docker Compose on Railway: https://docs.railway.app/deploy/docker-compose


