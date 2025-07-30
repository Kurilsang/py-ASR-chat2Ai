"""
ASR语音识别服务
负责语音识别相关功能
"""

import speech_recognition as sr
from typing import Optional
from utils.config_manager import ConfigManager


class ASRService:
    """ASR语音识别服务"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化ASR服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # 调整环境噪音
        self._adjust_ambient_noise()
    
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
            return self._try_offline_recognition(audio_data)
        except Exception as e:
            print(f"❌ 识别过程中发生未知错误：{e}")
            return None
    
    def _try_offline_recognition(self, audio_data: sr.AudioData) -> Optional[str]:
        """
        尝试离线识别
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果文本
        """
        try:
            print("🔄 尝试使用离线识别...")
            text = self.recognizer.recognize_sphinx(audio_data, language='zh-CN')
            return text
        except Exception:
            print("❌ 离线识别也失败了")
            return None
    
    def recognize_english(self, audio_data: sr.AudioData) -> Optional[str]:
        """
        识别英文语音
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果文本
        """
        try:
            print("🔍 正在识别英文语音...")
            text = self.recognizer.recognize_google(audio_data, language='en-US')
            return text
        except Exception as e:
            print(f"❌ 英文识别失败：{e}")
            return None
    
    def set_energy_threshold(self, threshold: float):
        """
        设置能量阈值
        
        Args:
            threshold: 能量阈值
        """
        self.recognizer.energy_threshold = threshold
        print(f"🔧 能量阈值设置为: {threshold}")
    
    def get_energy_threshold(self) -> float:
        """
        获取当前能量阈值
        
        Returns:
            当前能量阈值
        """
        return self.recognizer.energy_threshold
    
    def adjust_energy_threshold_multiplier(self, multiplier: float = None):
        """
        调整能量阈值倍数
        
        Args:
            multiplier: 倍数，如果为None则从配置文件读取
        """
        if multiplier is None:
            multiplier = self.config.get_float('VOICE_DETECTION', 'energy_threshold_multiplier', 1.5)
        
        current_threshold = self.recognizer.energy_threshold
        new_threshold = current_threshold * multiplier
        self.recognizer.energy_threshold = new_threshold
        
        print(f"🔧 能量阈值从 {current_threshold:.0f} 调整为 {new_threshold:.0f}")
    
    def test_microphone(self) -> bool:
        """
        测试麦克风是否正常工作
        
        Returns:
            是否正常工作
        """
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
    
    def get_microphone_info(self) -> dict:
        """
        获取麦克风信息
        
        Returns:
            麦克风信息字典
        """
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            
            info = {
                "device_count": pa.get_device_count(),
                "default_input_device": pa.get_default_input_device_info(),
                "input_devices": []
            }
            
            # 获取所有输入设备
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    info["input_devices"].append({
                        "index": i,
                        "name": device_info['name'],
                        "channels": device_info['maxInputChannels'],
                        "sample_rate": device_info['defaultSampleRate']
                    })
            
            pa.terminate()
            return info
            
        except Exception as e:
            print(f"❌ 获取麦克风信息失败：{e}")
            return {}
    
    def print_microphone_info(self):
        """打印麦克风信息"""
        info = self.get_microphone_info()
        
        if not info:
            print("❌ 无法获取麦克风信息")
            return
        
        print(f"\n🎤 麦克风信息：")
        print(f"   设备总数: {info['device_count']}")
        
        if 'default_input_device' in info:
            default = info['default_input_device']
            print(f"   默认输入设备: {default['name']}")
        
        if info['input_devices']:
            print(f"   可用输入设备:")
            for device in info['input_devices']:
                print(f"     [{device['index']}] {device['name']} "
                      f"({device['channels']}通道, {device['sample_rate']:.0f}Hz)")
        else:
            print("   ❌ 未找到可用的输入设备")
    
    def calibrate_for_ambient_noise(self, duration: float = 2.0):
        """
        重新校准环境噪音
        
        Args:
            duration: 校准持续时间（秒）
        """
        print(f"🔧 重新校准环境噪音（持续{duration}秒）...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            print(f"✅ 环境噪音校准完成，新阈值: {self.recognizer.energy_threshold:.0f}")
        except Exception as e:
            print(f"❌ 环境噪音校准失败：{e}")
    
    def get_recognizer_config(self) -> dict:
        """
        获取识别器配置
        
        Returns:
            识别器配置信息
        """
        return {
            "energy_threshold": self.recognizer.energy_threshold,
            "dynamic_energy_threshold": self.recognizer.dynamic_energy_threshold,
            "dynamic_energy_adjustment_damping": self.recognizer.dynamic_energy_adjustment_damping,
            "dynamic_energy_ratio": self.recognizer.dynamic_energy_ratio,
            "pause_threshold": self.recognizer.pause_threshold,
            "operation_timeout": self.recognizer.operation_timeout,
            "phrase_threshold": self.recognizer.phrase_threshold,
            "non_speaking_duration": self.recognizer.non_speaking_duration
        }
    
    def print_recognizer_config(self):
        """打印识别器配置"""
        config = self.get_recognizer_config()
        print("\n🔧 识别器配置：")
        for key, value in config.items():
            print(f"   {key}: {value}") 