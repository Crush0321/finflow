@echo off
chcp 65001 >nul
echo 正在启动财经新闻爬取平台...
echo.

REM 设置UTF-8编码
set PYTHONIOENCODING=utf-8

REM 进入虚拟环境
call venv\Scripts\activate

REM 检查flask是否已安装
python -c "import flask" 2>nul
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

echo.
echo 启动Web服务...
echo 请在浏览器中访问: http://127.0.0.1:5000
echo.
python app.py

pause
