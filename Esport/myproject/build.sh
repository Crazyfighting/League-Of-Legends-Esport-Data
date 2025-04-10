#!/bin/bash

# 升級 pip
pip install --upgrade pip

# 安裝依賴
pip install -r requirements.txt

# 收集靜態文件
python manage.py collectstatic --noinput

# 執行數據庫遷移
python manage.py migrate