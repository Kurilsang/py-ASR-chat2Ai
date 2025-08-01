"""
ASR服务工厂
提供多种ASR服务的创建和管理
支持传统ASR和Whisper ASR，并提供回退机制
"""

from typing import Optional, Union
from utils.config_manager import ConfigManager
from .asr_service import ASRService
from .whisper_asr_service import WhisperASRService


class ASRServiceFactory:
    """ASR服务工厂"""
    
    SUPPORTED_SERVICES = {
        'traditional': {
            'name': '传统ASR (Google/PocketSphinx)',
            'class': ASRService,
            'description': '基于speech_recognition库的传统ASR服务，支持Google和离线识别'
        },
        'whisper': {
            'name': 'Whisper ASR',
            'class': WhisperASRService,
            'description': 'OpenAI Whisper高精度语音识别，支持本地模型和API调用'
        }
    }
    
    @classmethod
    def create_service(cls, service_type: str, config_manager: ConfigManager) -> Optional[Union[ASRService, WhisperASRService]]:
        """
        创建指定类型的ASR服务
        
        Args:
            service_type: 服务类型 ('traditional' 或 'whisper')
            config_manager: 配置管理器
            
        Returns:
            ASR服务实例，创建失败返回None
        """
        if service_type not in cls.SUPPORTED_SERVICES:
            print(f"❌ 不支持的ASR服务类型: {service_type}")
            print(f"   支持的类型: {', '.join(cls.SUPPORTED_SERVICES.keys())}")
            return None
        
        try:
            service_info = cls.SUPPORTED_SERVICES[service_type]
            service_class = service_info['class']
            
            print(f"🔧 创建{service_info['name']}...")
            service = service_class(config_manager)
            
            # 检查服务是否可用
            if hasattr(service, 'is_available') and not service.is_available():
                print(f"⚠️ {service_info['name']}不可用")
                return None
            
            print(f"✅ {service_info['name']}创建成功")
            return service
            
        except Exception as e:
            print(f"❌ 创建{service_type} ASR服务失败: {e}")
            return None
    
    @classmethod
    def create_service_with_fallback(cls, 
                                   primary_type: str, 
                                   config_manager: ConfigManager,
                                   fallback_type: str = 'traditional') -> Optional[Union[ASRService, WhisperASRService]]:
        """
        创建ASR服务（带回退机制）
        
        Args:
            primary_type: 首选服务类型
            config_manager: 配置管理器
            fallback_type: 回退服务类型
            
        Returns:
            ASR服务实例
        """
        print(f"\n🏭 ASR服务工厂启动...")
        print(f"   首选服务: {primary_type}")
        print(f"   回退服务: {fallback_type}")
        
        # 尝试创建首选服务
        service = cls.create_service(primary_type, config_manager)
        if service:
            print(f"✅ 使用首选ASR服务: {primary_type}")
            return service
        
        # 首选服务失败，尝试回退服务
        if fallback_type != primary_type:
            print(f"\n🔄 首选服务失败，尝试回退服务...")
            service = cls.create_service(fallback_type, config_manager)
            if service:
                print(f"✅ 使用回退ASR服务: {fallback_type}")
                return service
        
        print(f"❌ 所有ASR服务都不可用")
        return None
    
    @classmethod
    def get_available_services(cls, config_manager: ConfigManager) -> dict:
        """
        获取可用的ASR服务列表
        
        Args:
            config_manager: 配置管理器
            
        Returns:
            可用服务的字典
        """
        available_services = {}
        
        for service_type, service_info in cls.SUPPORTED_SERVICES.items():
            try:
                # 快速检查服务是否可用（不完全初始化）
                if service_type == 'whisper':
                    # 检查Whisper依赖
                    try:
                        import whisper
                        available = True
                    except ImportError:
                        available = False
                else:
                    # 传统ASR通常都可用
                    available = True
                
                if available:
                    available_services[service_type] = service_info
                    
            except Exception:
                continue
        
        return available_services
    
    @classmethod
    def test_service(cls, service_type: str, config_manager: ConfigManager) -> bool:
        """
        测试指定ASR服务
        
        Args:
            service_type: 服务类型
            config_manager: 配置管理器
            
        Returns:
            是否测试成功
        """
        print(f"\n🧪 测试{service_type} ASR服务...")
        
        service = cls.create_service(service_type, config_manager)
        if not service:
            print(f"❌ {service_type} ASR服务创建失败")
            return False
        
        try:
            # 调用服务的测试方法
            if hasattr(service, 'test_recognition'):
                return service.test_recognition()
            elif hasattr(service, 'test_microphone'):
                return service.test_microphone()
            else:
                print(f"⚠️ {service_type} ASR服务不支持测试")
                return True
                
        except Exception as e:
            print(f"❌ {service_type} ASR服务测试失败: {e}")
            return False
    
    @classmethod
    def print_supported_services(cls):
        """打印支持的ASR服务信息"""
        print("\n🎤 支持的ASR服务:")
        print("=" * 50)
        
        for service_type, service_info in cls.SUPPORTED_SERVICES.items():
            print(f"\n📌 {service_type.upper()}")
            print(f"   名称: {service_info['name']}")
            print(f"   描述: {service_info['description']}")
    
    @classmethod
    def print_service_comparison(cls):
        """打印服务对比信息"""
        print("\n📊 ASR服务对比:")
        print("=" * 60)
        
        print("\n🔸 传统ASR (Traditional)")
        print("   优势: 快速启动、轻量级、稳定性好")
        print("   劣势: 识别精度一般、依赖网络")
        print("   适用: 快速原型、网络环境好的场景")
        
        print("\n🔸 Whisper ASR")
        print("   优势: 识别精度高、多语言支持、可离线使用")
        print("   劣势: 模型较大、首次加载慢、需要更多计算资源")
        print("   适用: 高精度要求、多语言场景、离线使用")


