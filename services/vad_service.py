"""
VAD语音活动检测服务
负责智能语音检测和录音控制
"""

import speech_recognition as sr
import time
from typing import Optional
from utils.config_manager import ConfigManager


class VoiceActivityDetector:
    """语音活动检测器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化VAD服务
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self._load_config()
        
        print(f"🎯 VAD配置: 静音超时={self.silence_timeout}秒, 最小语音={self.min_speech_duration}秒")
    
    def _load_config(self):
        """从配置文件加载VAD参数"""
        self.silence_timeout = self.config.get_float('VOICE_DETECTION', 'silence_timeout', 2.0)
        self.min_speech_duration = self.config.get_float('VOICE_DETECTION', 'min_speech_duration', 0.5)
        self.max_recording_duration = self.config.get_float('VOICE_DETECTION', 'max_recording_duration', 30.0)
        self.energy_multiplier = self.config.get_float('VOICE_DETECTION', 'energy_threshold_multiplier', 1.5)
    
    def detect_speech_automatically(self, recognizer: sr.Recognizer, microphone: sr.Microphone) -> Optional[sr.AudioData]:
        """
        自动检测语音并录音（无限等待模式）
        
        Args:
            recognizer: 语音识别器
            microphone: 麦克风
            
        Returns:
            录制的音频数据
        """
        try:
            print("🎤 正在监听语音...")
            print("💡 请开始说话，程序会自动检测语音开始和结束")
            
            with microphone as source:
                # 动态调整噪音阈值
                ambient_energy = recognizer.energy_threshold
                adjusted_threshold = ambient_energy * self.energy_multiplier
                recognizer.energy_threshold = adjusted_threshold
                
                print(f"🔧 能量阈值调整为: {adjusted_threshold:.0f}")
                
                # 等待语音开始，然后自动录制
                audio = recognizer.listen(
                    source,
                    timeout=None,  # 无限等待语音开始
                    phrase_time_limit=self.max_recording_duration
                )
                
                print("✅ 语音录制完成！")
                return audio
                
        except sr.WaitTimeoutError:
            print("❌ 录音超时")
            return None
        except Exception as e:
            print(f"❌ 录音失败：{e}")
            return None
    
    def listen_for_speech_with_vad(self, recognizer: sr.Recognizer, microphone: sr.Microphone) -> Optional[sr.AudioData]:
        """
        使用VAD进行智能语音检测（循环等待模式）
        
        Args:
            recognizer: 语音识别器
            microphone: 麦克风
            
        Returns:
            录制的音频数据
        """
        try:
            print("🎯 智能语音检测已启动...")
            
            with microphone as source:
                # 动态调整噪音阈值
                self._adjust_energy_threshold(recognizer)
                
                # 循环检测语音
                while True:
                    try:
                        print("👂 等待语音输入...")
                        
                        # 监听语音，自动检测开始和结束
                        audio = recognizer.listen(
                            source,
                            timeout=1,  # 1秒超时，然后继续循环
                            phrase_time_limit=self.max_recording_duration
                        )
                        
                        print("✅ 检测到语音，录制完成！")
                        return audio
                        
                    except sr.WaitTimeoutError:
                        # 1秒内没有语音，继续监听
                        continue
                        
        except KeyboardInterrupt:
            print("\n❌ 用户中断语音检测")
            return None
        except Exception as e:
            print(f"❌ 语音检测失败：{e}")
            return None
    
    def listen_with_timeout(self, recognizer: sr.Recognizer, microphone: sr.Microphone, 
                           timeout: float = 10.0) -> Optional[sr.AudioData]:
        """
        带超时的语音监听
        
        Args:
            recognizer: 语音识别器
            microphone: 麦克风
            timeout: 超时时间（秒）
            
        Returns:
            录制的音频数据
        """
        try:
            print(f"🎤 监听语音（超时：{timeout}秒）...")
            
            with microphone as source:
                self._adjust_energy_threshold(recognizer)
                
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=self.max_recording_duration
                )
                
                print("✅ 语音录制完成！")
                return audio
                
        except sr.WaitTimeoutError:
            print(f"❌ 语音检测超时（{timeout}秒）")
            return None
        except Exception as e:
            print(f"❌ 语音检测失败：{e}")
            return None
    
    def _adjust_energy_threshold(self, recognizer: sr.Recognizer):
        """
        调整能量阈值
        
        Args:
            recognizer: 语音识别器
        """
        try:
            ambient_energy = recognizer.energy_threshold
            adjusted_threshold = ambient_energy * self.energy_multiplier
            recognizer.energy_threshold = adjusted_threshold
            print(f"🔧 能量阈值: {ambient_energy:.0f} → {adjusted_threshold:.0f}")
        except Exception as e:
            print(f"⚠️ 能量阈值调整失败：{e}")
    
    def calibrate_noise_level(self, recognizer: sr.Recognizer, microphone: sr.Microphone, 
                             duration: float = 2.0) -> float:
        """
        校准环境噪音水平
        
        Args:
            recognizer: 语音识别器
            microphone: 麦克风
            duration: 校准持续时间（秒）
            
        Returns:
            校准后的能量阈值
        """
        try:
            print(f"🔧 校准环境噪音（持续{duration}秒）...")
            
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=duration)
            
            threshold = recognizer.energy_threshold
            print(f"✅ 环境噪音校准完成，阈值: {threshold:.0f}")
            return threshold
            
        except Exception as e:
            print(f"❌ 环境噪音校准失败：{e}")
            return recognizer.energy_threshold
    
    def test_voice_detection(self, recognizer: sr.Recognizer, microphone: sr.Microphone) -> bool:
        """
        测试语音检测功能
        
        Args:
            recognizer: 语音识别器
            microphone: 麦克风
            
        Returns:
            测试是否成功
        """
        try:
            print("🧪 测试语音检测功能...")
            print("请在3秒内说话...")
            
            with microphone as source:
                audio = recognizer.listen(source, timeout=3, phrase_time_limit=2)
            
            print("✅ 语音检测测试成功")
            return True
            
        except sr.WaitTimeoutError:
            print("⚠️ 未检测到语音，可能需要调整麦克风或阈值")
            return False
        except Exception as e:
            print(f"❌ 语音检测测试失败：{e}")
            return False
    
    def get_optimal_threshold(self, recognizer: sr.Recognizer, microphone: sr.Microphone) -> float:
        """
        获取最优能量阈值
        
        Args:
            recognizer: 语音识别器
            microphone: 麦克风
            
        Returns:
            最优阈值
        """
        try:
            # 多次采样获取平均值
            thresholds = []
            
            print("🔧 计算最优能量阈值...")
            
            for i in range(3):
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    thresholds.append(recognizer.energy_threshold)
                time.sleep(0.5)
            
            optimal_threshold = sum(thresholds) / len(thresholds) * self.energy_multiplier
            print(f"✅ 计算得出最优阈值: {optimal_threshold:.0f}")
            
            return optimal_threshold
            
        except Exception as e:
            print(f"❌ 最优阈值计算失败：{e}")
            return recognizer.energy_threshold * self.energy_multiplier
    
    def set_detection_sensitivity(self, sensitivity: str):
        """
        设置检测灵敏度
        
        Args:
            sensitivity: 灵敏度级别 ('low', 'medium', 'high')
        """
        sensitivity_map = {
            'low': 2.0,      # 低灵敏度，需要更大的声音
            'medium': 1.5,   # 中等灵敏度（默认）
            'high': 1.2      # 高灵敏度，更容易触发
        }
        
        if sensitivity in sensitivity_map:
            self.energy_multiplier = sensitivity_map[sensitivity]
            print(f"🔧 检测灵敏度设置为: {sensitivity} (倍数: {self.energy_multiplier})")
        else:
            print(f"❌ 无效的灵敏度级别: {sensitivity}")
    
    def get_detection_stats(self) -> dict:
        """
        获取检测统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "silence_timeout": self.silence_timeout,
            "min_speech_duration": self.min_speech_duration,
            "max_recording_duration": self.max_recording_duration,
            "energy_multiplier": self.energy_multiplier
        }
    
    def print_detection_stats(self):
        """打印检测统计信息"""
        stats = self.get_detection_stats()
        print("\n🎯 VAD检测配置：")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    
    def update_config(self, **kwargs):
        """
        更新VAD配置
        
        Args:
            **kwargs: 配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                print(f"🔧 更新配置 {key}: {value}")
            else:
                print(f"⚠️ 未知配置项: {key}")
    
    def enable_dynamic_threshold(self, recognizer: sr.Recognizer, enable: bool = True):
        """
        启用/禁用动态阈值调整
        
        Args:
            recognizer: 语音识别器
            enable: 是否启用
        """
        recognizer.dynamic_energy_threshold = enable
        status = "启用" if enable else "禁用"
        print(f"🔧 动态阈值调整已{status}")
    
    def set_pause_threshold(self, recognizer: sr.Recognizer, threshold: float = 0.8):
        """
        设置暂停检测阈值
        
        Args:
            recognizer: 语音识别器
            threshold: 暂停阈值（秒）
        """
        recognizer.pause_threshold = threshold
        print(f"🔧 暂停检测阈值设置为: {threshold}秒") 