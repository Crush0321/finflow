#!/usr/bin/env python3
"""
企业微信机器人推送模块
"""
import json
import requests
from typing import List


class WeChatBot:
    """企业微信机器人"""
    
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.webhook_url = config['wechat']['webhook_url']
        self.mentioned_list = config['wechat'].get('mentioned_list', [])
        self.mentioned_mobile_list = config['wechat'].get('mentioned_mobile_list', [])
    
    def send_text(self, content: str) -> bool:
        """
        发送文本消息
        """
        if len(content) > 2048:
            content = content[:2045] + "..."
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": self.mentioned_list,
                "mentioned_mobile_list": self.mentioned_mobile_list
            }
        }
        
        return self._send(payload)
    
    def send_markdown(self, content: str) -> bool:
        """
        发送Markdown消息
        """
        # 企业微信限制4096字节
        if len(content.encode('utf-8')) > 4000:
            content = content[:2000] + "\n\n...（内容已截断）"
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        return self._send(payload)
    
    def send_news_card(self, title: str, description: str, url: str, pic_url: str = "") -> bool:
        """
        发送图文卡片
        """
        payload = {
            "msgtype": "news",
            "news": {
                "articles": [
                    {
                        "title": title[:128],
                        "description": description[:512],
                        "url": url,
                        "picurl": pic_url
                    }
                ]
            }
        }
        
        return self._send(payload)
    
    def send_file(self, file_path: str) -> bool:
        """
        发送文件（需要先上传）
        """
        # 上传文件获取media_id
        media_id = self._upload_file(file_path)
        if not media_id:
            return False
        
        payload = {
            "msgtype": "file",
            "file": {
                "media_id": media_id
            }
        }
        
        return self._send(payload)
    
    def _send(self, payload: dict) -> bool:
        """发送请求"""
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.webhook_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                print("✅ 消息推送成功")
                return True
            else:
                print(f"❌ 推送失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            return False
    
    def _upload_file(self, file_path: str) -> str:
        """上传文件获取media_id"""
        try:
            # 企业微信上传接口
            upload_url = self.webhook_url.replace('send', 'upload_media')
            upload_url += "&type=file"
            
            with open(file_path, 'rb') as f:
                files = {'media': f}
                response = requests.post(upload_url, files=files, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if result.get('errcode') == 0:
                    return result['media_id']
                else:
                    print(f"上传文件失败: {result}")
                    return ""
                    
        except Exception as e:
            print(f"上传文件异常: {e}")
            return ""


if __name__ == '__main__':
    # 测试
    bot = WeChatBot()
    bot.send_markdown("## 测试消息\n这是一条来自FinFlow的测试消息。")