class ASRServiceManager:
    """ASR服务管理器 - 管理多个ASR服务实例"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化ASR服务管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config = config_manager
        self.services = {}
        self.current_service = None
        
        # 从配置文件读取默认服务
        self.default_service_type = self.config.get('ASR_SETTINGS', 'default_service', 'traditional')
    
    def add_service(self, service_type: str, service_instance) -> bool:
        """
        添加ASR服务实例
        
        Args:
            service_type: 服务类型
            service_instance: 服务实例
            
        Returns:
            是否添加成功
        """
        try:
            self.services[service_type] = service_instance
            print(f"✅ ASR服务已添加: {service_type}")
            
            # 如果是默认服务，设置为当前服务
            if service_type == self.default_service_type:
                self.current_service = service_instance
            
            return True
        except Exception as e:
            print(f"❌ 添加ASR服务失败: {e}")
            return False
    
    def switch_service(self, service_type: str) -> bool:
        """
        切换到指定的ASR服务
        
        Args:
            service_type: 目标服务类型
            
        Returns:
            是否切换成功
        """
        if service_type not in self.services:
            print(f"❌ ASR服务不存在: {service_type}")
            return False
        
        try:
            self.current_service = self.services[service_type]
            print(f"✅ 已切换到ASR服务: {service_type}")
            return True
        except Exception as e:
            print(f"❌ 切换ASR服务失败: {e}")
            return False
    
    def get_current_service(self):
        """获取当前ASR服务"""
        return self.current_service
    
    def get_available_services(self) -> list:
        """获取可用的服务类型列表"""
        return list(self.services.keys())
    
    def print_service_status(self):
        """打印服务状态"""
        print(f"\n🔧 ASR服务管理器状态:")
        print(f"   默认服务: {self.default_service_type}")
        print(f"   当前服务: {type(self.current_service).__name__ if self.current_service else 'None'}")
        print(f"   可用服务: {', '.join(self.services.keys())}")
        
        # 显示各服务的详细状态
        for service_type, service in self.services.items():
            status = "✅ 可用" if (hasattr(service, 'is_available') and service.is_available()) else "❌ 不可用"
            service_name = service.get_service_name() if hasattr(service, 'get_service_name') else service_type
            print(f"   [{service_type}] {service_name}: {status}") 