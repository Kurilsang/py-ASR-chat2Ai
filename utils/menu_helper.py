"""
菜单工具 - 处理用户界面交互和菜单选择
"""

import os
from typing import Dict, List, Tuple, Any


class MenuHelper:
    """菜单工具类"""
    
    @staticmethod
    def print_header():
        """打印程序头部信息"""
        print("🎙️ 中文语音识别+AI对话+TTS合成演示程序")
        print("🔧 支持智能语音检测和自动连续对话")
        print("⚡ 现已支持Whisper高精度语音识别")
        print("=" * 60)
    
    @staticmethod
    def print_usage_guide(enable_tts: bool = True):
        """打印使用说明"""
        print("\n📖 使用说明：")
        print("1. 🎤 确保麦克风正常工作")
        print("2. 🎯 智能语音检测已启用")
        print("3. 🗣️ 直接说话，程序自动检测开始和结束")
        print("4. 🤖 AI会回复您的话并显示在控制台")
        if enable_tts:
            print("5. 🔊 AI回复会通过语音播放")
        print("6. 🔄 支持智能连续对话（无需按键）")
    
    @staticmethod
    def select_asr_service() -> str:
        """选择ASR语音识别服务"""
        print("\n🎤 选择ASR语音识别服务：")
        options = {
            "1": ("传统ASR", "traditional", "基于Google/PocketSphinx，快速启动"),
            "2": ("Whisper ASR", "whisper", "OpenAI Whisper，高精度识别")
        }
        
        for key, (name, _, desc) in options.items():
            print(f"{key}. {name} ({desc})")
        
        choice = input("请选择（1或2）：").strip()
        
        if choice in options:
            name, asr_type, _ = options[choice]
            print(f"\n💡 选择了{name}")
            
            if choice == "2":
                MenuHelper._show_whisper_guide()
                
            return asr_type
        else:
            print("❌ 无效选择，默认使用传统ASR")
            return "traditional"
    
    @staticmethod
    def _show_whisper_guide():
        """显示Whisper使用指南"""
        print("\n📋 Whisper ASR使用说明：")
        print("1. 本地模式: pip install openai-whisper")
        print("   - 自动下载模型（首次使用需要时间）")
        print("   - 支持CPU和GPU加速")
        print("   - 可离线使用")
        print("2. API模式: 需要OpenAI API Key")
        print("   - 在config.ini中配置api_key")
        print("   - 或设置环境变量OPENAI_API_KEY")
        print("💡 如果Whisper不可用会自动回退到传统ASR")
        print("⚡ 推荐使用base模型平衡速度和精度")
    
    @staticmethod
    def select_ai_service() -> str:
        """选择AI服务"""
        print("\n🤖 选择AI对话服务：")
        options = {
            "1": ("简单AI", "simple", "本地免费，立即可用"),
            "2": ("Ollama", "ollama", "本地免费，需要先安装"),
            "3": ("OpenAI GPT", "openai", "在线付费，需要API Key")
        }
        
        for key, (name, _, desc) in options.items():
            print(f"{key}. {name} ({desc})")
        
        choice = input("请选择（1、2或3）：").strip()
        
        if choice in options:
            name, ai_type, _ = options[choice]
            print(f"\n💡 选择了{name}")
            
            if choice == "2":
                MenuHelper._show_ollama_guide()
            elif choice == "3":
                MenuHelper._show_openai_guide()
                
            return ai_type
        else:
            print("❌ 无效选择，默认使用简单AI")
            return "simple"
    
    @staticmethod
    def _show_ollama_guide():
        """显示Ollama使用指南"""
        print("\n📋 Ollama使用说明：")
        print("1. 访问 https://ollama.ai 下载安装Ollama")
        print("2. 运行: ollama pull qwen2:0.5b  (下载中文模型)")
        print("3. 确保Ollama服务正在运行")
        print("💡 如果连接失败会自动回退到简单AI")
    
    @staticmethod
    def _show_openai_guide():
        """显示OpenAI使用指南"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("\n⚠️ 需要设置OpenAI API Key:")
            print("set OPENAI_API_KEY=your_api_key_here  (Windows)")
            print("export OPENAI_API_KEY=your_api_key_here  (Linux/Mac)")
        print("💡 如果连接失败会自动回退到简单AI")
    
    @staticmethod
    def select_tts_service() -> Tuple[str, bool]:
        """选择TTS服务"""
        print("\n🔊 选择TTS语音合成服务：")
        options = {
            "1": ("pyttsx3", "pyttsx3", True, "Windows内置，免费"),
            "2": ("Google TTS", "gtts", True, "在线，免费但需网络"),
            "3": ("Azure TTS", "azure", True, "高质量，需要API Key"),
            "4": ("关闭TTS", "none", False, "仅文字回复")
        }
        
        for key, (name, _, _, desc) in options.items():
            print(f"{key}. {name} ({desc})")
        
        choice = input("请选择（1、2、3或4）：").strip()
        
        if choice in options:
            name, tts_type, enable_tts, _ = options[choice]
            print(f"\n💡 选择了{name}")
            
            if choice == "2":
                print("需要安装: pip install gtts pygame")
            elif choice == "3":
                print("需要设置AZURE_SPEECH_KEY环境变量")
                print("安装: pip install azure-cognitiveservices-speech")
            elif choice == "4":
                print("TTS已关闭，仅显示文字回复")
                
            return tts_type, enable_tts
        else:
            print("❌ 无效选择，默认使用pyttsx3")
            return "pyttsx3", True
    
    @staticmethod
    def select_conversation_mode() -> str:
        """选择对话模式"""
        print("\n🎯 请选择模式：")
        options = {
            "1": ("单次对话", "single"),
            "2": ("智能连续对话", "smart_continuous", " (推荐)"),
            "3": ("手动连续对话", "manual_continuous")
        }
        
        for key, option in options.items():
            name = option[0]
            extra = option[2] if len(option) > 2 else ""
            print(f"{key}. {name}{extra}")
        
        choice = input("请输入选择（1、2或3）：").strip()
        
        if choice in options:
            return options[choice][1]
        else:
            print("❌ 无效选择，执行智能连续对话")
            return "smart_continuous"
    
    @staticmethod
    def show_conversation_stats(conversation_count: int, duration: float):
        """显示对话统计信息"""
        print(f"📊 对话统计：共 {conversation_count} 轮，持续时间 {duration:.1f} 秒")
    
    @staticmethod
    def show_success_message(message: str):
        """显示成功消息"""
        print(f"✅ {message}")
    
    @staticmethod
    def show_error_message(message: str):
        """显示错误消息"""
        print(f"❌ {message}")
    
    @staticmethod
    def show_warning_message(message: str):
        """显示警告消息"""
        print(f"⚠️ {message}")
    
    @staticmethod  
    def show_info_message(message: str):
        """显示信息消息"""
        print(f"💡 {message}")
    
    @staticmethod
    def show_progress_message(message: str):
        """显示进度消息"""
        print(f"🔄 {message}")
    
    @staticmethod
    def confirm_action(message: str) -> bool:
        """确认操作"""
        response = input(f"❓ {message} (y/n): ").strip().lower()
        return response in ['y', 'yes', '是', '确定']
    
    @staticmethod
    def get_user_input(prompt: str, default: str = "") -> str:
        """获取用户输入"""
        if default:
            full_prompt = f"{prompt} (默认: {default}): "
        else:
            full_prompt = f"{prompt}: "
        
        user_input = input(full_prompt).strip()
        return user_input if user_input else default
    
    @staticmethod
    def show_separator(char: str = "=", length: int = 60):
        """显示分隔线"""
        print(char * length)
    
    @staticmethod
    def clear_screen():
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def pause(message: str = "按任意键继续..."):
        """暂停等待用户输入"""
        input(message) 