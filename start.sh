#!/bin/bash
echo "正在启动财经新闻爬取平台..."
echo ""

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

echo ""
echo "启动Web服务..."
echo "请在浏览器中访问: http://127.0.0.1:5000"
echo ""
python app.py
