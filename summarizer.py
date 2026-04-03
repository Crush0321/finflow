#!/usr/bin/env python3
"""
通义千问文本汇总模块
"""
import json
import requests
from typing import List, Dict


class QwenSummarizer:
    """通义千问文本汇总器"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.api_key = config['dashscope']['api_key']
        self.model = config['dashscope']['model']
        self.base_url = config['dashscope']['base_url']
        self.style = config['summary']['style']
    
    def summarize(self, news_list: List[Dict]) -> str:
        """
        将新闻列表汇总成可读性高的文字
        """
        if not news_list:
            return "今日暂无重要财经资讯。"
        
        # 构建提示词
        prompt = self._build_prompt(news_list)
        
        # 调用通义千问API
        return self._call_api(prompt)
    
    def _build_prompt(self, news_list: List[Dict]) -> str:
        """构建提示词"""
        # 准备新闻内容
        news_text = []
        for i, news in enumerate(news_list[:20], 1):  # 最多取20条
            title = news.get('title', '')
            content = news.get('content', '')[:300]  # 正文前300字
            source = news.get('source', '')
            pub_time = news.get('pub_time', '')
            
            news_text.append(f"【{i}】{title}\n来源：{source} | 时间：{pub_time}\n内容摘要：{content}\n")
        
        news_content = "\n".join(news_text)
        
        prompt = f"""你是一位专业的财经资讯分析师。请将以下今日财经新闻汇总成一份专业、简洁、可读性高的日报。

要求：
1. {self.style}
2. 按重要性对新闻进行分类（如：市场动态、政策解读、公司要闻、行业热点等）
3. 每个类别选取最重要的3-5条新闻进行简述
4. 对重要新闻添加简要分析或影响评估
5. 最后添加一段今日市场总结（50-100字）
6. 使用Markdown格式，便于阅读
7. 总字数控制在1500字以内

以下是今日新闻原始数据：

{news_content}

请生成今日财经日报："""
        
        return prompt
    
    def _call_api(self, prompt: str) -> str:
        """调用通义千问API"""
        url = f"{self.base_url}/services/aigc/text-generation/generation"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是专业的财经资讯分析师，擅长将财经新闻整理成专业、易读的日报。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "result_format": "message",
                "max_tokens": 2000,
                "temperature": 0.7,
                "top_p": 0.8
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            
            if 'output' in result and 'choices' in result['output']:
                return result['output']['choices'][0]['message']['content']
            else:
                print(f"API响应异常: {result}")
                return self._fallback_summary(news_list)
                
        except Exception as e:
            print(f"调用通义千问API失败: {e}")
            # 降级处理：返回简单汇总
            return self._fallback_summary(news_list)
    
    def _fallback_summary(self, news_list: List[Dict]) -> str:
        """API失败时的降级处理"""
        lines = ["## 📊 今日财经热点\n"]
        
        # 按来源分组
        sources = {}
        for news in news_list[:15]:
            source = news.get('source', '其他')
            if source not in sources:
                sources[source] = []
            sources[source].append(news)
        
        for source, items in sources.items():
            lines.append(f"\n### {source}\n")
            for news in items[:5]:
                title = news.get('title', '')
                pub_time = news.get('pub_time', '')
                lines.append(f"• **{title}**  *{pub_time}*")
        
        lines.append("\n---\n*以上为本日重要财经资讯汇总*")
        return "\n".join(lines)
