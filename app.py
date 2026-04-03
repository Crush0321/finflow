#!/usr/bin/env python3
"""
Flask Web - 财经新闻热点
"""
import os
import shutil
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from spider_api import crawl_eastmoney, crawl_sina, crawl_cls, save, load_by_date, load_dates
from summarizer import QwenSummarizer
from wechat_bot import WeChatBot

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


@app.route('/api/push', methods=['POST'])
def api_push():
    """生成日报并推送到企业微信"""
    try:
        # 加载今日新闻
        today = datetime.now().strftime('%Y%m%d')
        news_list = load_by_date(today)
        
        if not news_list:
            return jsonify({
                'success': False,
                'error': '今日暂无新闻数据，请先爬取新闻'
            })
        
        # 数据清洗
        cleaned_news = _clean_news(news_list)
        
        # 生成汇总
        summarizer = QwenSummarizer()
        summary = summarizer.summarize(cleaned_news)
        
        # 构建消息
        weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][datetime.now().weekday()]
        title = f"📊 {today} {weekday} 财经日报"
        source_stats = _get_source_stats(cleaned_news)
        header = f"{title}\n\n📈 数据来源：{source_stats}\n"
        full_message = header + "\n" + summary
        
        # 推送到企业微信
        bot = WeChatBot()
        success = bot.send_markdown(full_message)
        
        if success:
            # 保存日报
            _save_report(today, full_message)
            return jsonify({
                'success': True,
                'message': f'推送成功！共汇总 {len(cleaned_news)} 条新闻',
                'summary': summary[:200] + '...' if len(summary) > 200 else summary
            })
        else:
            return jsonify({
                'success': False,
                'error': '推送到企业微信失败，请检查配置'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def _clean_news(news_list):
    """数据清洗"""
    cleaned = []
    seen_titles = set()
    
    for news in news_list:
        title = news.get('title', '').strip()
        if not title or len(title) < 5:
            continue
        
        title_key = title[:15]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        
        content = news.get('content', '').strip()
        content = content.replace('\n\n', '\n').replace('  ', ' ')
        pub_time = news.get('pub_time', '')
        
        cleaned.append({
            'id': news.get('id', ''),
            'title': title,
            'content': content[:500],
            'pub_time': pub_time,
            'source': news.get('source', ''),
            'url': news.get('url', '')
        })
    
    cleaned.sort(key=lambda x: x['pub_time'], reverse=True)
    return cleaned


def _get_source_stats(news_list):
    """获取来源统计"""
    sources = {}
    for news in news_list:
        source = news.get('source', '其他')
        sources[source] = sources.get(source, 0) + 1
    return " | ".join([f"{k}:{v}条" for k, v in sources.items()])


def _save_report(date, content):
    """保存日报"""
    report_dir = 'reports'
    os.makedirs(report_dir, exist_ok=True)
    filepath = os.path.join(report_dir, f'report_{date}.md')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


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
    os.makedirs('reports', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
