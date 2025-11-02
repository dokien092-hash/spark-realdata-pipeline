#!/bin/bash
# Script upload docker-compose.yml lên EC2

EC2_HOST="3.25.91.76"
EC2_USER="ec2-user"
KEY_PATH="$HOME/Downloads/financial-pipeline-key.pem"

echo "📤 Uploading docker-compose.yml to EC2..."

scp -i "$KEY_PATH" \
    docker-compose.yml \
    "$EC2_USER@$EC2_HOST:~/spark-realdata-pipeline/"

echo "✅ Upload completed!"
echo ""
echo "📝 Trên EC2, chạy các lệnh sau để tắt Grafana:"
echo "   cd ~/spark-realdata-pipeline"
echo "   docker-compose stop grafana"
echo "   docker-compose rm -f grafana"
echo "   docker-compose up -d"
echo "   docker-compose ps"



