"""
Whisper ASR语音识别服务
基于OpenAI Whisper模型的高精度语音识别
支持本地模型和API调用两种模式
"""

import os
import tempfile
import wave
import numpy as np
from typing import Optional, Union
import speech_recognition as sr
from utils.config_manager import ConfigManager


class WhisperASRService:
    """基于OpenAI Whisper的ASR语音识别服务"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化Whisper ASR服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # 获取配置
        self.model_size = self.config.get_string('WHISPER_SETTINGS', 'model_size', 'base')
        self.use_api = self.config.get_bool('WHISPER_SETTINGS', 'use_api', False)
        self.api_key = self.config.get_string('WHISPER_SETTINGS', 'api_key', '')
        self.language = self.config.get_string('WHISPER_SETTINGS', 'language', 'zh')
        self.device = self.config.get_string('WHISPER_SETTINGS', 'device', 'auto')
        
        # 初始化Whisper
        self.whisper_model = None
        self._initialize_whisper()
        
        # 调整环境噪音
        self._adjust_ambient_noise()
        
        # 统计信息
        self.usage_stats = {
            'total_recognitions': 0,
            'successful_recognitions': 0,
            'api_calls': 0,
            'local_calls': 0,
            'avg_confidence': 0.0
        }
    
    def _initialize_whisper(self):
        """初始化Whisper模型"""
        try:
            if self.use_api and self.api_key:
                print("🔧 配置Whisper API模式...")
                # 设置OpenAI API Key
                os.environ['OPENAI_API_KEY'] = self.api_key
                print("✅ Whisper API配置完成")
            else:
                print(f"🔧 加载Whisper本地模型: {self.model_size}")
                import whisper
                
                # 自动选择设备
                if self.device == 'auto':
                    import torch
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                    print(f"🔧 自动选择设备: {device}")
                else:
                    device = self.device
                
                self.whisper_model = whisper.load_model(self.model_size, device=device)
                print(f"✅ Whisper本地模型加载完成 (模型: {self.model_size}, 设备: {device})")
                
        except ImportError:
            print("❌ Whisper库未安装，请运行: pip install openai-whisper")
            raise
        except Exception as e:
            print(f"❌ Whisper初始化失败: {e}")
            raise
    
    def _adjust_ambient_noise(self):
        """调整环境噪音"""
        print("🔧 正在调整环境噪音，请保持安静...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ 环境噪音调整完成！")
        except Exception as e:
            print(f"⚠️ 环境噪音调整失败：{e}")
    
    def recognize_chinese(self, audio_data: sr.AudioData) -> Optional[str]:
        """
        使用Whisper识别中文语音
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果文本，如果识别失败返回None
        """
        return self._recognize_with_whisper(audio_data, language='zh')
    
    def recognize_english(self, audio_data: sr.AudioData) -> Optional[str]:
        """
        使用Whisper识别英文语音
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果文本，如果识别失败返回None
        """
        return self._recognize_with_whisper(audio_data, language='en')
    
    def recognize_auto(self, audio_data: sr.AudioData) -> Optional[str]:
        """
        使用Whisper自动识别语音（自动检测语言）
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果文本，如果识别失败返回None
        """
        return self._recognize_with_whisper(audio_data, language=None)
    
    def _recognize_with_whisper(self, audio_data: sr.AudioData, language: Optional[str] = None) -> Optional[str]:
        """
        使用Whisper进行语音识别
        
        Args:
            audio_data: 音频数据
            language: 指定语言代码，None表示自动检测
            
        Returns:
            识别结果文本
        """
        self.usage_stats['total_recognitions'] += 1
        
        try:
            if self.use_api and self.api_key:
                return self._recognize_with_api(audio_data, language)
            else:
                return self._recognize_with_local_model(audio_data, language)
                
        except Exception as e:
            print(f"❌ Whisper识别失败: {e}")
            return None
    
    def _recognize_with_api(self, audio_data: sr.AudioData, language: Optional[str]) -> Optional[str]:
        """使用Whisper API进行识别"""
        try:
            print("🌐 正在使用Whisper API识别语音...")
            self.usage_stats['api_calls'] += 1
            
            # 将音频数据保存为临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # 转换音频格式
                audio_wav = audio_data.get_wav_data()
                temp_file.write(audio_wav)
            
            # 使用speech_recognition的whisper API支持
            if language:
                result = self.recognizer.recognize_whisper_api(
                    audio_data, 
                    api_key=self.api_key,
                    language=language
                )
            else:
                result = self.recognizer.recognize_whisper_api(
                    audio_data, 
                    api_key=self.api_key
                )
            
            # 清理临时文件
            try:
                os.unlink(temp_filename)
            except:
                pass
            
            if result:
                self.usage_stats['successful_recognitions'] += 1
                print(f"✅ API识别成功: {result}")
                return result
            else:
                print("❌ API识别结果为空")
                return None
                
        except Exception as e:
            print(f"❌ Whisper API识别失败: {e}")
            return None
    
    def _recognize_with_local_model(self, audio_data: sr.AudioData, language: Optional[str]) -> Optional[str]:
        """使用本地Whisper模型进行识别"""
        try:
            print(f"🎤 正在使用Whisper本地模型识别语音 (模型: {self.model_size})...")
            self.usage_stats['local_calls'] += 1
            
            # 将音频数据转换为numpy数组
            audio_wav = audio_data.get_wav_data()
            
            # 保存为临时wav文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                temp_file.write(audio_wav)
            
            # 使用Whisper进行转录
            transcribe_options = {}
            if language:
                transcribe_options['language'] = language
            
            result = self.whisper_model.transcribe(temp_filename, **transcribe_options)
            
            # 清理临时文件
            try:
                os.unlink(temp_filename)
            except:
                pass
            
            text = result.get('text', '').strip()
            
            if text:
                self.usage_stats['successful_recognitions'] += 1
                
                # 获取置信度信息（如果可用）
                segments = result.get('segments', [])
                if segments:
                    avg_confidence = sum(seg.get('no_speech_prob', 0) for seg in segments) / len(segments)
                    confidence = 1.0 - avg_confidence  # 转换为置信度
                    self.usage_stats['avg_confidence'] = (
                        (self.usage_stats['avg_confidence'] * (self.usage_stats['successful_recognitions'] - 1) + confidence) 
                        / self.usage_stats['successful_recognitions']
                    )
                
                # 显示识别的语言（如果检测到）
                detected_language = result.get('language', 'unknown')
                print(f"✅ 本地识别成功 (语言: {detected_language}): {text}")
                
                return text
            else:
                print("❌ 本地识别结果为空")
                return None
                
        except Exception as e:
            print(f"❌ Whisper本地识别失败: {e}")
            return None
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        if self.use_api:
            return f"WhisperAPI"
        else:
            return f"Whisper-{self.model_size}"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        try:
            if self.use_api:
                return bool(self.api_key)
            else:
                return self.whisper_model is not None
        except:
            return False
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        # Whisper支持的主要语言
        return [
            'zh', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'ru', 'pt', 
            'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'da', 'no'
        ]
    
    def test_recognition(self) -> bool:
        """
        测试识别功能
        
        Returns:
            是否测试成功
        """
        try:
            print("🧪 测试Whisper识别功能...")
            with self.microphone as source:
                print("请说一句话进行测试（5秒内）...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=3)
                
                result = self.recognize_auto(audio)
                if result:
                    print(f"✅ Whisper识别测试成功: {result}")
                    return True
                else:
                    print("❌ Whisper识别测试失败: 无识别结果")
                    return False
                    
        except sr.WaitTimeoutError:
            print("⚠️ 测试超时，未检测到语音")
            return False
        except Exception as e:
            print(f"❌ Whisper识别测试失败: {e}")
            return False
    
    def print_service_info(self):
        """打印服务信息"""
        print(f"\n🎤 Whisper ASR服务信息:")
        print(f"   服务名称: {self.get_service_name()}")
        print(f"   运行模式: {'API模式' if self.use_api else '本地模式'}")
        
        if not self.use_api:
            print(f"   模型大小: {self.model_size}")
            print(f"   设备: {self.device}")
        
        print(f"   默认语言: {self.language}")
        print(f"   支持语言: {', '.join(self.get_supported_languages()[:10])}...")
        print(f"   服务状态: {'✅ 可用' if self.is_available() else '❌ 不可用'}")
    
    def print_usage_stats(self):
        """打印使用统计"""
        print(f"\n📊 Whisper ASR使用统计:")
        print(f"   总识别次数: {self.usage_stats['total_recognitions']}")
        print(f"   成功识别次数: {self.usage_stats['successful_recognitions']}")
        
        if self.usage_stats['total_recognitions'] > 0:
            success_rate = (self.usage_stats['successful_recognitions'] / 
                          self.usage_stats['total_recognitions']) * 100
            print(f"   识别成功率: {success_rate:.1f}%")
        
        if self.use_api:
            print(f"   API调用次数: {self.usage_stats['api_calls']}")
        else:
            print(f"   本地调用次数: {self.usage_stats['local_calls']}")
            
        if self.usage_stats['avg_confidence'] > 0:
            print(f"   平均置信度: {self.usage_stats['avg_confidence']:.2f}")
    
    # 兼容原ASRService接口的方法
    def set_energy_threshold(self, threshold: float):
        """设置能量阈值"""
        self.recognizer.energy_threshold = threshold
        print(f"🔧 能量阈值设置为: {threshold}")
    
    def get_energy_threshold(self) -> float:
        """获取当前能量阈值"""
        return self.recognizer.energy_threshold
    
    def adjust_energy_threshold_multiplier(self, multiplier: float = None):
        """调整能量阈值倍数"""
        if multiplier is None:
            multiplier = self.config.get_float('VOICE_DETECTION', 'energy_threshold_multiplier', 1.5)
        
        current_threshold = self.recognizer.energy_threshold
        new_threshold = current_threshold * multiplier
        self.recognizer.energy_threshold = new_threshold
        
        print(f"🔧 能量阈值从 {current_threshold:.0f} 调整为 {new_threshold:.0f}")
    
    def test_microphone(self) -> bool:
        """测试麦克风是否正常工作"""
        try:
            print("🎤 测试麦克风...")
            with self.microphone as source:
                print("请说话进行测试...")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=2)
                print("✅ 麦克风测试成功")
                return True
        except sr.WaitTimeoutError:
            print("⚠️ 麦克风测试超时，可能没有检测到语音")
            return False
        except Exception as e:
            print(f"❌ 麦克风测试失败：{e}")
            return False
    
    def calibrate_for_ambient_noise(self, duration: float = 2.0):
        """重新校准环境噪音"""
        print(f"🔧 重新校准环境噪音（持续{duration}秒）...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            print(f"✅ 环境噪音校准完成，新阈值: {self.recognizer.energy_threshold:.0f}")
        except Exception as e:
            print(f"❌ 环境噪音校准失败：{e}") 