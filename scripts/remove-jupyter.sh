#!/bin/bash
# Script xóa Jupyter service khỏi docker-compose.yml để tiết kiệm dung lượng

cd ~/spark-realdata-pipeline || exit 1

# Backup
cp docker-compose.yml docker-compose.yml.backup

# Xóa section Jupyter bằng sed
# Tìm từ dòng "# Jupyter" đến hết service definition của nó
sed -i '/# ============================================{$/,/data-network$/ {
    /# Jupyter/,/data-network$/d
}' docker-compose.yml

# Hoặc cách đơn giản hơn: comment out toàn bộ section
sed -i '/^  # ============================================$/,/^    networks:.*data-network$/ {
    s/^/##REMOVE_JUPYTER##/
}' docker-compose.yml

sed -i '/##REMOVE_JUPYTER##/d' docker-compose.yml

echo "✅ Đã xóa Jupyter service khỏi docker-compose.yml"
echo "📝 Backup tại: docker-compose.yml.backup"






