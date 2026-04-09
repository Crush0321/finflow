#!/usr/bin/env python3
"""
Flask Web - 财经新闻热点
"""
import os
import shutil
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from spider_api import (crawl_eastmoney, crawl_sina, crawl_cls, 
                        crawl_36kr, crawl_jiemian, crawl_huxiu,
                        save, load_by_date, load_dates)
from summarizer import QwenSummarizer
from wechat_bot import WeChatBot

app = Flask(__name__)

# 爬虫配置
CRAWLERS = {
    'eastmoney': ('东方财富', crawl_eastmoney),
    'sina': ('新浪财经', crawl_sina),
    'cls': ('财联社', crawl_cls),
    '36kr': ('36氪', crawl_36kr),
    'jiemian': ('界面新闻', crawl_jiemian),

}

# 消费趋势爬虫配置（银发+单身经济）
TRENDING_CRAWLERS = {
    '36kr': ('36氪', crawl_36kr),
    'jiemian': ('界面新闻', crawl_jiemian),
    'huxiu': ('虎嗅', crawl_huxiu),
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
    
    # 删除当天的旧数据（只删除本次要爬取的源）
    today = datetime.now().strftime('%Y%m%d')
    data_dir = os.path.join('data', today)
    if os.path.exists(data_dir):
        for key in targets:
            filepath = os.path.join(data_dir, f'{key}_{today}.json')
            if os.path.exists(filepath):
                os.remove(filepath)
    
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


@app.route('/api/crawl/trending', methods=['POST'])
def api_crawl_trending():
    """爬取消费趋势源（银发+单身经济）"""
    
    # 删除当天的旧数据
    today = datetime.now().strftime('%Y%m%d')
    data_dir = os.path.join('data', today)
    if os.path.exists(data_dir):
        # 删除消费趋势相关文件
        for key in TRENDING_CRAWLERS.keys():
            filepath = os.path.join(data_dir, f'{key}_{today}.json')
            if os.path.exists(filepath):
                os.remove(filepath)
    
    results = {}
    total = 0
    
    try:
        for key, (name, func) in TRENDING_CRAWLERS.items():
            news = func()
            if news:
                _, count = save(news, key)
                results[name] = count
                total += count
        
        return jsonify({
            'success': True,
            'total': total,
            'results': results,
            'message': '消费趋势源抓取完成'
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


@app.route('/api/push/trending', methods=['POST'])
def api_push_trending():
    """生成消费趋势日报并推送（银发+单身经济）"""
    try:
        # 加载今日新闻
        today = datetime.now().strftime('%Y%m%d')
        news_list = load_by_date(today)
        
        if not news_list:
            return jsonify({
                'success': False,
                'error': '今日暂无新闻数据，请先爬取消费趋势新闻'
            })
        
        # 数据清洗 + 关键词过滤
        filtered_news = _filter_trending_news(news_list)
        
        if not filtered_news:
            return jsonify({
                'success': False,
                'error': '未找到银发经济/单身经济相关内容，请先爬取消费趋势新闻'
            })
        
        # 生成消费趋势汇总
        summarizer = QwenSummarizer()
        summary = _generate_trending_summary(summarizer, filtered_news)
        
        # 构建消息
        weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][datetime.now().weekday()]
        title = f"🔥 {today} {weekday} 消费趋势日报"
        source_stats = _get_source_stats(filtered_news)
        header = f"{title}\n\n📈 数据来源：{source_stats}\n💡 聚焦：银发经济 | 单身经济 | 新消费趋势\n"
        full_message = header + "\n" + summary
        
        # 推送到企业微信
        bot = WeChatBot()
        success = bot.send_markdown(full_message)
        
        if success:
            # 保存日报
            _save_trending_report(today, full_message)
            return jsonify({
                'success': True,
                'message': f'消费趋势日报推送成功！共汇总 {len(filtered_news)} 条相关新闻',
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


def _filter_trending_news(news_list):
    """筛选银发经济/单身经济相关新闻"""
    keywords = [
        # 银发经济
        '银发', '养老', '老年', '老龄', '退休', '养老产业', '养老社区',
        '适老', '老年消费', '银发市场', '养老金融', '医养',
        # 单身经济
        '单身', '独居', '一人经济', '单身经济', '独居生活', '一个人',
        '单身消费', '独居青年', '一人食', '迷你', '小家电',
        # 新消费趋势
        '新消费', '消费升级', '消费趋势', '年轻人消费', 'Z世代',
        '宠物经济', '陪伴经济', '情绪价值', '悦己消费',
    ]
    
    cleaned = []
    seen_titles = set()
    
    for news in news_list:
        title = news.get('title', '').strip()
        content = news.get('content', '').strip()
        
        if not title or len(title) < 5:
            continue
        
        # 检查关键词
        full_text = title + ' ' + content[:500]
        if not any(kw in full_text for kw in keywords):
            continue
        
        # 去重
        title_key = title[:15]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        
        cleaned.append({
            'id': news.get('id', ''),
            'title': title,
            'content': content.replace('\n\n', '\n').replace('  ', ' ')[:500],
            'pub_time': news.get('pub_time', ''),
            'source': news.get('source', ''),
            'url': news.get('url', '')
        })
    
    cleaned.sort(key=lambda x: x['pub_time'], reverse=True)
    return cleaned


def _generate_trending_summary(summarizer, news_list):
    """生成消费趋势专项汇总"""
    # 构建消费趋势专用提示词
    news_text = []
    for i, news in enumerate(news_list[:20], 1):
        title = news.get('title', '')
        content = news.get('content', '')[:300]
        source = news.get('source', '')
        pub_time = news.get('pub_time', '')
        news_text.append(f"【{i}】{title}\n来源：{source} | 时间：{pub_time}\n内容摘要：{content}\n")
    
    news_content = "\n".join(news_text)
    
    prompt = f"""你是一位专业的消费趋势分析师，专注于银发经济、单身经济和新消费领域。

请将以下今日消费行业新闻汇总成一份专业、简洁、可读性高的消费趋势日报。

要求：
1. 重点聚焦三大领域：银发经济（养老产业、老年消费）、单身经济（独居生活、一人经济）、新消费趋势（情绪价值、悦己消费等）
2. 按领域分类整理，每个领域选取最重要的3-5条新闻
3. 对每条新闻添加简要的趋势分析或商业价值评估
4. 最后添加一段今日消费趋势总结（50-100字），提炼核心洞察
5. 使用Markdown格式，标题清晰，便于阅读
6. 总字数控制在1500字以内

以下是今日消费行业新闻原始数据：

{news_content}

请生成今日消费趋势日报："""

    return summarizer._call_api(prompt)


def _save_trending_report(date, content):
    """保存消费趋势日报"""
    report_dir = 'reports'
    os.makedirs(report_dir, exist_ok=True)
    filepath = os.path.join(report_dir, f'trending_{date}.md')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


@app.route('/api/news')
def api_news():
    """获取新闻列表"""
    date = request.args.get('date', datetime.now().strftime('%Y%m%d'))
    source = request.args.get('source', 'all')
    keyword = request.args.get('keyword', '').lower()
    
    news = load_by_date(date)
    
    # 源筛选（支持财经源和消费趋势源）
    if source != 'all' and source in CRAWLERS:
        news = [n for n in news if n.get('source') == CRAWLERS[source][0]]
    
    # 关键词搜索
    if keyword:
        news = [n for n in news if keyword in n.get('title', '').lower() 
                or keyword in n.get('content', '').lower()]
    
    return jsonify({'total': len(news), 'news': news})


@app.route('/api/sources')
def api_sources():
    """获取所有数据源列表"""
    return jsonify({
        'finance': [
            {'key': 'eastmoney', 'name': '东方财富'},
            {'key': 'sina', 'name': '新浪财经'},
            {'key': 'cls', 'name': '财联社'},
        ],
        'trending': [
            {'key': '36kr', 'name': '36氪'},
            {'key': 'jiemian', 'name': '界面新闻'},
            {'key': 'huxiu', 'name': '虎嗅'},
        ]
    })


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
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    print(f"启动服务: http://127.0.0.1:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)
