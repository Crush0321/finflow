#!/usr/bin/env python3
"""
测试日报生成功能（不推送）
"""
import json
from datetime import datetime
from spider_api import crawl_eastmoney, crawl_sina, crawl_cls, save
from summarizer import QwenSummarizer

def test_report():
    """测试生成日报"""
    print("开始测试日报生成...\n")
    
    # 检查配置
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        if 'YOUR_' in config['dashscope']['api_key']:
            print("⚠️ 警告: 请在 config.json 中配置通义千问API Key")
            return
    except Exception as e:
        print(f"❌ 配置文件错误: {e}")
        return
    
    # 爬取少量新闻测试
    print("[1/3] 爬取新闻...")
    news = crawl_eastmoney()
    if news:
        save(news, 'eastmoney')
        print(f"✅ 获取 {len(news)} 条新闻")
    
    # 数据清洗
    print("\n[2/3] 数据清洗...")
    cleaned = []
    seen = set()
    for n in news[:10]:  # 只取10条测试
        title = n.get('title', '').strip()
        if title and title[:10] not in seen:
            seen.add(title[:10])
            cleaned.append({
                'title': title,
                'content': n.get('content', '')[:300],
                'pub_time': n.get('pub_time', ''),
                'source': n.get('source', '')
            })
    print(f"✅ 清洗后 {len(cleaned)} 条")
    
    # 生成汇总
    print("\n[3/3] 调用通义千问生成汇总...")
    summarizer = QwenSummarizer()
    summary = summarizer.summarize(cleaned)
    
    print("\n" + "="*60)
    print("生成的日报内容:")
    print("="*60)
    print(summary)
    print("="*60)
    
    # 保存到文件
    today = datetime.now().strftime('%Y%m%d')
    with open(f'test_report_{today}.md', 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"\n✅ 测试报告已保存: test_report_{today}.md")

if __name__ == '__main__':
    test_report()
