# ☁️ Deploy Pipeline lên Oracle Cloud Always Free

Oracle Cloud có **2 VMs miễn phí VĨNH VIỄN** (không giới hạn thời gian như AWS).

## ✅ Ưu điểm:
- **Free VĨNH VIỄN** - 2 VMs (ARM hoặc x86)
- **Không giới hạn thời gian** (khác AWS chỉ 12 tháng)
- **24GB RAM total** (đủ cho pipeline)
- **Full control** như AWS EC2

## ⚠️ Lưu ý:
- Cần credit card để verify (không charge)
- ARM-based VMs (Ampere) free, x86 có thể charge
- Setup phức tạp hơn Railway/Render

## 📋 Bước 1: Tạo Oracle Cloud Account

### 1.1. Đăng ký
1. Vào https://www.oracle.com/cloud/free/
2. Click **"Start for Free"**
3. Điền thông tin (cần credit card để verify, KHÔNG charge)
4. Verify email và phone

### 1.2. Tạo Compartment
1. Vào **Identity & Security** → **Compartments**
2. Click **"Create Compartment"**
3. Name: `spark-pipeline`
4. Click **"Create"**

## 📋 Bước 2: Tạo VMs (Always Free)

### 2.1. Tạo Instance
1. Vào **Compute** → **Instances**
2. Click **"Create Instance"**
3. **Name**: `pipeline-vm-1`
4. **Image**: **Canonical Ubuntu 22.04** (hoặc Oracle Linux)
5. **Shape**: Chọn **VM.Standard.A1.Flex** (ARM - Always Free)
   - **OCPUs**: 2 (free limit)
   - **Memory**: 12 GB (free limit)
6. **Networking**: 
   - Create new VCN hoặc use default
   - ✅ Assign public IPv4 address
7. **SSH Keys**: 
   - Upload public key hoặc generate mới
8. Click **"Create"**

### 2.2. Setup Security List (Firewall)
1. Vào **Networking** → **Virtual Cloud Networks**
2. Click vào VCN của instance
3. **Security Lists** → **Default Security List** → **Ingress Rules**
4. Thêm rules:
   - **Port 22** (SSH): `0.0.0.0/0`
   - **Port 8081** (Airflow): `0.0.0.0/0`
   - **Port 5432** (PostgreSQL - chỉ internal): `10.0.0.0/16`

## 📋 Bước 3: Setup trên VM

### 3.1. SSH vào VM
```bash
ssh ubuntu@<PUBLIC_IP>
```

### 3.2. Update system
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.3. Install Docker & Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

### 3.4. Clone project
```bash
# Install git
sudo apt install git -y

# Clone repo (nếu có GitHub repo)
git clone https://github.com/your-username/spark-realdata-pipeline.git
cd spark-realdata-pipeline

# HOẶC upload code bằng SCP (từ máy local)
# scp -i ~/.ssh/oracle-key -r . ubuntu@<PUBLIC_IP>:~/spark-realdata-pipeline
```

### 3.5. Tạo `.env` file
```bash
cat > .env << EOF
FINNHUB_API_KEY=your_key_here
POLYGON_API_KEY=your_key_here
ALPHA_VANTAGE_KEY=your_key_here
EOF
```

### 3.6. Start Docker Compose
```bash
docker compose up -d
```

### 3.7. Setup auto-start
```bash
# Tạo systemd service
sudo tee /etc/systemd/system/docker-compose.service > /dev/null << 'EOF'
[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/spark-realdata-pipeline
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=ubuntu
Group=docker

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable docker-compose.service
sudo systemctl start docker-compose.service
```

### 3.8. Verify
```bash
docker compose ps
docker compose logs airflow-scheduler | tail -50
```

## 📋 Bước 4: Access Services

### Airflow UI
- URL: `http://<PUBLIC_IP>:8081`
- Username: `admin`
- Password: `admin`

### PostgreSQL
- Chỉ accessible từ trong VM (security best practice)
- Nếu cần remote access, setup SSH tunnel:
```bash
ssh -L 5432:localhost:5432 ubuntu@<PUBLIC_IP>
```

## 💰 Pricing

**Always Free Tier:**
- ✅ 2 VMs (ARM): 2 OCPUs, 12GB RAM mỗi VM
- ✅ 200GB block storage
- ✅ 10TB egress/month
- ✅ **KHÔNG GIỚI HẠN THỜI GIAN**

**Total Cost: $0/tháng VĨNH VIỄN**

## 🚨 Troubleshooting

### Cannot create VM (out of capacity)
- Oracle Cloud free tier có giới hạn theo region
- Thử region khác: Singapore, Tokyo, Seoul

### SSH connection failed
- Check Security List rules (port 22)
- Verify public IP đã assign
- Check SSH key đúng

### Docker không start
- Check user đã trong docker group: `groups`
- Restart: `sudo systemctl restart docker`

### Out of disk space
- Check: `df -h`
- Clean Docker: `docker system prune -a -f`

## 📚 Tài liệu tham khảo
- Oracle Cloud Free Tier: https://www.oracle.com/cloud/free/
- Always Free Resources: https://www.oracle.com/cloud/free/always-free/


