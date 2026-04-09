#!/usr/bin/env python3
"""
爬虫API - 东方财富/新浪财经/财联社/36氪/虎嗅
"""
import requests
import time
import random
import json
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup

# Selenium 浏览器自动化（用于JS渲染网站）
try:
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium 未安装，浏览器自动化功能不可用")
    print("运行: pip install selenium webdriver-manager")

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

def crawl_36kr():
    """36氪-消费与生活频道（使用浏览器自动化）"""
    if SELENIUM_AVAILABLE:
        print("   使用浏览器自动化爬取36氪...")
        return crawl_36kr_selenium()
    else:
        print("   警告: Selenium未安装，36氪爬取失败")
        return []


def crawl_jiemian():
    """界面新闻-生活方式频道"""
    # 尝试多个可能有内容的频道
    urls = [
        "https://www.jiemian.com/lists/132.html",  # 商业
        "https://www.jiemian.com/lists/51.html",   # 生活
        "https://www.jiemian.com/lists/89.html",   # 消费
    ]
    all_news = []
    for url in urls:
        news = parse_news(url, "https://www.jiemian.com/",
            r'https?://www\.jiemian\.com/article/\d+\.html', max_count=10)
        all_news.extend(news)
        if len(all_news) >= 15:
            break
    
    selectors = {
        'content': ['#content', '.article-content', '.article-detail', 
                    '.content-main', '.article-body'],
    }
    seen = set()
    unique_news = []
    for n in all_news:
        if n['url'] not in seen:
            seen.add(n['url'])
            n['source'] = '界面新闻'
            n['content'], n['pub_time'] = extract_content_and_time(n['url'], selectors, "https://www.jiemian.com/")
            unique_news.append(n)
    return unique_news[:15]


def create_browser_driver(headless=True):
    """创建 Edge 浏览器驱动"""
    if not SELENIUM_AVAILABLE:
        return None
    
    try:
        options = EdgeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 尝试使用系统自带的 Edge 驱动
        try:
            # 使用 webdriver-manager 自动管理驱动
            from webdriver_manager.microsoft import EdgeChromiumDriverManager
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
        except:
            # 如果下载失败，尝试使用本地 Edge 驱动
            print("   尝试使用本地 Edge 驱动...")
            driver = webdriver.Edge(options=options)
        
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"浏览器驱动创建失败: {e}")
        return None


