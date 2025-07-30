"""
依赖检查工具 - 检查和验证所需的Python包
"""

import sys
import subprocess
from typing import List, Dict, Tuple
import importlib.util


class DependencyChecker:
    """依赖检查器"""
    
    # 基础依赖包
    BASIC_DEPENDENCIES = {
        'speech_recognition': 'SpeechRecognition',
        'pyaudio': 'pyaudio', 
        'requests': 'requests',
        'pyttsx3': 'pyttsx3'
    }
    
    # 可选依赖包
    OPTIONAL_DEPENDENCIES = {
        'gtts': 'gtts',           # Google TTS
        'pygame': 'pygame',       # 音频播放
        'azure.cognitiveservices.speech': 'azure-cognitiveservices-speech'  # Azure TTS
    }
    
    @classmethod
    def check_basic_dependencies(cls) -> Tuple[bool, List[str]]:
        """
        检查基础依赖包
        
        Returns:
            Tuple[bool, List[str]]: (是否全部满足, 缺失的包列表)
        """
        missing_packages = []
        
        for module_name, package_name in cls.BASIC_DEPENDENCIES.items():
            if not cls._is_package_installed(module_name):
                missing_packages.append(package_name)
        
        if missing_packages:
            print(f"❌ 缺少基础依赖包：{', '.join(missing_packages)}")
            print("\n📦 请安装基础依赖包：")
            print(f"pip install {' '.join(missing_packages)}")
            return False, missing_packages
        else:
            print("✅ 基础依赖包检查通过")
            return True, []
    
    @classmethod
    def check_optional_dependencies(cls) -> Dict[str, bool]:
        """
        检查可选依赖包
        
        Returns:
            Dict[str, bool]: 每个可选包的安装状态
        """
        status = {}
        
        for module_name, package_name in cls.OPTIONAL_DEPENDENCIES.items():
            is_installed = cls._is_package_installed(module_name)
            status[package_name] = is_installed
            
            if is_installed:
                print(f"✅ 可选包 {package_name} 已安装")
            else:
                print(f"⚠️ 可选包 {package_name} 未安装")
        
        return status
    
    @classmethod
    def _is_package_installed(cls, module_name: str) -> bool:
        """
        检查单个包是否已安装
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否已安装
        """
        try:
            # 尝试导入模块
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError, AttributeError):
            return False
    
    @classmethod
    def check_python_version(cls, min_version: Tuple[int, int] = (3, 8)) -> bool:
        """
        检查Python版本
        
        Args:
            min_version: 最低版本要求
            
        Returns:
            bool: 是否满足版本要求
        """
        current_version = sys.version_info[:2]
        
        if current_version >= min_version:
            print(f"✅ Python版本检查通过：{sys.version.split()[0]}")
            return True
        else:
            print(f"❌ Python版本过低：当前 {sys.version.split()[0]}，需要 {min_version[0]}.{min_version[1]}+")
            return False
    
    @classmethod
    def install_package(cls, package_name: str) -> bool:
        """
        尝试安装包
        
        Args:
            package_name: 包名称
            
        Returns:
            bool: 是否安装成功
        """
        try:
            print(f"🔧 正在安装 {package_name}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ {package_name} 安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ {package_name} 安装失败：{e}")
            return False
        except Exception as e:
            print(f"❌ 安装 {package_name} 时发生未知错误：{e}")
            return False
    
    @classmethod
    def auto_install_missing_basic_dependencies(cls) -> bool:
        """
        自动安装缺失的基础依赖包
        
        Returns:
            bool: 是否全部安装成功
        """
        success, missing_packages = cls.check_basic_dependencies()
        
        if success:
            return True
        
        print("\n🤖 尝试自动安装缺失的基础依赖包...")
        
        all_success = True
        for package in missing_packages:
            if not cls.install_package(package):
                all_success = False
        
        if all_success:
            print("✅ 所有基础依赖包安装完成")
            # 重新检查
            success, _ = cls.check_basic_dependencies()
            return success
        else:
            print("❌ 部分依赖包安装失败，请手动安装")
            return False
    
    @classmethod
    def get_system_info(cls) -> Dict[str, str]:
        """
        获取系统信息
        
        Returns:
            Dict[str, str]: 系统信息
        """
        import platform
        
        return {
            "Python版本": sys.version.split()[0],
            "操作系统": platform.system(),
            "系统版本": platform.release(),
            "架构": platform.machine(),
            "处理器": platform.processor()
        }
    
    @classmethod
    def print_system_info(cls):
        """打印系统信息"""
        print("\n🖥️ 系统信息：")
        info = cls.get_system_info()
        for key, value in info.items():
            print(f"   {key}: {value}")
    
    @classmethod
    def comprehensive_check(cls) -> bool:
        """
        综合检查
        
        Returns:
            bool: 是否满足运行要求
        """
        print("🔍 开始综合依赖检查...")
        
        # 1. 检查Python版本
        python_ok = cls.check_python_version()
        
        # 2. 检查基础依赖
        basic_ok, _ = cls.check_basic_dependencies()
        
        # 3. 检查可选依赖
        optional_status = cls.check_optional_dependencies()
        
        # 4. 打印系统信息
        cls.print_system_info()
        
        # 总结
        if python_ok and basic_ok:
            print("\n✅ 系统环境检查通过，可以正常运行程序")
            
            # 给出可选包建议
            missing_optional = [pkg for pkg, installed in optional_status.items() if not installed]
            if missing_optional:
                print(f"\n💡 建议安装可选包以获得更好体验：")
                print(f"pip install {' '.join(missing_optional)}")
            
            return True
        else:
            print("\n❌ 系统环境检查未通过，请解决上述问题后重试")
            return False
    
    @classmethod
    def check_microphone_access(cls) -> bool:
        """
        检查麦克风访问权限
        
        Returns:
            bool: 是否可以访问麦克风
        """
        try:
            import pyaudio
            
            # 尝试初始化PyAudio
            pa = pyaudio.PyAudio()
            
            # 检查是否有输入设备
            input_devices = []
            for i in range(pa.get_device_count()):
                device_info = pa.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append(device_info['name'])
            
            pa.terminate()
            
            if input_devices:
                print(f"✅ 检测到 {len(input_devices)} 个音频输入设备")
                print(f"   主要设备: {input_devices[0]}")
                return True
            else:
                print("❌ 未检测到可用的音频输入设备")
                return False
                
        except Exception as e:
            print(f"❌ 麦克风访问检查失败：{e}")
            return False
    
    @classmethod
    def check_network_connectivity(cls) -> bool:
        """
        检查网络连接
        
        Returns:
            bool: 是否有网络连接
        """
        try:
            import requests
            
            # 测试连接到Google（用于ASR和TTS）
            response = requests.get("https://www.google.com", timeout=5)
            if response.status_code == 200:
                print("✅ 网络连接正常")
                return True
            else:
                print("⚠️ 网络连接异常")
                return False
                
        except Exception as e:
            print(f"⚠️ 网络连接检查失败：{e}")
            return False 