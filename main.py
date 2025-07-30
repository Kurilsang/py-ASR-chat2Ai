#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文语音识别+AI对话+TTS语音合成演示程序
使用speech_recognition库实现ASR，结合AI对话功能和TTS语音合成
"""

import speech_recognition as sr
import pyaudio
import time
import requests
import json
import os
import random
import pyttsx3
import threading
from typing import Optional


class TTSEngine:
    """文本转语音引擎类"""
    
    def __init__(self, tts_type="pyttsx3"):
        """
        初始化TTS引擎
        
        Args:
            tts_type: TTS类型，支持 "pyttsx3", "gtts", "azure"
        """
        self.tts_type = tts_type
        self.engine = None
        
        if tts_type == "pyttsx3":
            self.init_pyttsx3()
    
    def init_pyttsx3(self):
        """初始化pyttsx3引擎"""
        try:
            self.engine = pyttsx3.init()
            
            # 设置语音参数
            voices = self.engine.getProperty('voices')
            
            # 尝试选择中文语音
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            # 设置语速和音量
            self.engine.setProperty('rate', 200)    # 语速
            self.engine.setProperty('volume', 0.8)  # 音量
            
            print("✅ pyttsx3 TTS引擎初始化成功")
            
        except Exception as e:
            print(f"❌ pyttsx3初始化失败：{e}")
            self.engine = None
    
    def speak_with_pyttsx3(self, text: str):
        """使用pyttsx3进行语音合成"""
        if not self.engine:
            print("❌ TTS引擎未初始化")
            return False
        
        try:
            print(f"🔊 正在播放语音：{text[:20]}...")
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"❌ TTS播放失败：{e}")
            return False
    
    def speak_with_gtts(self, text: str):
        """使用Google TTS进行语音合成"""
        try:
            from gtts import gTTS
            import pygame
            import io
            
            print(f"🌐 正在使用Google TTS生成语音...")
            
            # 生成语音
            tts = gTTS(text=text, lang='zh-cn', slow=False)
            
            # 保存到内存
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # 播放音频
            pygame.mixer.init()
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            print("✅ Google TTS播放完成")
            return True
            
        except ImportError:
            print("❌ 缺少gtts或pygame库，请安装：pip install gtts pygame")
            return False
        except Exception as e:
            print(f"❌ Google TTS失败：{e}")
            return False
    
    def speak_with_azure(self, text: str):
        """使用Azure TTS进行语音合成"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # 需要Azure订阅密钥
            speech_key = os.getenv('AZURE_SPEECH_KEY')
            service_region = os.getenv('AZURE_SPEECH_REGION', 'eastus')
            
            if not speech_key:
                print("❌ 请设置AZURE_SPEECH_KEY环境变量")
                return False
            
            # 配置语音服务
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, 
                region=service_region
            )
            speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"
            
            # 创建合成器
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
            print(f"🌐 正在使用Azure TTS生成语音...")
            
            # 合成语音
            result = synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print("✅ Azure TTS播放完成")
                return True
            else:
                print(f"❌ Azure TTS失败：{result.reason}")
                return False
                
        except ImportError:
            print("❌ 缺少azure-cognitiveservices-speech库")
            return False
        except Exception as e:
            print(f"❌ Azure TTS失败：{e}")
            return False
    
    def speak(self, text: str, async_play: bool = True):
        """
        文本转语音播放
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
        """
        if not text or not text.strip():
            return False
        
        def _speak():
            success = False
            
            if self.tts_type == "pyttsx3":
                success = self.speak_with_pyttsx3(text)
            elif self.tts_type == "gtts":
                success = self.speak_with_gtts(text)
            elif self.tts_type == "azure":
                success = self.speak_with_azure(text)
            
            if not success:
                print("🔄 TTS失败，尝试使用pyttsx3备选方案...")
                # 如果当前不是pyttsx3，尝试初始化并使用pyttsx3
                if self.tts_type != "pyttsx3":
                    # 重新初始化pyttsx3作为备选
                    try:
                        if not self.engine:
                            print("🔧 正在初始化pyttsx3备选引擎...")
                            self.init_pyttsx3()
                        if self.engine:
                            self.speak_with_pyttsx3(text)
                        else:
                            print("❌ 备选pyttsx3引擎初始化失败")
                    except Exception as e:
                        print(f"❌ 备选TTS方案失败：{e}")
                else:
                    print("❌ pyttsx3引擎不可用")
        
        if async_play:
            # 异步播放，不阻塞程序
            thread = threading.Thread(target=_speak)
            thread.daemon = True
            thread.start()
            return True
        else:
            # 同步播放
            _speak()
            return True


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
            "默认": [
                "这是个很有趣的问题！",
                "我理解你的意思，让我想想",
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
        
        # 告别词检测
        farewells = ["再见", "拜拜", "回头见", "告别", "bye", "goodbye"]
        if any(farewell in message_lower for farewell in farewells):
            return random.choice(self.simple_responses["告别"])
        
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


class ChineseASRWithAIAndTTS:
    """中文语音识别+AI对话+TTS语音合成类"""
    
    def __init__(self, ai_type="simple", tts_type="pyttsx3", enable_tts=True):
        """初始化语音识别器、AI对话和TTS"""
        print("🎤 初始化语音识别系统...")
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.ai_chat = AIChat(ai_type)
        self.enable_tts = enable_tts
        
        # 初始化TTS
        if enable_tts:
            print("🔊 初始化TTS语音合成...")
            self.tts_engine = TTSEngine(tts_type)
        else:
            self.tts_engine = None
        
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
        """运行语音识别+AI对话+TTS"""
        print("\n" + "="*60)
        print("🗣️ 开始语音识别+AI对话+TTS合成")
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
        
        # 步骤6：TTS语音合成播放
        if self.enable_tts and self.tts_engine:
            self.tts_engine.speak(ai_response, async_play=True)
        
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
                    # 短暂暂停，等待TTS播放
                    time.sleep(2)
                    
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
    missing_packages = []
    
    try:
        import speech_recognition
    except ImportError:
        missing_packages.append("SpeechRecognition")
    
    try:
        import pyaudio
    except ImportError:
        missing_packages.append("pyaudio")
        
    try:
        import requests
    except ImportError:
        missing_packages.append("requests")
        
    try:
        import pyttsx3
    except ImportError:
        missing_packages.append("pyttsx3")
    
    if missing_packages:
        print(f"❌ 缺少依赖包：{', '.join(missing_packages)}")
        print("\n📦 请安装依赖包：")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    else:
        print("✅ 基本依赖包检查通过")
        return True


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


def setup_tts_service():
    """设置TTS服务"""
    print("\n🔊 选择TTS语音合成服务：")
    print("1. pyttsx3 (Windows内置，免费)")
    print("2. Google TTS (在线，免费但需网络)")
    print("3. Azure TTS (高质量，需要API Key)")
    print("4. 关闭TTS (仅文字回复)")
    
    choice = input("请选择（1、2、3或4）：").strip()
    
    if choice == '1':
        print("\n💡 使用pyttsx3：Windows内置TTS")
        return "pyttsx3", True
    elif choice == '2':
        print("\n💡 使用Google TTS：需要安装gtts和pygame")
        print("pip install gtts pygame")
        return "gtts", True
    elif choice == '3':
        print("\n💡 使用Azure TTS：需要设置AZURE_SPEECH_KEY")
        print("pip install azure-cognitiveservices-speech")
        return "azure", True
    elif choice == '4':
        print("\n💡 TTS已关闭，仅显示文字回复")
        return "none", False
    else:
        print("❌ 无效选择，默认使用pyttsx3")
        return "pyttsx3", True


def main():
    """主函数"""
    print("🎙️ 中文语音识别+AI对话+TTS合成演示程序")
    print("="*60)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 选择AI服务
    ai_type = setup_ai_service()
    
    # 选择TTS服务
    tts_type, enable_tts = setup_tts_service()
    
    try:
        # 创建ASR+AI+TTS实例
        asr_ai_tts = ChineseASRWithAIAndTTS(ai_type, tts_type, enable_tts)
        
        # 显示使用说明
        print(f"\n📖 使用说明：")
        print("1. 🎤 确保麦克风正常工作")
        print("2. 🗣️ 程序会提示您开始说话")
        print("3. 🇨🇳 请说清楚的中文")
        print("4. 🤖 AI会回复您的话并显示在控制台")
        if enable_tts:
            print("5. 🔊 AI回复会通过语音播放")
        print("6. 🔄 可以连续对话")
        
        # 选择模式
        print(f"\n🎯 请选择模式：")
        print("1. 单次对话")
        print("2. 连续对话")
        
        choice = input("请输入选择（1或2）：").strip()
        
        if choice == '1':
            asr_ai_tts.run_conversation()
        elif choice == '2':
            asr_ai_tts.run_continuous_conversation()
        else:
            print("❌ 无效选择，执行单次对话")
            asr_ai_tts.run_conversation()
            
    except Exception as e:
        print(f"❌ 程序执行过程中发生错误：{e}")
    
    print("\n👋 程序结束")


if __name__ == '__main__':
    main()
