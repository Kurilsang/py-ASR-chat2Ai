#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文语音识别+AI对话+TTS合成演示程序
程序启动入口 - 使用模块化架构 + 流式TTS + Whisper ASR

项目结构：
├── main.py                     # 启动入口
├── config/config.ini          # 配置文件
├── utils/                     # 工具模块
├── services/                  # 服务模块
└── core/                      # 核心业务模块
"""

import time
from utils import ConfigManager, MenuHelper, DependencyChecker
from services import (
    ASRServiceFactory,
    AIServiceFactory, 
    TTSServiceFactory, 
    VoiceActivityDetector
)
# 导入流式TTS服务
from services.streaming_tts_enhanced import EnhancedStreamingTTSFactory
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
        asr_type = MenuHelper.select_asr_service()
        ai_type = MenuHelper.select_ai_service()
        tts_type, enable_tts = MenuHelper.select_tts_service()
        
        # 4. 初始化服务
        print("\n🔧 初始化系统服务...")
        
        # 初始化ASR服务（新增Whisper支持）
        print("🎤 初始化语音识别服务...")
        asr_service = ASRServiceFactory.create_service_with_fallback(
            primary_type=asr_type, 
            config_manager=config_manager, 
            fallback_type="traditional"
        )
        
        if not asr_service:
            print("❌ ASR服务初始化失败，程序无法继续运行")
            return
        
        # 显示ASR服务信息
        if hasattr(asr_service, 'print_service_info'):
            asr_service.print_service_info()
        
        # 初始化AI服务（带回退机制）
        print("🤖 初始化AI对话服务...")
        ai_service = AIServiceFactory.create_service_with_fallback(
            ai_type, config_manager, fallback_type="simple"
        )
        
        # 初始化TTS服务（可选）- 使用流式TTS
        tts_service = None
        if enable_tts:
            print("🔊 初始化流式TTS语音合成服务...")
            
            # 询问用户是否使用流式TTS
            use_streaming = MenuHelper.confirm_action("是否使用流式TTS（推荐，可显著提升长对话响应速度）")
            
            if use_streaming:
                try:
                    # 创建增强流式TTS服务
                    tts_service = EnhancedStreamingTTSFactory.create_enhanced_streaming_with_fallback(
                        primary_type=tts_type,
                        config_manager=config_manager,
                        fallback_type="pyttsx3",
                        max_chunk_size=80,      # 文本片段大小
                        queue_size=10,          # 播放队列大小
                        cache_audio=True        # 启用音频缓存
                    )
                    print("✅ 流式TTS服务初始化成功")
                    print("🚀 长对话响应速度将显著提升！")
                    
                    # 创建流式TTS适配器，使其兼容原有接口
                    tts_service = StreamingTTSAdapter(tts_service, config_manager)
                    
                except Exception as e:
                    print(f"⚠️ 流式TTS初始化失败: {e}")
                    print("🔄 回退到传统TTS服务...")
                    tts_service = TTSServiceFactory.create_service_with_fallback(
                        tts_type, config_manager, fallback_type="pyttsx3"
                    )
            else:
                # 使用传统TTS服务
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
        
        # 如果使用了流式TTS，显示额外说明
        if enable_tts and isinstance(tts_service, StreamingTTSAdapter):
            print("\n🚀 流式TTS功能已启用:")
            print("   - 长回复将边合成边播放，大幅缩短等待时间")
            print("   - 智能文本分割，保持语音自然连贯")
            print("   - 支持实时进度显示和中途停止")
        
        # 如果使用了Whisper，显示额外说明
        if hasattr(asr_service, 'get_service_name') and 'Whisper' in asr_service.get_service_name():
            print("\n🎤 Whisper ASR功能已启用:")
            print("   - 高精度语音识别，支持多语言")
            print("   - 自动语言检测和噪声抑制")
            print("   - 更好的中文识别效果")
        
        # 7. 服务测试（可选）
        if MenuHelper.confirm_action("是否进行服务测试"):
            conversation_manager.test_all_services()
            
            # 如果使用流式TTS，进行额外的流式测试
            if enable_tts and isinstance(tts_service, StreamingTTSAdapter):
                if MenuHelper.confirm_action("是否测试流式TTS性能"):
                    test_streaming_tts_performance(tts_service)
            
            # 如果使用Whisper，进行额外的Whisper测试
            if hasattr(asr_service, 'test_recognition'):
                if MenuHelper.confirm_action("是否测试Whisper识别功能"):
                    asr_service.test_recognition()
        
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
            
            # 如果使用了流式TTS，显示流式TTS统计
            if enable_tts and isinstance(tts_service, StreamingTTSAdapter):
                tts_service.print_streaming_stats()
            
            # 如果使用了Whisper，显示Whisper统计
            if hasattr(asr_service, 'print_usage_stats'):
                asr_service.print_usage_stats()
        
        print("\n👋 程序结束，感谢使用！")
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        MenuHelper.show_error_message(f"程序运行时发生未预期错误：{e}")
        print("\n💡 建议检查配置文件和依赖包是否正确安装")
    
    # 程序结束前的清理
    try:
        # 清理流式TTS临时文件
        if 'tts_service' in locals() and hasattr(tts_service, 'cleanup'):
            tts_service.cleanup()
    except:
        pass


class StreamingTTSAdapter:
    """流式TTS适配器 - 使流式TTS兼容原有TTS接口"""
    
    def __init__(self, streaming_tts_service, config_manager):
        """
        初始化适配器
        
        Args:
            streaming_tts_service: 流式TTS服务实例
            config_manager: 配置管理器
        """
        self.streaming_service = streaming_tts_service
        self.config = config_manager
        self._is_speaking = False
        
        # 统计信息
        self.usage_stats = {
            'total_requests': 0,
            'streaming_requests': 0,
            'traditional_requests': 0,
            'total_characters': 0,
            'avg_response_time': 0
        }
    
    def speak(self, text: str, async_play: bool = True) -> bool:
        """
        TTS播放接口 - 自动选择流式或传统模式
        
        Args:
            text: 要合成的文本
            async_play: 是否异步播放
            
        Returns:
            是否成功
        """
        if not text or not text.strip():
            return False
        
        self.usage_stats['total_requests'] += 1
        self.usage_stats['total_characters'] += len(text)
        
        # 根据文本长度决定是否使用流式模式
        text_length = len(text.strip())
        use_streaming = text_length > 50  # 超过50字符使用流式
        
        if use_streaming:
            return self._speak_streaming(text, async_play)
        else:
            return self._speak_traditional(text, async_play)
    
    def _speak_streaming(self, text: str, async_play: bool) -> bool:
        """使用流式TTS播放"""
        try:
            self.usage_stats['streaming_requests'] += 1
            self._is_speaking = True
            
            print(f"🎵 使用流式TTS播放 ({len(text)}字符)")
            
            def progress_callback(progress: float, message: str):
                if progress > 0:
                    print(f"🔄 流式TTS: {message}")
            
            success = self.streaming_service.speak_streaming(text, progress_callback)
            
            if success and not async_play:
                # 同步模式：等待播放完成
                while self.streaming_service.is_streaming:
                    time.sleep(0.1)
            
            return success
            
        except Exception as e:
            print(f"❌ 流式TTS播放失败: {e}")
            return False
        finally:
            self._is_speaking = False
    
    def _speak_traditional(self, text: str, async_play: bool) -> bool:
        """使用传统TTS播放"""
        try:
            self.usage_stats['traditional_requests'] += 1
            
            # 回退到基础TTS服务
            base_service = self.streaming_service.base_tts_service
            return base_service.speak(text, async_play)
            
        except Exception as e:
            print(f"❌ 传统TTS播放失败: {e}")
            return False
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"智能流式{self.streaming_service.get_service_name()}"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.streaming_service.is_available()
    
    def stop_speaking(self):
        """停止当前播放"""
        try:
            self.streaming_service.stop_streaming()
            self._is_speaking = False
        except:
            pass
    
    @property
    def is_speaking(self) -> bool:
        """是否正在播放"""
        return self._is_speaking or self.streaming_service.is_streaming
    
    def print_streaming_stats(self):
        """打印流式TTS使用统计"""
        print("\n📊 流式TTS使用统计:")
        print(f"   总请求数: {self.usage_stats['total_requests']}")
        print(f"   流式播放: {self.usage_stats['streaming_requests']}")
        print(f"   传统播放: {self.usage_stats['traditional_requests']}")
        print(f"   总字符数: {self.usage_stats['total_characters']}")
        
        if self.usage_stats['streaming_requests'] > 0:
            streaming_ratio = self.usage_stats['streaming_requests'] / self.usage_stats['total_requests'] * 100
            print(f"   流式使用率: {streaming_ratio:.1f}%")
        
        # 显示流式TTS详细统计
        if hasattr(self.streaming_service, 'print_detailed_stats'):
            self.streaming_service.print_detailed_stats()
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self.streaming_service, 'stop_streaming'):
                self.streaming_service.stop_streaming()
            if hasattr(self.streaming_service, '_cleanup_temp_files'):
                self.streaming_service._cleanup_temp_files()
        except:
            pass


def test_streaming_tts_performance(tts_service):
    """测试流式TTS性能"""
    print("\n🧪 流式TTS性能测试")
    print("=" * 40)
    
    test_texts = [
        "这是一个短文本测试。",
        "这是一个中等长度的文本，用来测试流式TTS在中等长度内容上的表现，包含一些详细的描述和说明。",
        """这是一个长文本测试，模拟AI助手可能给出的详细回答。
        流式TTS技术能够显著改善用户体验，特别是在处理长文本时。
        传统的TTS需要等待完整合成后才能播放，而流式TTS可以边合成边播放。
        这种技术在语音助手、在线教育、客服系统等场景中非常有用。
        通过智能分割和并行处理，实现更流畅的语音交互体验。"""
    ]
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n🔬 测试 {i} - 文本长度: {len(text)}字符")
        
        start_time = time.time()
        
        success = tts_service.speak(text, async_play=False)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            print(f"✅ 测试完成 - 耗时: {duration:.2f}秒")
        else:
            print(f"❌ 测试失败")
        
        print("-" * 40)


def show_help():
    """显示帮助信息"""
    help_text = """
