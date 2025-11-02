#!/bin/bash
# Script troubleshoot SSH connection

EC2_HOST="3.25.91.76"
KEY_PATH="$HOME/Downloads/financial-pipeline-key.pem"

echo "🔍 Troubleshooting SSH connection..."
echo ""

echo "1. Testing connection with verbose mode..."
ssh -v -i "$KEY_PATH" -o ConnectTimeout=5 ec2-user@$EC2_HOST 2>&1 | head -30

echo ""
echo "2. Testing if port 22 is open..."
if nc -z -v -w5 $EC2_HOST 22 2>&1; then
    echo "✅ Port 22 is OPEN"
else
    echo "⚠️  Port 22 might be CLOSED or instance is not running"
fi

echo ""
echo "3. Testing with different timeout..."
ssh -i "$KEY_PATH" -o ConnectTimeout=10 -o ServerAliveInterval=5 ec2-user@$EC2_HOST "echo 'Connection successful!'" 2>&1