def crawl_36kr_selenium():
    """36氪-使用Selenium浏览器自动化（简化版）"""
    if not SELENIUM_AVAILABLE:
        return []
    
    driver = None
    all_news = []
    seen_urls = set()
    
    try:
        driver = create_browser_driver(headless=True)
        if not driver:
            return []
        
        # 只尝试首页
        entry_url = "https://36kr.com/"
        print(f"   正在加载: {entry_url}")
        
        try:
            driver.get(entry_url)
            
            # 简单等待，不检查特定元素
            time.sleep(5)
            
            # 获取页面源码
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            # 查找文章链接（多种模式）
            links = soup.find_all('a', href=re.compile(r'/p/\d+'))
            print(f"   找到 {len(links)} 个链接")
            
            for link in links[:15]:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                if not title or len(title) < 8:
                    continue
                
                # 处理相对URL
                if href.startswith('/'):
                    href = 'https://36kr.com' + href
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                all_news.append({
                    'id': str(hash(href) & 0xFFFFFFFF),
                    'title': title,
                    'url': href,
                    'content': '',
                    'pub_time': '',
                    'source': '36氪'
                })
                
        except Exception as e:
            print(f"   36Kr页面加载失败: {e}")
                
    except Exception as e:
        print(f"   36Kr浏览器爬取异常: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
    
    # 去重
    unique_news = []
    seen = set()
    for n in all_news:
        if n['url'] not in seen:
            seen.add(n['url'])
            unique_news.append(n)
    
    # 提取详情
    selectors = {
        'content': ['.article-detail', '.articleContent', '.common-width.content', 
                    '.article-body', '.article-content', '.kr-article-body', '.article'],
    }
    
    for n in unique_news[:15]:
        n['content'], n['pub_time'] = extract_content_and_time(
            n['url'], selectors, "https://36kr.com/")
    
    return unique_news[:15]


def crawl_huxiu():
    """虎嗅-消费与商业频道（使用浏览器自动化）"""
    if SELENIUM_AVAILABLE:
        print("   使用浏览器自动化爬取虎嗅...")
        return crawl_huxiu_selenium()
    else:
        print("   警告: Selenium未安装，虎嗅爬取失败")
        return []


def crawl_huxiu_selenium():
    """虎嗅-使用Selenium浏览器自动化"""
    if not SELENIUM_AVAILABLE:
        return []
    
    driver = None
    all_news = []
    seen_urls = set()
    
    try:
        driver = create_browser_driver(headless=True)
        if not driver:
            return []
        
        urls_to_try = [
            "https://www.huxiu.com/channel/105.html",  # 消费
            "https://www.huxiu.com/",  # 首页
        ]
        
        for entry_url in urls_to_try:
            try:
                print(f"   正在加载: {entry_url}")
                driver.get(entry_url)
                
                # 等待页面加载
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/article/']")))
                
                # 滚动加载更多内容
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 获取页面源码
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                
                # 查找文章链接
                links = soup.find_all('a', href=re.compile(r'/article/\d+'))
                print(f"   找到 {len(links)} 个链接")
                
                for link in links[:15]:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not title or len(title) < 8:
                        continue
                    
                    # 处理URL
                    if href.startswith('/'):
                        href = 'https://www.huxiu.com' + href
                    elif not href.startswith('http'):
                        href = 'https://www.huxiu.com/' + href
                    
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    all_news.append({
                        'id': str(hash(href) & 0xFFFFFFFF),
                        'title': title,
                        'url': href,
                        'content': '',
                        'pub_time': '',
                        'source': '虎嗅'
                    })
                    
            except Exception as e:
                print(f"   虎嗅页面加载失败 ({entry_url}): {e}")
                continue
                
    except Exception as e:
        print(f"   虎嗅浏览器爬取异常: {e}")
    finally:
        if driver:
            driver.quit()
    
    # 去重
    unique_news = []
    seen = set()
    for n in all_news:
        if n['url'] not in seen:
            seen.add(n['url'])
            unique_news.append(n)
    
    # 提取详情
    selectors = {
        'content': ['.article-content', '.article-body', '#article-content',
                    '.content-main', '.article-detail', '.article-wrap'],
    }
    
    for n in unique_news[:15]:
        n['content'], n['pub_time'] = extract_content_and_time(
            n['url'], selectors, "https://www.huxiu.com/")
    
    return unique_news[:15]


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


def crawl_all(sources=None):
    """抓取所有
    
    Args:
        sources: 指定要爬取的源列表，None表示全部财经源
                 'finance' - 财经三源 (东财/新浪/财联)
                 'trending' - 消费趋势三源 (36氪/界面/虎嗅)
    """
    # 定义爬虫配置
    all_crawlers = [
        ('东方财富', crawl_eastmoney, 'eastmoney'),
        ('新浪财经', crawl_sina, 'sina'),
        ('财联社', crawl_cls, 'cls'),
        ('36氪', crawl_36kr, '36kr'),
        ('界面新闻', crawl_jiemian, 'jiemian'),
        ('虎嗅', crawl_huxiu, 'huxiu'),
    ]
    
    # 根据参数筛选
    if sources == 'finance':
        crawlers = all_crawlers[:3]
    elif sources == 'trending':
        crawlers = all_crawlers[3:]
    else:
        crawlers = all_crawlers
    
    results = {}
    total = len(crawlers)
    for i, (name, func, key) in enumerate(crawlers, 1):
        print(f"[{i}/{total}] 抓取{name}...")
        try:
            news = func()
            if news:
                path, count = save(news, key)
                results[name] = {'count': count, 'file': path}
                print(f"   ✓ 获取 {count} 条")
            else:
                print(f"   ✗ 无数据")
        except Exception as e:
            print(f"   ✗ 错误: {e}")
    
    return results


def crawl_trending():
    """专门抓取消费趋势源（36氪+界面+虎嗅）"""
    return crawl_all(sources='trending')


if __name__ == '__main__':
    import sys
    
    # 支持命令行参数
    # python spider_api.py           # 爬取全部
    # python spider_api.py finance   # 只爬财经源
    # python spider_api.py trending  # 只爬消费趋势源
    
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    r = crawl_all(sources=arg)
    print("\n完成:", {k: v['count'] for k, v in r.items()})
