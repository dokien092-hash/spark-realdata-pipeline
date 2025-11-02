#!/bin/bash
# Script để init database schema trên Render PostgreSQL
# Chạy script này một lần sau khi tạo PostgreSQL service

# Usage: 
# export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
# bash scripts/init-render-db.sh

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable chưa được set"
    echo "Lấy DATABASE_URL từ Render dashboard → PostgreSQL service → Internal Database URL"
    exit 1
fi

echo "🔧 Initializing database schema..."
echo "Database: $DATABASE_URL"

# Install psql nếu chưa có (trên local machine)
if ! command -v psql &> /dev/null; then
    echo "⚠️  psql chưa được cài. Cài đặt:"
    echo "   macOS: brew install postgresql"
    echo "   Linux: sudo apt install postgresql-client"
    exit 1
fi

# Run init.sql
psql "$DATABASE_URL" -f sql/init.sql

if [ $? -eq 0 ]; then
    echo "✅ Database schema đã được init thành công!"
else
    echo "❌ Error khi init database schema"
    exit 1
fi

