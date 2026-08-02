#!/bin/bash
set -e

echo "Starting MySQL service..."
service mysql start

echo "Configuring MySQL database & importing DW dump..."
mysql -e "CREATE DATABASE IF NOT EXISTS brazilian_ecommerce_dw;" || true
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '';" || true
mysql -e "FLUSH PRIVILEGES;" || true
# The dump creates tables with FK references before their referenced tables exist,
# so import with FOREIGN_KEY_CHECKS disabled. It also contains redundant
# INSERT statements targeting the vw_customer_persona VIEW (which cannot be
# inserted into and whose data is derived anyway) and stale v1.0 INSERTs for
# customer_segment_ml (rebuilt by the segmentation trainer) — strip those blocks.
awk '
  /^INSERT INTO `customer_segment_ml`/{skip=1}
  /^INSERT INTO `vw_customer_persona`/{skip=1}
  skip && /;$/ {skip=0; next}
  skip {next}
  {print}
' /app/SQL/dump_brazilian_ecommerce_dw.sql \
  | mysql --init-command="SET FOREIGN_KEY_CHECKS=0" brazilian_ecommerce_dw

echo "Exporting runtime DB config..."
export DB_TYPE=mysql
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=brazilian_ecommerce_dw
export DB_USER=root
export DB_PASSWORD=''

echo "Starting FastAPI Backend on port 8000..."
cd /app/backend
# Bind to 0.0.0.0 so the API is reachable via the container's published port
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Waiting for FastAPI backend to start..."
sleep 3

echo "Serving Next.js static build on port 7860..."
cd /app/frontend
exec npx serve -s out -l 7860 --no-clipboard
