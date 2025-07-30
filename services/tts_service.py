"""
TTS语音合成服务 - 策略模式实现
支持多种TTS服务：pyttsx3、Google TTS、Azure TTS
"""

import os
import time
import threading
from abc import ABC, abstractmethod
from typing import Optional
from utils.config_manager import ConfigManager


class TTSServiceInterface(ABC):
    """TTS服务接口"""
    
    @abstractmethod
    def speak(self, text: str, async_play: bool = True) -> bool:
        """
        文本转语音播放
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
            
        Returns:
            是否成功
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
    
    @abstractmethod
    def stop_speaking(self):
        """停止当前播放"""
        pass
    
    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        """是否正在播放"""
        pass


class PyttsxTTSService(TTSServiceInterface):
    """pyttsx3 TTS服务"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化pyttsx3 TTS服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.engine = None
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        
        self._initialize_engine()
    
    def _initialize_engine(self):
        """初始化pyttsx3引擎"""
        try:
            import pyttsx3
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
    
    def speak(self, text: str, async_play: bool = True) -> bool:
        """
        使用pyttsx3进行语音合成
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
            
        Returns:
            是否成功
        """
        if not self.engine or not text.strip():
            return False
        
        def _speak():
            with self._speaking_lock:
                try:
                    print(f"🔊 正在播放语音：{text[:20]}...")
                    self._is_speaking = True
                    self.engine.say(text)
                    self.engine.runAndWait()
                    
                    # TTS完成后的等待时间
                    wait_time = self.config.get_float('TTS_SETTINGS', 'tts_completion_wait', 0.5)
                    time.sleep(wait_time)
                    
                    self._is_speaking = False
                    return True
                except Exception as e:
                    print(f"❌ TTS播放失败：{e}")
                    self._is_speaking = False
                    return False
        
        if async_play:
            thread = threading.Thread(target=_speak)
            thread.daemon = True
            thread.start()
            return True
        else:
            return _speak()
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return "pyttsx3"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.engine is not None
    
    def stop_speaking(self):
        """停止当前播放"""
        if self.engine:
            try:
                self.engine.stop()
                self._is_speaking = False
            except:
                pass
    
    @property
    def is_speaking(self) -> bool:
        """是否正在播放"""
        return self._is_speaking
    
    def set_voice_properties(self, rate: int = None, volume: float = None):
        """
        设置语音属性
        
        Args:
            rate: 语速
            volume: 音量 (0.0-1.0)
        """
        if not self.engine:
            return
        
        if rate is not None:
            self.engine.setProperty('rate', rate)
            print(f"🔧 语速设置为：{rate}")
        
        if volume is not None:
            self.engine.setProperty('volume', volume)
            print(f"🔧 音量设置为：{volume}")
    
    def list_voices(self) -> list:
        """列出可用的语音"""
        if not self.engine:
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            return [{"id": voice.id, "name": voice.name} for voice in voices]
        except:
            return []


class GoogleTTSService(TTSServiceInterface):
    """Google TTS服务"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化Google TTS服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
    
    def speak(self, text: str, async_play: bool = True) -> bool:
        """
        使用Google TTS进行语音合成
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
            
        Returns:
            是否成功
        """
        if not text.strip():
            return False
        
        def _speak():
            with self._speaking_lock:
                try:
                    from gtts import gTTS
                    import pygame
                    import io
                    
                    print(f"🌐 正在使用Google TTS生成语音...")
                    self._is_speaking = True
                    
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
                    
                    # TTS完成后的等待时间
                    wait_time = self.config.get_float('TTS_SETTINGS', 'tts_completion_wait', 0.5)
                    time.sleep(wait_time)
                    
                    self._is_speaking = False
                    print("✅ Google TTS播放完成")
                    return True
                    
                except ImportError:
                    print("❌ 缺少gtts或pygame库，请安装：pip install gtts pygame")
                    self._is_speaking = False
                    return False
                except Exception as e:
                    print(f"❌ Google TTS失败：{e}")
                    self._is_speaking = False
                    return False
        
        if async_play:
            thread = threading.Thread(target=_speak)
            thread.daemon = True
            thread.start()
            return True
        else:
            return _speak()
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return "Google TTS"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            import gtts
            import pygame
            return True
        except ImportError:
            return False
    
    def stop_speaking(self):
        """停止当前播放"""
        try:
            import pygame
            pygame.mixer.music.stop()
            self._is_speaking = False
        except:
            pass
    
    @property
    def is_speaking(self) -> bool:
        """是否正在播放"""
        return self._is_speaking


class AzureTTSService(TTSServiceInterface):
    """Azure TTS服务"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化Azure TTS服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.speech_key = os.getenv('AZURE_SPEECH_KEY')
        self.service_region = os.getenv('AZURE_SPEECH_REGION', 'eastus')
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
    
    def speak(self, text: str, async_play: bool = True) -> bool:
        """
        使用Azure TTS进行语音合成
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
            
        Returns:
            是否成功
        """
        if not text.strip() or not self.speech_key:
            return False
        
        def _speak():
            with self._speaking_lock:
                try:
                    import azure.cognitiveservices.speech as speechsdk
                    
                    # 配置语音服务
                    speech_config = speechsdk.SpeechConfig(
                        subscription=self.speech_key, 
                        region=self.service_region
                    )
                    speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"
                    
                    # 创建合成器
                    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
                    
                    print(f"🌐 正在使用Azure TTS生成语音...")
                    self._is_speaking = True
                    
                    # 合成语音
                    result = synthesizer.speak_text_async(text).get()
                    
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        # TTS完成后的等待时间
                        wait_time = self.config.get_float('TTS_SETTINGS', 'tts_completion_wait', 0.5)
                        time.sleep(wait_time)
                        
                        self._is_speaking = False
                        print("✅ Azure TTS播放完成")
                        return True
                    else:
                        print(f"❌ Azure TTS失败：{result.reason}")
                        self._is_speaking = False
                        return False
                        
                except ImportError:
                    print("❌ 缺少azure-cognitiveservices-speech库")
                    self._is_speaking = False
                    return False
                except Exception as e:
                    print(f"❌ Azure TTS失败：{e}")
                    self._is_speaking = False
                    return False
        
        if async_play:
            thread = threading.Thread(target=_speak)
            thread.daemon = True
            thread.start()
            return True
        else:
            return _speak()
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return "Azure TTS"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.speech_key:
            return False
        
        try:
            import azure.cognitiveservices.speech
            return True
        except ImportError:
            return False
    
    def stop_speaking(self):
        """停止当前播放"""
        # Azure TTS没有直接的停止方法，通过标记来处理
        self._is_speaking = False
    
    @property
    def is_speaking(self) -> bool:
        """是否正在播放"""
        return self._is_speaking


