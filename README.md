# 财经新闻热点爬取平台

一键爬取东方财富、新浪财经、财联社的最新财经新闻。

## 项目结构

```
finflow/
├── app.py              # Flask Web服务
├── spider_api.py       # 爬虫核心
├── requirements.txt    # 依赖
├── start.bat          # Windows启动
├── start.sh           # Mac/Linux启动
└── templates/
    └── index.html     # 前端页面
```

## 快速开始

```bash
# Windows
start.bat

# Mac/Linux
./start.sh
```

然后访问 http://127.0.0.1:5000

## 功能

- 一键爬取三大财经网站新闻
- 按日期存储（JSON格式）
- 关键词搜索
- 来源筛选
- 实时进度显示

## 手动运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

## 数据存储

按日期存储在 `data/YYYYMMDD/` 目录：
- `eastmoney_YYYYMMDD.json`
- `sina_YYYYMMDD.json`
- `cls_YYYYMMDD.json`
