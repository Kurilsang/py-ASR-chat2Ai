#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文语音识别+AI对话+TTS合成演示程序
程序启动入口 - 使用模块化架构

项目结构：
├── main.py                     # 启动入口
├── config/config.ini          # 配置文件
├── utils/                     # 工具模块
├── services/                  # 服务模块
└── core/                      # 核心业务模块
"""

from utils import ConfigManager, MenuHelper, DependencyChecker
from services import (
    ASRService, 
    AIServiceFactory, 
    TTSServiceFactory, 
    VoiceActivityDetector
)
from core import ConversationManager


def main():
    """主函数 - 应用程序入口"""
    try:
        # 显示程序头部
        MenuHelper.print_header()
        
        # 1. 环境检查
        if not DependencyChecker.comprehensive_check():
            return
        
        # 2. 初始化配置管理器（单例模式）
        config_manager = ConfigManager()
        
        # 3. 用户选择服务配置
        ai_type = MenuHelper.select_ai_service()
        tts_type, enable_tts = MenuHelper.select_tts_service()
        
        # 4. 初始化服务
        print("\n🔧 初始化系统服务...")
        
        # 初始化ASR服务
        print("🎤 初始化语音识别服务...")
        asr_service = ASRService(config_manager)
        
        # 初始化AI服务（带回退机制）
        print("🤖 初始化AI对话服务...")
        ai_service = AIServiceFactory.create_service_with_fallback(
            ai_type, config_manager, fallback_type="simple"
        )
        
        # 初始化TTS服务（可选）
        tts_service = None
        if enable_tts:
            print("🔊 初始化TTS语音合成服务...")
            tts_service = TTSServiceFactory.create_service_with_fallback(
                tts_type, config_manager, fallback_type="pyttsx3"
            )
        
        # 初始化VAD服务
        print("🎯 初始化语音活动检测服务...")
        vad_service = VoiceActivityDetector(config_manager)
        
        # 5. 创建对话管理器
        print("🎯 初始化对话管理器...")
        conversation_manager = ConversationManager(
            config_manager=config_manager,
            asr_service=asr_service,
            ai_service=ai_service,
            tts_service=tts_service,
            vad_service=vad_service
        )
        
        # 6. 显示使用说明
        MenuHelper.print_usage_guide(enable_tts)
        
        # 7. 服务测试（可选）
        if MenuHelper.confirm_action("是否进行服务测试"):
            conversation_manager.test_all_services()
        
        # 8. 选择对话模式并运行
        mode = MenuHelper.select_conversation_mode()
        
        print(f"\n🚀 启动对话系统...")
        conversation_manager.print_service_info()
        
        # 运行对话
        stats = {}
        if mode == "single":
            success = conversation_manager.run_single_conversation()
            if success:
                print("✅ 单次对话完成")
        elif mode == "smart_continuous":
            stats = conversation_manager.run_smart_continuous_conversation()
        elif mode == "manual_continuous":
            stats = conversation_manager.run_manual_continuous_conversation()
        
        # 9. 显示统计信息
        if stats:
            MenuHelper.show_separator()
            conversation_manager.print_conversation_stats()
        
        print("\n👋 程序结束，感谢使用！")
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        MenuHelper.show_error_message(f"程序运行时发生未预期错误：{e}")
        print("\n💡 建议检查配置文件和依赖包是否正确安装")
    
    # 程序结束前的清理
    try:
        # 可以在这里添加清理代码
        pass
    except:
        pass


def show_help():
    """显示帮助信息"""
    help_text = """
🎙️ 中文语音识别+AI对话+TTS合成演示程序

功能特性：
- 🎤 智能语音识别 (ASR)
- 🤖 多种AI对话服务 (简单AI/Ollama/OpenAI)
- 🔊 多种语音合成 (pyttsx3/Google TTS/Azure TTS)
- 🎯 智能语音活动检测 (VAD)
- 🔄 连续对话支持
- ⚙️ 灵活配置管理

使用方法：
1. 确保麦克风正常工作
2. 运行程序：python main.py
3. 按提示选择服务和模式
4. 开始语音对话

配置文件：config/config.ini
依赖安装：pip install -r requirements.txt

项目地址：https://github.com/your-repo/py-ASR-demo
"""
    print(help_text)


def show_version():
    """显示版本信息"""
    version_info = """
🎙️ 中文语音识别+AI对话+TTS合成演示程序
版本：2.0.0
作者：AI Assistant
更新日期：2024-12-19

主要更新：
- ✨ 重构为模块化架构
- 🏭 采用工厂模式和策略模式
- 🔧 单例配置管理器
- 📊 完善的统计和监控
- 🎯 智能语音活动检测
- 🔄 自动回退机制
"""
    print(version_info)


if __name__ == '__main__':
    import sys
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['--help', '-h', 'help']:
            show_help()
        elif arg in ['--version', '-v', 'version']:
            show_version()
        else:
            print(f"❌ 未知参数：{arg}")
            print("使用 --help 查看帮助信息")
    else:
        # 正常启动程序
        main()
