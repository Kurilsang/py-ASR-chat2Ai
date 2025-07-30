"""
AI对话服务 - 策略模式实现
支持多种AI服务：简单AI、Ollama、OpenAI
"""

import os
import time
import random
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from utils.config_manager import ConfigManager


class AIServiceInterface(ABC):
    """AI服务接口"""
    
    @abstractmethod
    def get_response(self, message: str) -> str:
        """
        获取AI回复
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        pass
    
    @abstractmethod
    def get_service_name(self) -> str:
        """获取服务名称"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查服务是否可用"""
        pass


class SimpleAIService(AIServiceInterface):
    """简单AI服务 - 基于规则的本地AI"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化简单AI服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self._initialize_responses()
    
    def _initialize_responses(self):
        """初始化回复模板"""
        self.response_templates = {
            "问候": [
                "你好！很高兴和你聊天！",
                "你好呀！有什么可以帮助你的吗？",
                "嗨！今天心情怎么样？"
            ],
            "时间": [
                f"现在是{time.strftime('%Y年%m月%d日 %H点%M分')}",
                "时间过得真快呢！",
                "让我看看现在几点了"
            ],
            "天气": [
                "今天天气还不错呢！",
                "我是AI，看不到窗外的天气，但希望今天是个好天气！",
                "不论什么天气，保持好心情最重要！"
            ],
            "告别": [
                "再见！期待下次和你聊天！",
                "拜拜！祝你今天愉快！",
                "下次见！保重身体哦！"
            ],
            "感谢": [
                "不客气！很高兴能帮到你！",
                "这是我应该做的！",
                "能为你服务我很开心！"
            ],
            "默认": [
                "这是个很有趣的问题！",
                "我理解你的意思，让我想想",
                "谢谢你跟我分享这个！",
                "你说得很有道理！",
                "这让我学到了新东西！",
                "我觉得你的想法很棒！"
            ]
        }
    
    def get_response(self, message: str) -> str:
        """
        获取简单AI回复
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        message_lower = message.lower()
        
        # 问候词检测
        greetings = ["你好", "您好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好"]
        if any(greeting in message_lower for greeting in greetings):
            return random.choice(self.response_templates["问候"])
        
        # 告别词检测
        farewells = ["再见", "拜拜", "回头见", "告别", "bye", "goodbye"]
        if any(farewell in message_lower for farewell in farewells):
            return random.choice(self.response_templates["告别"])
        
        # 感谢词检测
        thanks = ["谢谢", "感谢", "thank", "thanks"]
        if any(thank in message_lower for thank in thanks):
            return random.choice(self.response_templates["感谢"])
        
        # 时间相关
        time_words = ["时间", "几点", "现在", "日期", "今天"]
        if any(word in message_lower for word in time_words):
            return random.choice(self.response_templates["时间"])
        
        # 天气相关
        weather_words = ["天气", "气温", "下雨", "晴天", "阴天"]
        if any(word in message_lower for word in weather_words):
            return random.choice(self.response_templates["天气"])
        
        # 默认回复
        return random.choice(self.response_templates["默认"])
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return "简单AI"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return True


class OllamaAIService(AIServiceInterface):
    """Ollama AI服务"""
    
    def __init__(self, config_manager: ConfigManager, model: str = "qwen2:0.5b"):
        """
        初始化Ollama AI服务
        
        Args:
            config_manager: 配置管理器
            model: 使用的模型名称
        """
        self.config = config_manager
        self.model = model
        self.base_url = "http://localhost:11434/api/generate"
        self.timeout = 30
    
    def get_response(self, message: str) -> str:
        """
        获取Ollama AI回复
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        try:
            payload = {
                "model": self.model,
                "prompt": f"你是一个友善的AI助手，请用中文简洁地回答用户的问题。用户说：{message}",
                "stream": False
            }
            
            response = requests.post(self.base_url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '抱歉，我无法理解您的问题。')
            else:
                return f"Ollama服务错误：{response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return "无法连接到Ollama服务，请确保Ollama正在运行。"
        except requests.exceptions.Timeout:
            return "请求超时，请稍后再试。"
        except Exception as e:
            return f"Ollama对话出错：{e}"
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"Ollama ({self.model})"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> list:
        """列出可用的模型"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []
    
    def set_model(self, model: str):
        """设置使用的模型"""
        self.model = model


