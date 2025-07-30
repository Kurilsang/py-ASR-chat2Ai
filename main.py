#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文语音识别+AI对话演示程序
使用speech_recognition库实现ASR，结合AI对话功能
"""

import speech_recognition as sr
import pyaudio
import time
import requests
import json
import os
import random
from typing import Optional


class AIChat:
    """AI对话类"""
    
    def __init__(self, ai_type="simple"):
        """
        初始化AI对话
        
        Args:
            ai_type: AI类型，支持 "simple", "ollama" 或 "openai"
        """
        self.ai_type = ai_type
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.ollama_url = "http://localhost:11434/api/generate"
        
        # 简单AI回复模板
        self.simple_responses = {
            "问候": [
                "你好！很高兴和你聊天！",
                "你好呀！有什么可以帮助你的吗？",
                "嗨！今天心情怎么样？"
            ],
            "时间": [
                f"现在是{time.strftime('%Y年%m月%d日 %H:%M:%S')}",
                "时间过得真快呢！",
                "让我看看现在几点了..."
            ],
            "天气": [
                "今天天气还不错呢！",
                "我是AI，看不到窗外的天气，但希望今天是个好天气！",
                "无论什么天气，保持好心情最重要！"
            ],
            "默认": [
                "这是个很有趣的问题！",
                "我理解你的意思，让我想想...",
                "谢谢你跟我分享这个！",
                "你说得很有道理！",
                "这让我学到了新东西！",
                "我觉得你的想法很棒！"
            ]
        }
    
    def chat_with_simple_ai(self, message: str) -> str:
        """
        使用简单的规则AI回复
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        message_lower = message.lower()
        
        # 问候词检测
        greetings = ["你好", "您好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好"]
        if any(greeting in message_lower for greeting in greetings):
            return random.choice(self.simple_responses["问候"])
        
        # 时间相关
        time_words = ["时间", "几点", "现在", "日期", "今天"]
        if any(word in message_lower for word in time_words):
            return random.choice(self.simple_responses["时间"])
        
        # 天气相关
        weather_words = ["天气", "气温", "下雨", "晴天", "阴天"]
        if any(word in message_lower for word in weather_words):
            return random.choice(self.simple_responses["天气"])
        
        # 默认回复
        return random.choice(self.simple_responses["默认"])
        
    def chat_with_ollama(self, message: str, model: str = "qwen2:0.5b") -> Optional[str]:
        """
        使用Ollama本地模型对话
        
        Args:
            message: 用户消息
            model: 使用的模型名称
            
        Returns:
            AI回复内容
        """
        try:
            payload = {
                "model": model,
                "prompt": f"你是一个友善的AI助手，请用中文简洁地回答用户的问题。用户说：{message}",
                "stream": False
            }
            
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '抱歉，我无法理解您的问题。')
            else:
                return f"Ollama服务错误：{response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return None  # 返回None表示连接失败，会回退到简单AI
        except requests.exceptions.Timeout:
            return "请求超时，请稍后再试。"
        except Exception as e:
            return f"Ollama对话出错：{e}"
    
    def chat_with_openai(self, message: str) -> Optional[str]:
        """
        使用OpenAI GPT对话
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        if not self.openai_api_key:
            return "请设置OPENAI_API_KEY环境变量"
        
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "你是一个友善的AI助手，请用中文简洁地回答用户的问题。"},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                return f"OpenAI API错误：{response.status_code}"
                
        except Exception as e:
            return f"OpenAI对话出错：{e}"
    
    def get_ai_response(self, message: str) -> str:
        """
        获取AI回复
        
        Args:
            message: 用户消息
            
        Returns:
            AI回复内容
        """
        print(f"🤖 正在思考回复...")
        
        if self.ai_type == "simple":
            return self.chat_with_simple_ai(message)
        elif self.ai_type == "ollama":
            response = self.chat_with_ollama(message)
            # 如果Ollama连接失败或出现错误，回退到简单AI
            if response is None or "错误" in response or "失败" in response or "无法连接" in response:
                print("🔄 Ollama服务不可用，使用简单AI回复...")
                return self.chat_with_simple_ai(message)
            return response
        elif self.ai_type == "openai":
            response = self.chat_with_openai(message)
            # 如果OpenAI失败，回退到简单AI
            if response is None or "错误" in response or "失败" in response or "请设置" in response:
                print("🔄 OpenAI服务不可用，使用简单AI回复...")
                return self.chat_with_simple_ai(message)
            return response
        else:
            return "不支持的AI类型"


class ChineseASRWithAI:
    """中文语音识别+AI对话类"""
    
    def __init__(self, ai_type="simple"):
        """初始化语音识别器和AI对话"""
        print("🎤 初始化语音识别系统...")
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.ai_chat = AIChat(ai_type)
        
        # 调整环境噪音
        print("🔧 正在调整环境噪音，请保持安静...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("✅ 环境噪音调整完成！")
    
    def record_audio(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[sr.AudioData]:
        """
        录制音频
        
        Args:
            timeout: 等待开始说话的超时时间（秒）
            phrase_time_limit: 单次录音的最大时长（秒）
            
        Returns:
            录制的音频数据，如果录制失败返回None
        """
        try:
            print(f"🎙️ 请开始说话（{timeout}秒内开始，最长录制{phrase_time_limit}秒）...")
            
            with self.microphone as source:
                # 录制音频
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
            
            print("✅ 录音完成！正在进行语音识别...")
            return audio
            
        except sr.WaitTimeoutError:
            print("❌ 错误：等待超时，未检测到语音输入")
            return None
        except Exception as e:
            print(f"❌ 录音过程中发生错误：{e}")
            return None
    
    def recognize_chinese(self, audio_data: sr.AudioData) -> Optional[str]:
        """
        识别中文语音
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果文本，如果识别失败返回None
        """
        try:
            # 使用Google Speech Recognition识别中文
            print("🔍 正在使用Google ASR识别中文语音...")
            text = self.recognizer.recognize_google(audio_data, language='zh-CN')
            return text
            
        except sr.UnknownValueError:
            print("❌ 识别失败：无法理解音频内容")
            return None
        except sr.RequestError as e:
            print(f"❌ 识别服务错误：{e}")
            # 尝试使用离线识别作为备选方案
            try:
                print("🔄 尝试使用离线识别...")
                text = self.recognizer.recognize_sphinx(audio_data, language='zh-CN')
                return text
            except:
                print("❌ 离线识别也失败了")
                return None
        except Exception as e:
            print(f"❌ 识别过程中发生未知错误：{e}")
            return None
    
    def run_conversation(self):
        """运行语音识别+AI对话"""
        print("\n" + "="*60)
        print("🗣️ 开始语音识别+AI对话")
        print("="*60)
        
        # 步骤1：录制音频
        audio_data = self.record_audio()
        if audio_data is None:
            return False
        
        # 步骤2：语音识别
        user_input = self.recognize_chinese(audio_data)
        if not user_input:
            return False
        
        # 步骤3：显示用户输入
        print(f"\n👤 您说：{user_input}")
        
        # 步骤4：获取AI回复
        ai_response = self.ai_chat.get_ai_response(user_input)
        
        # 步骤5：显示AI回复
        print(f"🤖 AI回复：{ai_response}")
        print("="*60)
        
        return True
    
    def run_continuous_conversation(self):
        """连续对话模式"""
        print("\n🔄 进入连续对话模式")
        print("💡 说'退出'、'结束'或按Ctrl+C可退出程序")
        
        try:
            while True:
                success = self.run_conversation()
                
                if success:
                    # 检查是否要退出
                    time.sleep(1)  # 短暂暂停
                    
                # 询问是否继续
                choice = input("\n⏭️ 按Enter继续对话，输入'quit'退出：").strip().lower()
                if choice in ['quit', 'q', '退出', '结束']:
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 程序被用户中断")
        except Exception as e:
            print(f"\n❌ 连续对话过程中发生错误：{e}")


def check_dependencies():
    """检查依赖包是否安装"""
    try:
        import speech_recognition
        import pyaudio
        import requests
        print("✅ 基本依赖包检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包：{e}")
        print("\n📦 请安装以下依赖包：")
        print("pip install SpeechRecognition pyaudio requests")
        return False


def setup_ai_service():
    """设置AI服务"""
    print("\n🤖 选择AI对话服务：")
    print("1. 简单AI (本地免费，立即可用)")
    print("2. Ollama (本地免费，需要先安装)")
    print("3. OpenAI GPT (在线付费，需要API Key)")
    
    choice = input("请选择（1、2或3）：").strip()
    
    if choice == '1':
        print("\n💡 使用简单AI：基于规则的本地AI回复")
        return "simple"
    elif choice == '2':
        print("\n📋 Ollama使用说明：")
        print("1. 访问 https://ollama.ai 下载安装Ollama")
        print("2. 运行: ollama pull qwen2:0.5b  (下载中文模型)")
        print("3. 确保Ollama服务正在运行")
        print("💡 如果连接失败会自动回退到简单AI")
        return "ollama"
    elif choice == '3':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("\n⚠️ 需要设置OpenAI API Key:")
            print("set OPENAI_API_KEY=your_api_key_here  (Windows)")
            print("export OPENAI_API_KEY=your_api_key_here  (Linux/Mac)")
        print("💡 如果连接失败会自动回退到简单AI")
        return "openai"
    else:
        print("❌ 无效选择，默认使用简单AI")
        return "simple"


def main():
    """主函数"""
    print("🎙️ 中文语音识别+AI对话演示程序")
    print("="*60)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 选择AI服务
    ai_type = setup_ai_service()
    
    try:
        # 创建ASR+AI实例
        asr_ai = ChineseASRWithAI(ai_type)
        
        # 显示使用说明
        print(f"\n📖 使用说明：")
        print("1. 🎤 确保麦克风正常工作")
        print("2. 🗣️ 程序会提示您开始说话")
        print("3. 🇨🇳 请说清楚的中文")
        print("4. 🤖 AI会回复您的话并显示在控制台")
        print("5. 🔄 可以连续对话")
        
        # 选择模式
        print(f"\n🎯 请选择模式：")
        print("1. 单次对话")
        print("2. 连续对话")
        
        choice = input("请输入选择（1或2）：").strip()
        
        if choice == '1':
            asr_ai.run_conversation()
        elif choice == '2':
            asr_ai.run_continuous_conversation()
        else:
            print("❌ 无效选择，执行单次对话")
            asr_ai.run_conversation()
            
    except Exception as e:
        print(f"❌ 程序执行过程中发生错误：{e}")
    
    print("\n👋 程序结束")


if __name__ == '__main__':
    main()