class TTSServiceWithFallback:
    """带有回退机制的TTS服务"""
    
    def __init__(self, primary_service: TTSServiceInterface, fallback_service: TTSServiceInterface):
        """
        初始化带回退的TTS服务
        
        Args:
            primary_service: 主要TTS服务
            fallback_service: 回退TTS服务
        """
        self.primary_service = primary_service
        self.fallback_service = fallback_service
    
    def speak(self, text: str, async_play: bool = True) -> bool:
        """
        文本转语音播放（带回退机制）
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
            
        Returns:
            是否成功
        """
        # 尝试主要服务
        if self.primary_service.is_available():
            success = self.primary_service.speak(text, async_play)
            if success:
                return True
        
        # 回退到备选服务
        print(f"🔄 {self.primary_service.get_service_name()}不可用，使用{self.fallback_service.get_service_name()}...")
        return self.fallback_service.speak(text, async_play)
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"{self.primary_service.get_service_name()} → {self.fallback_service.get_service_name()}"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.primary_service.is_available() or self.fallback_service.is_available()
    
    def stop_speaking(self):
        """停止当前播放"""
        self.primary_service.stop_speaking()
        self.fallback_service.stop_speaking()
    
    @property
    def is_speaking(self) -> bool:
        """是否正在播放"""
        return self.primary_service.is_speaking or self.fallback_service.is_speaking


class TTSServiceFactory:
    """TTS服务工厂 - 工厂模式"""
    
    @staticmethod
    def create_service(service_type: str, config_manager: ConfigManager) -> TTSServiceInterface:
        """
        创建TTS服务实例
        
        Args:
            service_type: 服务类型 ('pyttsx3', 'gtts', 'azure')
            config_manager: 配置管理器
            
        Returns:
            TTS服务实例
        """
        if service_type == "pyttsx3":
            return PyttsxTTSService(config_manager)
        elif service_type == "gtts":
            return GoogleTTSService(config_manager)
        elif service_type == "azure":
            return AzureTTSService(config_manager)
        else:
            raise ValueError(f"不支持的TTS服务类型：{service_type}")
    
    @staticmethod
    def create_service_with_fallback(
        primary_type: str, 
        config_manager: ConfigManager,
        fallback_type: str = "pyttsx3"
    ) -> TTSServiceWithFallback:
        """
        创建带回退机制的TTS服务
        
        Args:
            primary_type: 主要服务类型
            config_manager: 配置管理器
            fallback_type: 回退服务类型，默认为pyttsx3
            
        Returns:
            带回退机制的TTS服务
        """
        primary_service = TTSServiceFactory.create_service(primary_type, config_manager)
        fallback_service = TTSServiceFactory.create_service(fallback_type, config_manager)
        
        return TTSServiceWithFallback(primary_service, fallback_service)
    
    @staticmethod
    def get_available_services() -> list:
        """获取可用的服务类型列表"""
        return ["pyttsx3", "gtts", "azure"]
    
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
            "pyttsx3": "Windows内置，免费",
            "gtts": "在线，免费但需网络",
            "azure": "高质量，需要API Key"
        }
        
        return descriptions.get(service_type, "未知服务") 