"""
对话管理器 - 核心业务层
协调ASR、AI、TTS、VAD等服务完成完整的对话流程
"""

import time
from typing import Optional
from utils.config_manager import ConfigManager
from utils.menu_helper import MenuHelper
from services.asr_service import ASRService
from services.ai_service import AIServiceWithFallback
from services.tts_service import TTSServiceInterface
from services.vad_service import VoiceActivityDetector


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, 
                 config_manager: ConfigManager,
                 asr_service: ASRService,
                 ai_service: AIServiceWithFallback,
                 tts_service: Optional[TTSServiceInterface] = None,
                 vad_service: Optional[VoiceActivityDetector] = None):
        """
        初始化对话管理器
        
        Args:
            config_manager: 配置管理器
            asr_service: ASR语音识别服务
            ai_service: AI对话服务
            tts_service: TTS语音合成服务（可选）
            vad_service: VAD语音活动检测服务（可选）
        """
        self.config = config_manager
        self.asr_service = asr_service
        self.ai_service = ai_service
        self.tts_service = tts_service
        self.vad_service = vad_service
        
        # 对话统计
        self.conversation_count = 0
        self.start_time = None
        self.total_recognition_time = 0
        self.total_ai_response_time = 0
        self.total_tts_time = 0
        
        print("🎯 对话管理器初始化完成")
    
    def run_single_conversation(self) -> bool:
        """
        运行单次对话
        
        Returns:
            是否成功完成对话
        """
        print("\n" + "="*60)
        print("🗣️ 开始语音识别+AI对话+TTS合成")
        print("="*60)
        
        try:
            # 步骤1：语音录制和识别
            user_input = self._record_and_recognize()
            if not user_input:
                return False
            
            # 步骤2：显示用户输入
            print(f"\n👤 您说：{user_input}")
            
            # 步骤3：获取AI回复
            ai_response = self._get_ai_response(user_input)
            if not ai_response:
                return False
            
            # 步骤4：显示AI回复
            print(f"🤖 AI回复：{ai_response}")
            
            # 步骤5：TTS语音播放
            if self.tts_service:
                self._play_tts_response(ai_response)
            
            print("="*60)
            return True
            
        except KeyboardInterrupt:
            print("\n❌ 用户中断对话")
            return False
        except Exception as e:
            print(f"❌ 对话过程中发生错误：{e}")
            return False
    
    def run_smart_continuous_conversation(self) -> dict:
        """
        运行智能连续对话模式（无需手动交互）
        
        Returns:
            对话统计信息
        """
        print("\n🤖 进入智能连续对话模式")
        print("🎯 语音检测已启动，无需按回车")
        print("💡 说话会自动识别，静音会自动处理")
        print("⚠️ 按 Ctrl+C 可退出程序")
        
        self.start_time = time.time()
        timeout = self.config.get_float('CONVERSATION', 'conversation_timeout', 300)
        
        try:
            while True:
                # 检查对话超时
                if time.time() - self.start_time > timeout:
                    print(f"\n⏰ 对话超时（{timeout}秒），自动退出")
                    break
                
                print(f"\n🔄 第 {self.conversation_count + 1} 轮对话")
                
                # 等待TTS播放完成
                self._wait_for_tts_completion()
                
                # 运行一轮对话
                success = self.run_single_conversation()
                
                if success:
                    self.conversation_count += 1
                    
                    # 对话间隔
                    pause_time = self.config.get_float('CONVERSATION', 'response_pause_time', 1.0)
                    print(f"⏸️ 等待 {pause_time} 秒后继续...")
                    time.sleep(pause_time)
                else:
                    # 如果识别失败，稍作等待后继续
                    print("⏸️ 等待 2 秒后重试...")
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            print(f"\n\n👋 用户中断，共进行了 {self.conversation_count} 轮对话")
        except Exception as e:
            print(f"\n❌ 连续对话过程中发生错误：{e}")
        
        return self._get_conversation_stats()
    
    def run_manual_continuous_conversation(self) -> dict:
        """
        运行手动连续对话模式（需要按回车）
        
        Returns:
            对话统计信息
        """
        print("\n🔄 进入连续对话模式")
        print("💡 说'退出'、'结束'或按Ctrl+C可退出程序")
        
        self.start_time = time.time()
        
        try:
            while True:
                success = self.run_single_conversation()
                
                if success:
                    self.conversation_count += 1
                    
                    # 等待TTS播放完成
                    self._wait_for_tts_completion()
                    
                # 询问是否继续
                choice = input("\n⏭️ 按Enter继续对话，输入'quit'退出：").strip().lower()
                if choice in ['quit', 'q', '退出', '结束']:
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 程序被用户中断")
        except Exception as e:
            print(f"\n❌ 连续对话过程中发生错误：{e}")
        
        return self._get_conversation_stats()
    
    def _record_and_recognize(self) -> Optional[str]:
        """
        录制音频并进行语音识别
        
        Returns:
            识别结果文本
        """
        start_time = time.time()
        
        try:
            # 使用VAD进行智能录音
            if self.vad_service:
                audio_data = self.vad_service.listen_for_speech_with_vad(
                    self.asr_service.recognizer, 
                    self.asr_service.microphone
                )
            else:
                # 使用传统录音方式
                print("🎙️ 请开始说话...")
                with self.asr_service.microphone as source:
                    audio_data = self.asr_service.recognizer.listen(source, timeout=10)
            
            if not audio_data:
                return None
            
            # 语音识别
            recognition_start = time.time()
            result = self.asr_service.recognize_chinese(audio_data)
            recognition_time = time.time() - recognition_start
            
            self.total_recognition_time += recognition_time
            
            return result
            
        except Exception as e:
            print(f"❌ 录音和识别失败：{e}")
            return None
    
    def _get_ai_response(self, user_input: str) -> Optional[str]:
        """
        获取AI回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI回复内容
        """
        try:
            ai_start = time.time()
            response = self.ai_service.get_response(user_input)
            ai_time = time.time() - ai_start
            
            self.total_ai_response_time += ai_time
            
            return response
            
        except Exception as e:
            print(f"❌ AI回复获取失败：{e}")
            return None
    
    def _play_tts_response(self, text: str):
        """
        播放TTS回复
        
        Args:
            text: 要播放的文本
        """
        if not self.tts_service:
            return
        
        try:
            tts_start = time.time()
            
            # 同步播放，等待完成
            success = self.tts_service.speak(text, async_play=False)
            
            if success:
                tts_time = time.time() - tts_start
                self.total_tts_time += tts_time
            
        except Exception as e:
            print(f"❌ TTS播放失败：{e}")
    
    def _wait_for_tts_completion(self):
        """等待TTS播放完成"""
        if not self.tts_service:
            return
        
        # 检查TTS是否正在播放
        if hasattr(self.tts_service, 'is_speaking'):
            while self.tts_service.is_speaking:
                time.sleep(0.1)
    
    def _get_conversation_stats(self) -> dict:
        """
        获取对话统计信息
        
        Returns:
            统计信息字典
        """
        total_time = time.time() - self.start_time if self.start_time else 0
        
        stats = {
            "conversation_count": self.conversation_count,
            "total_time": total_time,
            "avg_recognition_time": self.total_recognition_time / max(self.conversation_count, 1),
            "avg_ai_response_time": self.total_ai_response_time / max(self.conversation_count, 1),
            "avg_tts_time": self.total_tts_time / max(self.conversation_count, 1),
            "conversations_per_minute": self.conversation_count / (total_time / 60) if total_time > 0 else 0
        }
        
        return stats
    
    def print_conversation_stats(self):
        """打印对话统计信息"""
        stats = self._get_conversation_stats()
        
        print(f"\n📊 对话统计信息：")
        print(f"   总轮数: {stats['conversation_count']}")
        print(f"   总时长: {stats['total_time']:.1f} 秒")
        print(f"   平均识别时间: {stats['avg_recognition_time']:.2f} 秒")
        print(f"   平均AI响应时间: {stats['avg_ai_response_time']:.2f} 秒")
        print(f"   平均TTS时间: {stats['avg_tts_time']:.2f} 秒")
        print(f"   对话频率: {stats['conversations_per_minute']:.1f} 轮/分钟")
    
    def reset_stats(self):
        """重置统计信息"""
        self.conversation_count = 0
        self.start_time = None
        self.total_recognition_time = 0
        self.total_ai_response_time = 0
        self.total_tts_time = 0
        print("🔄 统计信息已重置")
    
    def set_ai_service(self, ai_service: AIServiceWithFallback):
        """
        设置AI服务
        
        Args:
            ai_service: AI服务实例
        """
        self.ai_service = ai_service
        print(f"🔄 AI服务已切换到: {ai_service.get_service_name()}")
    
    def set_tts_service(self, tts_service: TTSServiceInterface):
        """
        设置TTS服务
        
        Args:
            tts_service: TTS服务实例
        """
        self.tts_service = tts_service
        print(f"🔄 TTS服务已切换到: {tts_service.get_service_name()}")
    
    def enable_tts(self, enable: bool = True):
        """
        启用/禁用TTS
        
        Args:
            enable: 是否启用
        """
        if enable and not self.tts_service:
            print("⚠️ 无法启用TTS：未设置TTS服务")
            return
        
        # 可以通过设置为None来禁用TTS
        if not enable:
            self.tts_service = None
            print("🔇 TTS已禁用")
        else:
            print("🔊 TTS已启用")
    
    def test_all_services(self) -> dict:
        """
        测试所有服务
        
        Returns:
            测试结果
        """
        results = {}
        
        print("🧪 开始服务测试...")
        
        # 测试ASR服务
        try:
            print("\n🎤 测试ASR服务...")
            asr_available = self.asr_service.test_microphone()
            results['asr'] = asr_available
        except Exception as e:
            print(f"❌ ASR测试失败：{e}")
            results['asr'] = False
        
        # 测试AI服务
        try:
            print("\n🤖 测试AI服务...")
            test_response = self.ai_service.get_response("测试")
            ai_available = bool(test_response and test_response.strip())
            results['ai'] = ai_available
            if ai_available:
                print(f"✅ AI服务测试成功：{test_response[:50]}...")
        except Exception as e:
            print(f"❌ AI测试失败：{e}")
            results['ai'] = False
        
        # 测试TTS服务
        if self.tts_service:
            try:
                print("\n🔊 测试TTS服务...")
                tts_available = self.tts_service.is_available()
                results['tts'] = tts_available
                if tts_available:
                    print("✅ TTS服务可用")
                else:
                    print("❌ TTS服务不可用")
            except Exception as e:
                print(f"❌ TTS测试失败：{e}")
                results['tts'] = False
        else:
            results['tts'] = None
        
        # 测试VAD服务
        if self.vad_service:
            try:
                print("\n🎯 测试VAD服务...")
                vad_available = self.vad_service.test_voice_detection(
                    self.asr_service.recognizer, 
                    self.asr_service.microphone
                )
                results['vad'] = vad_available
            except Exception as e:
                print(f"❌ VAD测试失败：{e}")
                results['vad'] = False
        else:
            results['vad'] = None
        
        # 总结测试结果
        print(f"\n📋 服务测试总结：")
        for service, status in results.items():
            if status is None:
                print(f"   {service.upper()}: 未配置")
            elif status:
                print(f"   {service.upper()}: ✅ 可用")
            else:
                print(f"   {service.upper()}: ❌ 不可用")
        
        return results
    
    def get_service_info(self) -> dict:
        """
        获取服务信息
        
        Returns:
            服务信息字典
        """
        info = {
            "asr_service": "ASR语音识别服务",
            "ai_service": self.ai_service.get_service_name() if self.ai_service else "未配置",
            "tts_service": self.tts_service.get_service_name() if self.tts_service else "未配置",
            "vad_service": "VAD语音活动检测" if self.vad_service else "未配置",
            "config_path": self.config.config_path
        }
        
        return info
    
    def print_service_info(self):
        """打印服务信息"""
        info = self.get_service_info()
        
        print(f"\n🔧 当前服务配置：")
        for key, value in info.items():
            print(f"   {key}: {value}") 