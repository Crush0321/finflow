#!/usr/bin/env python3
"""
爬虫API - 东方财富/新浪财经/财联社
"""
import requests
import time
import random
import json
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
]


def fetch(url, referer=""):
    """请求页面"""
    for i in range(3):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            if referer:
                headers["Referer"] = referer
            r = requests.get(url, headers=headers, timeout=15)
            r.encoding = r.apparent_encoding or 'utf-8'
            if r.status_code == 200:
                return r.text
        except:
            if i == 2:
                return None
            time.sleep(2 ** i)
    return None


def extract_time(soup, url):
    """多策略提取发布时间"""
    pub_time = ""
    
    # 策略1: 常用CSS选择器
    time_selectors = [
        '.time', '.date', '.pub-time', '.publish-time',
        '.info-source .time', '.news-source', '.source',
        '.post-time', '.article-time', '.release-time',
        '[class*="time"]', '[class*="date"]',
        'span.time', 'div.time', 'p.time',
        '.meta .time', '.meta time', 'time',
    ]
    
    for sel in time_selectors:
        tag = soup.select_one(sel)
        if tag:
            text = tag.get_text(strip=True)
            # 匹配时间格式 (2026-04-03 或 2026年04月03日 或 04-03 等)
            if re.search(r'\d{4}|\d{2}[:\-]', text):
                pub_time = text
                break
    
    # 策略2: 从meta标签提取
    if not pub_time:
        meta_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publishdate"]',
            'meta[name="PublishDate"]',
            'meta[name="publishDate"]',
            'meta[name="pubdate"]',
            'meta[name="PubDate"]',
        ]
        for sel in meta_selectors:
            tag = soup.select_one(sel)
            if tag and tag.get('content'):
                pub_time = tag['content'][:19]  # 只取前19个字符 (YYYY-MM-DD HH:MM:SS)
                break
    
    # 策略3: 正则从HTML中提取
    if not pub_time:
        html = str(soup)
        # 匹配常见时间格式
        patterns = [
            r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日\s]\d{1,2}:\d{1,2})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                pub_time = match.group(1)
                break
    
    # 清理格式
    if pub_time:
        pub_time = re.sub(r'\s+', ' ', pub_time).strip()[:30]
    
    return pub_time


def extract_content_and_time(url, selectors, referer):
    """提取正文和发布时间"""
    html = fetch(url, referer)
    if not html:
        return "", ""
    
    soup = BeautifulSoup(html, 'lxml')
    
    # 提取正文
    content = ""
    for sel in selectors.get('content', []):
        tag = soup.select_one(sel)
        if tag:
            text = tag.get_text(separator='\n', strip=True)
            content = re.sub(r'\s+', ' ', text)[:8000]
            break
    
    if not content:
        ps = soup.find_all('p')
        content = '\n'.join([p.get_text(strip=True) for p in ps if len(p.get_text(strip=True)) > 20])[:8000]
    
    # 提取发布时间
    pub_time = extract_time(soup, url)
    
    return content, pub_time


def parse_news(url, referer, link_pattern, title_min_len=8, max_count=20):
    """通用新闻列表解析"""
    html = fetch(url, referer)
    if not html:
        return []
    soup = BeautifulSoup(html, 'lxml')
    links = soup.find_all('a', href=re.compile(link_pattern))
    
    seen, news_list = set(), []
    for link in links[:max_count]:
        title = link.get_text(strip=True)
        href = link.get('href', '')
        if not title or href in seen or len(title) < title_min_len:
            continue
        seen.add(href)
        if not href.startswith('http'):
            href = 'https:' + href if href.startswith('//') else url.rstrip('/') + href
        news_list.append({
            'id': str(hash(href) & 0xFFFFFFFF),
            'title': title,
            'url': href,
            'content': '',
            'pub_time': '',
        })
    return news_list


# ============ 各站点爬虫 ============

def crawl_eastmoney():
    news = parse_news("https://www.eastmoney.com/", "", r'/(a|news)/\d+')
    selectors = {
        'content': ['#ContentBody', '.newsContent', '#newsContent', '.article-content', '.content'],
    }
    for n in news:
        n['source'] = '东方财富'
        n['content'], n['pub_time'] = extract_content_and_time(n['url'], selectors, "https://www.eastmoney.com/")
    return news


def crawl_sina():
    news = parse_news("https://finance.sina.com.cn/", "https://finance.sina.com.cn/",
        r'https?://finance\.sina\.com\.cn/.+/\d{4}-\d{2}-\d{2}/doc-[a-zA-Z0-9]+\.shtml')
    selectors = {
        'content': ['#artibody', '.article', '#article_content', '.article-content'],
    }
    for n in news:
        n['source'] = '新浪财经'
        n['content'], n['pub_time'] = extract_content_and_time(n['url'], selectors, "https://finance.sina.com.cn/")
    return news


def crawl_cls():
    news = parse_news("https://www.cls.cn/", "https://www.cls.cn/", r'/detail/\d+')
    selectors = {
        'content': ['.content', '.article-content', '#content', '.detail-content'],
    }
    for n in news:
        n['source'] = '财联社'
        if not n['url'].startswith('http'):
            n['url'] = 'https://www.cls.cn' + n['url']
        n['content'], n['pub_time'] = extract_content_and_time(n['url'], selectors, "https://www.cls.cn/")
    return news


# ============ 数据操作 ============

def save(news_list, source_name):
    """保存新闻"""
    today = datetime.now().strftime('%Y%m%d')
    data_dir = os.path.join('data', today)
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f'{source_name}_{today}.json')
    
    existing = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass
    
    existing_ids = {n['id'] for n in existing}
    for news in news_list:
        if news['id'] not in existing_ids:
            existing.append(news)
            existing_ids.add(news['id'])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    return filepath, len(existing)


def load_by_date(date_str=None):
    """加载指定日期"""
    if not date_str:
        date_str = datetime.now().strftime('%Y%m%d')
    data_dir = os.path.join('data', date_str)
    if not os.path.exists(data_dir):
        return []
    
    all_news = []
    for fn in os.listdir(data_dir):
        if fn.endswith('.json'):
            try:
                with open(os.path.join(data_dir, fn), 'r', encoding='utf-8') as f:
                    all_news.extend(json.load(f))
            except:
                pass
    all_news.sort(key=lambda x: x.get('pub_time', ''), reverse=True)
    return all_news


def load_dates():
    """加载所有日期"""
    if not os.path.exists('data'):
        return []
    return sorted([d for d in os.listdir('data') 
        if os.path.isdir(os.path.join('data', d)) and d.isdigit()], reverse=True)


def crawl_all():
    """抓取所有"""
    results = {}
    for name, func, key in [('东方财富', crawl_eastmoney, 'eastmoney'),
                            ('新浪财经', crawl_sina, 'sina'),
                            ('财联社', crawl_cls, 'cls')]:
        print(f"[{list(results.keys()).index(name)+1 if results else 1}/3] 抓取{name}...")
        news = func()
        if news:
            path, count = save(news, key)
            results[name] = {'count': count, 'file': path}
    return results


if __name__ == '__main__':
    r = crawl_all()
    print("\n完成:", {k: v['count'] for k, v in r.items()})
