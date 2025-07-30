"""
配置管理器 - 单例模式
负责加载和管理应用程序配置
"""

import os
import configparser
from typing import Optional


class ConfigManager:
    """配置管理器 - 单例模式"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[configparser.ConfigParser] = None
    _config_path: Optional[str] = None
    
    def __new__(cls, config_path: str = "config/config.ini"):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize(config_path)
        return cls._instance
    
    def _initialize(self, config_path: str):
        """初始化配置管理器"""
        self._config_path = config_path
        self._config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self._config_path):
                self._config.read(self._config_path, encoding='utf-8')
                print(f"✅ 配置文件加载成功：{self._config_path}")
            else:
                print(f"⚠️ 配置文件不存在，使用默认配置：{self._config_path}")
                self._create_default_config()
        except Exception as e:
            print(f"❌ 配置文件加载失败：{e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self._config['VOICE_DETECTION'] = {
            'silence_timeout': '2.0',
            'min_speech_duration': '0.5',
            'energy_threshold_multiplier': '1.5',
            'max_recording_duration': '30'
        }
        self._config['CONVERSATION'] = {
            'response_pause_time': '1.0',
            'auto_continuous_mode': 'true',
            'conversation_timeout': '300'
        }
        self._config['TTS_SETTINGS'] = {
            'tts_completion_wait': '0.5',
            'pause_detection_during_tts': 'true'
        }
        self._config['AUDIO_SETTINGS'] = {
            'sample_rate': '16000',
            'chunk_size': '4096',
            'channels': '1'
        }
    
    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return self._config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """获取布尔值配置"""
        try:
            return self._config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return self._config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def get_string(self, section: str, key: str, default: str = "") -> str:
        """获取字符串配置"""
        try:
            return self._config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def set_value(self, section: str, key: str, value: str):
        """设置配置值"""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            
            with open(self._config_path, 'w', encoding='utf-8') as configfile:
                self._config.write(configfile)
            print(f"✅ 配置文件保存成功：{self._config_path}")
        except Exception as e:
            print(f"❌ 配置文件保存失败：{e}")
    
    def reload_config(self):
        """重新加载配置文件"""
        self.load_config()
        print("🔄 配置文件已重新加载")
    
    @property
    def config_path(self) -> str:
        """获取配置文件路径"""
        return self._config_path
    
    def get_section_dict(self, section: str) -> dict:
        """获取整个配置节的字典"""
        try:
            return dict(self._config[section])
        except KeyError:
            return {}
    
    def has_section(self, section: str) -> bool:
        """检查是否存在指定配置节"""
        return self._config.has_section(section)
    
    def has_option(self, section: str, key: str) -> bool:
        """检查是否存在指定配置项"""
        return self._config.has_option(section, key) 