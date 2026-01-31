#!/bin/sh
set -e

# 确保目标目录存在
mkdir -p /app/data/static /app/data/logs

# 复制前端静态文件到挂载目录（如果源目录存在）
if [ -d "/app/frontend-dist" ] && [ "$(ls -A /app/frontend-dist 2>/dev/null)" ]; then
    echo "Copying frontend assets to mounted volume..."
    cp -r /app/frontend-dist/* /app/data/static/
    echo "Frontend assets copied successfully."
else
    echo "Warning: Frontend dist not found at /app/frontend-dist"
fi

# 启动 Python 应用
exec python -m app.mail_api web