class OpenAIService(AIServiceInterface):
    """OpenAI GPT服务"""
    
    def __init__(self, config_manager: ConfigManager, model: str = "gpt-3.5-turbo"):
        """
        初始化OpenAI服务
        
        Args:
            config_manager: 配置管理器
            model: 使用的模型名称
        """
        self.config = config_manager
        self.model = model
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.timeout = 30
    
    def get_response(self, message: str) -> str:
        """
        获取OpenAI回复
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        if not self.api_key:
            return "请设置OPENAI_API_KEY环境变量"
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个友善的AI助手，请用中文简洁地回答用户的问题。"},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return f"OpenAI API错误：{response.status_code}"
                
        except Exception as e:
            return f"OpenAI对话出错：{e}"
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"OpenAI ({self.model})"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.api_key:
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # 测试API连接
            test_payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=test_payload,
                timeout=5
            )
            
            return response.status_code == 200
        except:
            return False


class AIServiceWithFallback:
    """带有回退机制的AI服务"""
    
    def __init__(self, primary_service: AIServiceInterface, fallback_service: AIServiceInterface):
        """
        初始化带回退的AI服务
        
        Args:
            primary_service: 主要AI服务
            fallback_service: 回退AI服务
        """
        self.primary_service = primary_service
        self.fallback_service = fallback_service
    
    def get_response(self, message: str) -> str:
        """
        获取AI回复（带回退机制）
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        print(f"🤖 正在思考回复...")
        
        # 尝试主要服务
        try:
            response = self.primary_service.get_response(message)
            
            # 检查是否需要回退
            if self._should_fallback(response):
                print(f"🔄 {self.primary_service.get_service_name()}服务不可用，使用{self.fallback_service.get_service_name()}回复...")
                return self.fallback_service.get_response(message)
            
            return response
            
        except Exception as e:
            print(f"🔄 {self.primary_service.get_service_name()}出错，使用{self.fallback_service.get_service_name()}回复...")
            return self.fallback_service.get_response(message)
    
    def _should_fallback(self, response: str) -> bool:
        """
        判断是否需要回退到备选服务
        
        Args:
            response: AI回复
            
        Returns:
            是否需要回退
        """
        fallback_indicators = [
            "错误", "失败", "无法连接", "超时", 
            "请设置", "服务错误", "API错误"
        ]
        
        return any(indicator in response for indicator in fallback_indicators)
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"{self.primary_service.get_service_name()} → {self.fallback_service.get_service_name()}"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.primary_service.is_available() or self.fallback_service.is_available()


class AIServiceFactory:
    """AI服务工厂 - 工厂模式"""
    
    @staticmethod
    def create_service(service_type: str, config_manager: ConfigManager) -> AIServiceInterface:
        """
        创建AI服务实例
        
        Args:
            service_type: 服务类型 ('simple', 'ollama', 'openai')
            config_manager: 配置管理器
            
        Returns:
            AI服务实例
        """
        if service_type == "simple":
            return SimpleAIService(config_manager)
        elif service_type == "ollama":
            return OllamaAIService(config_manager)
        elif service_type == "openai":
            return OpenAIService(config_manager)
        else:
            raise ValueError(f"不支持的AI服务类型：{service_type}")
    
    @staticmethod
    def create_service_with_fallback(
        primary_type: str, 
        config_manager: ConfigManager,
        fallback_type: str = "simple"
    ) -> AIServiceWithFallback:
        """
        创建带回退机制的AI服务
        
        Args:
            primary_type: 主要服务类型
            config_manager: 配置管理器
            fallback_type: 回退服务类型，默认为简单AI
            
        Returns:
            带回退机制的AI服务
        """
        primary_service = AIServiceFactory.create_service(primary_type, config_manager)
        fallback_service = AIServiceFactory.create_service(fallback_type, config_manager)
        
        return AIServiceWithFallback(primary_service, fallback_service)
    
    @staticmethod
    def get_available_services() -> list:
        """获取可用的服务类型列表"""
        return ["simple", "ollama", "openai"]
    
    @staticmethod
    def get_service_description(service_type: str) -> str:
        """
        获取服务描述
        
        Args:
            service_type: 服务类型
            
        Returns:
            服务描述
        """
        descriptions = {
            "simple": "本地免费，立即可用",
            "ollama": "本地免费，需要先安装",
            "openai": "在线付费，需要API Key"
        }
        
        return descriptions.get(service_type, "未知服务") 