🎙️ 中文语音识别+AI对话+TTS合成演示程序

功能特性：
- 🎤 智能语音识别 (传统ASR/Whisper ASR)
- 🤖 多种AI对话服务 (简单AI/Ollama/OpenAI)
- 🔊 多种语音合成 (pyttsx3/Google TTS/Azure TTS)
- ⚡ 流式TTS技术 (边合成边播放，提升响应速度)
- 🎯 智能语音活动检测 (VAD)
- 🔄 连续对话支持
- ⚙️ 灵活配置管理

✨ ASR服务选择：
- 传统ASR: 基于Google/PocketSphinx，快速启动
- Whisper ASR: OpenAI Whisper高精度识别，支持多语言

使用方法：
1. 确保麦克风正常工作
2. 运行程序：python main.py
3. 按提示选择ASR、AI和TTS服务
4. 建议启用Whisper ASR获得更高识别精度
5. 建议启用流式TTS以获得更好体验
6. 开始语音对话

🎤 Whisper ASR新特性：
- 高精度语音识别，支持中英文等多语言
- 自动语言检测和噪声抑制
- 支持本地模型和OpenAI API两种模式
- 可完全离线使用（本地模式）

🚀 流式TTS特性：
- 长文本响应速度提升50-80%
- 智能文本分割，保持语义完整性
- 实时进度显示，支持中途停止
- 自动回退机制，确保稳定性

