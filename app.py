#!/usr/bin/env python3
"""
Flask Web - 财经新闻热点
"""
import os
import shutil
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from spider_api import crawl_eastmoney, crawl_sina, crawl_cls, save, load_by_date, load_dates

app = Flask(__name__)

# 爬虫配置
CRAWLERS = {
    'eastmoney': ('东方财富', crawl_eastmoney),
    'sina': ('新浪财经', crawl_sina),
    'cls': ('财联社', crawl_cls)
}


@app.route('/')
def index():
    dates = load_dates()
    today = datetime.now().strftime('%Y%m%d')
    if today not in dates:
        dates.insert(0, today)
    return render_template('index.html', dates=dates, today=today)


@app.route('/api/crawl', methods=['POST'])
def api_crawl():
    """同步爬取，完成后返回结果"""
    source = request.json.get('source', 'all')
    targets = list(CRAWLERS.keys()) if source == 'all' else [source]
    
    # 删除当天的旧数据
    today = datetime.now().strftime('%Y%m%d')
    data_dir = os.path.join('data', today)
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    
    results = {}
    total = 0
    
    try:
        for key in targets:
            if key not in CRAWLERS:
                continue
            name, func = CRAWLERS[key]
            news = func()
            if news:
                _, count = save(news, key)
                results[name] = count
                total += count
        
        return jsonify({
            'success': True,
            'total': total,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/news')
def api_news():
    """获取新闻列表"""
    date = request.args.get('date', datetime.now().strftime('%Y%m%d'))
    source = request.args.get('source', 'all')
    keyword = request.args.get('keyword', '').lower()
    
    news = load_by_date(date)
    
    if source != 'all' and source in CRAWLERS:
        news = [n for n in news if n.get('source') == CRAWLERS[source][0]]
    
    if keyword:
        news = [n for n in news if keyword in n.get('title', '').lower() 
                or keyword in n.get('content', '').lower()]
    
    return jsonify({'total': len(news), 'news': news})


@app.route('/api/dates')
def api_dates():
    """获取所有日期"""
    dates = load_dates()
    today = datetime.now().strftime('%Y%m%d')
    if today not in dates:
        dates.insert(0, today)
    return jsonify(dates)


@app.route('/api/news/<news_id>')
def api_detail(news_id):
    """获取单条新闻详情"""
    news = load_by_date(request.args.get('date'))
    for n in news:
        if n.get('id') == news_id:
            return jsonify(n)
    return jsonify({'error': 'Not found'}), 404


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
