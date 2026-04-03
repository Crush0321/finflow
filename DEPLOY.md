# 每日财经日报部署指南

## 配置文件

1. 复制 `config.json` 并修改配置：

```json
{
  "dashscope": {
    "api_key": "sk-xxxxxxxxxxxxxxxx",  // 通义千问API Key
    "model": "qwen-turbo",
    "base_url": "https://dashscope.aliyuncs.com/api/v1"
  },
  "wechat": {
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx"  // 企业微信机器人Webhook
  }
}
```

## 获取API Key

### 通义千问API Key
1. 访问 https://dashscope.aliyun.com/
2. 注册/登录阿里云账号
3. 创建API Key
4. 复制到 config.json

### 企业微信机器人
1. 在企业微信群中添加机器人
2. 复制Webhook地址
3. 粘贴到 config.json

## 运行日报

### 手动运行
```bash
python daily_report.py
```

### 测试（不推送）
```bash
python test_report.py
```

## 设置定时任务

### Linux/Mac (crontab)
```bash
# 编辑crontab
crontab -e

# 每天9:00和17:00推送日报
0 9,17 * * * cd /opt/finflow && /opt/finflow/venv/bin/python daily_report.py >> /var/log/finflow.log 2>&1
```

### Windows (计划任务)
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天 9:00 和 17:00
4. 操作：启动程序
   - 程序：`C:\path\to\finflow\venv\Scripts\python.exe`
   - 参数：`daily_report.py`
   - 起始于：`C:\path\to\finflow`

## 目录结构

```
finflow/
├── config.json          # 配置文件（需修改）
├── daily_report.py      # 日报主程序
├── summarizer.py        # 通义千问汇总模块
├── wechat_bot.py        # 企业微信推送模块
├── spider_api.py        # 爬虫核心
├── test_report.py       # 测试脚本
├── reports/             # 生成的日报保存目录
└── data/                # 爬取的数据
```

## 日志

日报生成日志会保存在 `reports/` 目录，格式：`report_YYYY-MM-DD.md`