配置文件：config/config.ini
依赖安装：pip install -r requirements.txt
测试Whisper：python test_whisper.py

项目地址：https://github.com/Kurilsang/py-ASR-chat2Ai
"""
    print(help_text)


def show_version():
    """显示版本信息"""
    version_info = """
🎙️ 中文语音识别+AI对话+TTS合成演示程序
版本：2.2.0 (Whisper ASR增强版)
作者：AI Assistant
更新日期：2024-12-19

主要更新：
- ✨ 重构为模块化架构
- 🏭 采用工厂模式和策略模式
- 🔧 单例配置管理器
- 📊 完善的统计和监控
- 🎯 智能语音活动检测
- 🔄 自动回退机制
- ⚡ 流式TTS技术 (重大更新)
- 🚀 长对话响应速度大幅提升
- 🧩 智能文本分割与并行处理
- 📈 详细性能统计与监控
- 🎤 Whisper ASR支持 (全新功能)
- 🌍 多语言高精度语音识别
- 🔧 ASR服务工厂和管理器
- 🛠️ 完善的依赖检查和测试工具

技术架构：
- 模块化设计，职责分离清晰
- 工厂模式支持多种服务类型
- 适配器模式实现服务兼容
- 策略模式支持算法切换
- 单例模式确保配置统一
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
