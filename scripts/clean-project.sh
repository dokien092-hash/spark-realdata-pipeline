#!/bin/bash
# Clean project script - Dọn dẹp dự án

echo "🧹 Bắt đầu clean dự án..."

# 1. Xóa Python cache
echo "1. Xóa Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo "   ✅ Đã xóa Python cache"

# 2. Xóa logs cũ (> 7 ngày)
echo "2. Xóa logs cũ (> 7 ngày)..."
find airflow/logs -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
find airflow/logs/dag_id=* -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ Đã xóa logs cũ"

# 3. Xóa file tạm và không cần thiết
echo "3. Xóa file tạm..."
rm -rf exam_docx/ 2>/dev/null || true
rm -f .DS_Store 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
echo "   ✅ Đã xóa file tạm"

# 4. Xóa test files
echo "4. Xóa test files..."
find . -type f -name "test_*.py" -not -path "*/venv/*" -not -path "*/env/*" -delete 2>/dev/null || true
echo "   ✅ Đã xóa test files"

# 5. Xóa Dockerfile không dùng
echo "5. Xóa Dockerfile không dùng..."
rm -f Dockerfile.render.* 2>/dev/null || true
echo "   ✅ Đã xóa Dockerfile không dùng"

# 6. Kiểm tra kích thước
echo ""
echo "📊 Kích thước thư mục chính:"
du -sh airflow/logs data/* 2>/dev/null | sort -h | head -5

echo ""
echo "✅ Clean dự án hoàn tất!"

