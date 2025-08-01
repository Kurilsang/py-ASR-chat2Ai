"""
对话管理器 - 核心业务层
协调ASR、AI、TTS、VAD等服务完成完整的对话流程
支持聊天记录的数据库存储功能
"""

import time
import uuid
from typing import Optional
from utils.config_manager import ConfigManager
from utils.menu_helper import MenuHelper
from utils.database_manager import DatabaseManager
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
                 vad_service: Optional[VoiceActivityDetector] = None,
                 user_id: str = "default"):
        """
        初始化对话管理器
        
        Args:
            config_manager: 配置管理器
            asr_service: ASR语音识别服务
            ai_service: AI对话服务
            tts_service: TTS语音合成服务（可选）
            vad_service: VAD语音活动检测服务（可选）
            user_id: 用户ID
        """
        self.config = config_manager
        self.asr_service = asr_service
        self.ai_service = ai_service
        self.tts_service = tts_service
        self.vad_service = vad_service
        self.user_id = user_id
        
        # 初始化数据库管理器
        self.db_manager = None
        self.current_session_id = None
        self.enable_database = config_manager.get_bool('MONGODB_SETTINGS', 'enable_database', True)
        
        if self.enable_database:
            try:
                self.db_manager = DatabaseManager(config_manager)
                if self.db_manager.is_connected():
                    # 创建新会话
                    self.current_session_id = self.db_manager.create_session(self.user_id)
                    print("💾 数据库存储已启用")
                else:
                    print("⚠️ 数据库连接失败，聊天记录将不会被保存")
                    self.enable_database = False
            except Exception as e:
                print(f"⚠️ 数据库初始化失败: {e}")
                self.enable_database = False
        else:
            print("💾 数据库存储已禁用")
        
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
            
            # 步骤5：保存聊天记录到数据库
            self._save_chat_record(user_input, ai_response)
            
            # 步骤6：TTS语音播放
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
    
    def _save_chat_record(self, user_message: str, ai_response: str):
        """
        保存聊天记录到数据库
        
        Args:
            user_message: 用户消息
            ai_response: AI回复
        """
        if not self.enable_database or not self.db_manager or not self.current_session_id:
            return
        
        try:
            # 获取服务名称
            asr_service_name = self.asr_service.get_service_name() if hasattr(self.asr_service, 'get_service_name') else 'unknown'
            ai_service_name = self.ai_service.get_current_service_name() if hasattr(self.ai_service, 'get_current_service_name') else 'unknown'
            tts_service_name = self.tts_service.get_service_name() if self.tts_service and hasattr(self.tts_service, 'get_service_name') else 'none'
            
            # 构建元数据
            metadata = {
                'recognition_time': getattr(self, '_last_recognition_time', 0),
                'ai_response_time': getattr(self, '_last_ai_response_time', 0),
                'tts_time': getattr(self, '_last_tts_time', 0),
                'conversation_round': self.conversation_count + 1
            }
            
            # 保存到数据库
            success = self.db_manager.save_chat_record(
                user_message=user_message,
                ai_response=ai_response,
                session_id=self.current_session_id,
                user_id=self.user_id,
                asr_service=asr_service_name,
                ai_service=ai_service_name,
                tts_service=tts_service_name,
                metadata=metadata
            )
            
            if success:
                # 更新会话统计
                self.db_manager.update_session(
                    self.current_session_id,
                    message_count=self.conversation_count + 1,
                    last_activity=self.db_manager._database.client.server_info()['localTime'] if self.db_manager._database else None
                )
            
        except Exception as e:
            print(f"⚠️ 保存聊天记录失败: {e}")
    
    def get_chat_history(self, limit: int = 10) -> list:
        """
        获取当前会话的聊天历史
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            聊天记录列表
        """
        if not self.enable_database or not self.db_manager or not self.current_session_id:
            return []
        
        try:
            return self.db_manager.get_chat_history(
                session_id=self.current_session_id,
                limit=limit
            )
        except Exception as e:
            print(f"⚠️ 获取聊天历史失败: {e}")
            return []
    
    def print_chat_history(self, limit: int = 5):
        """
        打印聊天历史记录
        
        Args:
            limit: 显示记录数限制
        """
        history = self.get_chat_history(limit)
        
        if not history:
            print("📝 暂无聊天历史记录")
            return
        
        print(f"\n📜 最近 {len(history)} 条聊天记录:")
        print("=" * 60)
        
        for i, record in enumerate(reversed(history), 1):
            timestamp = record.get('timestamp', 'unknown')
            user_msg = record.get('user_message', '')
            ai_msg = record.get('ai_response', '')
            
            print(f"\n{i}. 时间: {timestamp}")
            print(f"   👤 用户: {user_msg}")
            print(f"   🤖 AI: {ai_msg}")
        
        print("=" * 60)
    
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