# FinFlow 财经新闻爬取与智能日报

一键爬取东方财富、新浪财经、财联社的最新财经新闻，通过通义千问AI智能汇总，自动推送到企业微信。

## 功能特性

- ✅ **多源爬取**：东方财富、新浪财经、财联社
- ✅ **智能汇总**：调用通义千问AI生成专业财经日报
- ✅ **自动推送**：推送到企业微信机器人
- ✅ **定时任务**：支持每日自动运行
- ✅ **Web管理**：可视化查看新闻数据

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

编辑 `config.json`：

```json
{
  "dashscope": {
    "api_key": "your-dashscope-api-key",
    "model": "qwen-turbo"
  },
  "wechat": {
    "webhook_url": "your-wechat-webhook-url"
  }
}
```

### 3. 启动Web服务

```bash
python app.py
```

访问 http://127.0.0.1:5000

### 4. 生成并推送日报

```bash
python daily_report.py
```

## 项目结构

```
finflow/
├── app.py              # Flask Web服务
├── spider_api.py       # 爬虫核心
├── daily_report.py     # 日报生成主程序
├── summarizer.py       # 通义千问AI汇总
├── wechat_bot.py       # 企业微信推送
├── templates/          # Web前端模板
├── config.json         # 配置文件
└── requirements.txt    # 依赖清单
```

## 定时任务

### Linux/Mac (crontab)

```bash
# 每天9:00和17:00推送日报
0 9,17 * * * cd /path/to/finflow && python daily_report.py
```

### Windows (计划任务)

设置每天定时运行 `daily_report.py`

## 技术栈

- **后端**：Python + Flask
- **爬虫**：Requests + BeautifulSoup
- **AI**：通义千问 (Qwen)
- **推送**：企业微信机器人

## 许可证

MIT License
