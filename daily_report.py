#!/usr/bin/env python3
"""
每日财经日报生成与推送主程序
"""
import os
import sys
import json
from datetime import datetime
from typing import List, Dict

from spider_api import crawl_eastmoney, crawl_sina, crawl_cls, save, load_by_date
from summarizer import QwenSummarizer
from wechat_bot import WeChatBot


class DailyReport:
    """每日财经日报"""
    
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.summarizer = QwenSummarizer(config_path)
        self.bot = WeChatBot(config_path)
    
    def generate_and_send(self) -> bool:
        """
        生成并发送日报
        """
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"\n{'='*60}")
        print(f"📅 开始生成 {today} 财经日报")
        print(f"{'='*60}\n")
        
        # 1. 爬取新闻
        print("[1/4] 正在爬取新闻...")
        all_news = self._crawl_news()
        if not all_news:
            print("⚠️ 未获取到新闻数据")
            self.bot.send_text(f"[{today}] 今日暂无重要财经资讯。")
            return False
        
        print(f"✅ 共获取 {len(all_news)} 条新闻")
        
        # 2. 数据清洗
        print("\n[2/4] 正在清洗数据...")
        cleaned_news = self._clean_news(all_news)
        print(f"✅ 清洗后剩余 {len(cleaned_news)} 条有效新闻")
        
        # 3. 智能汇总
        print("\n[3/4] 正在调用通义千问生成汇总...")
        summary = self.summarizer.summarize(cleaned_news)
        print("✅ 汇总生成完成")
        
        # 4. 推送到企业微信
        print("\n[4/4] 正在推送到企业微信...")
        
        # 构建标题
        weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][datetime.now().weekday()]
        title = f"📊 {today} {weekday} 财经日报"
        
        # 添加标题和来源统计
        source_stats = self._get_source_stats(cleaned_news)
        header = f"{title}\n\n📈 数据来源：{source_stats}\n"
        
        full_message = header + "\n" + summary
        
        # 发送Markdown消息
        success = self.bot.send_markdown(full_message)
        
        if success:
            print(f"\n{'='*60}")
            print("✅ 日报推送成功！")
            print(f"{'='*60}")
            
            # 保存日报到本地
            self._save_report(today, full_message)
            return True
        else:
            print(f"\n{'='*60}")
            print("❌ 日报推送失败")
            print(f"{'='*60}")
            return False
    
    def _crawl_news(self) -> List[Dict]:
        """爬取新闻"""
        all_news = []
        
        # 东方财富
        print("  - 抓取东方财富...")
        em_news = crawl_eastmoney()
        if em_news:
            save(em_news, 'eastmoney')
            all_news.extend(em_news)
        
        # 新浪财经
        print("  - 抓取新浪财经...")
        sina_news = crawl_sina()
        if sina_news:
            save(sina_news, 'sina')
            all_news.extend(sina_news)
        
        # 财联社
        print("  - 抓取财联社...")
        cls_news = crawl_cls()
        if cls_news:
            save(cls_news, 'cls')
            all_news.extend(cls_news)
        
        return all_news
    
    def _clean_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        数据清洗
        """
        cleaned = []
        seen_titles = set()
        
        for news in news_list:
            # 清洗标题
            title = news.get('title', '').strip()
            if not title or len(title) < 5:
                continue
            
            # 去重（标题相似度）
            title_key = title[:15]  # 取前15字作为去重key
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            
            # 清洗正文
            content = news.get('content', '').strip()
            # 移除无用字符
            content = content.replace('\n\n', '\n').replace('  ', ' ')
            
            # 清洗时间
            pub_time = news.get('pub_time', '')
            
            cleaned.append({
                'id': news.get('id', ''),
                'title': title,
                'content': content[:500],  # 限制长度
                'pub_time': pub_time,
                'source': news.get('source', ''),
                'url': news.get('url', '')
            })
        
        # 按时间排序
        cleaned.sort(key=lambda x: x['pub_time'], reverse=True)
        
        return cleaned
    
    def _get_source_stats(self, news_list: List[Dict]) -> str:
        """获取来源统计"""
        sources = {}
        for news in news_list:
            source = news.get('source', '其他')
            sources[source] = sources.get(source, 0) + 1
        
        return " | ".join([f"{k}:{v}条" for k, v in sources.items()])
    
    def _save_report(self, date: str, content: str):
        """保存日报到本地"""
        report_dir = 'reports'
        os.makedirs(report_dir, exist_ok=True)
        
        filepath = os.path.join(report_dir, f'report_{date}.md')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📄 日报已保存: {filepath}")


def main():
    """主函数"""
    report = DailyReport()
    success = report.generate_and_send()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
