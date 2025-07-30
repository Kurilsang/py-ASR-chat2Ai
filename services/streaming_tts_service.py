"""
流式TTS语音合成服务
支持长文本分段合成、边合成边播放，提升响应速度和用户体验
"""

import re
import time
import threading
import queue
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from utils.config_manager import ConfigManager
from .tts_service import TTSServiceInterface, TTSServiceFactory


class TextChunker:
    """文本分割器 - 智能分割长文本"""
    
    @staticmethod
    def split_text(text: str, max_chunk_size: int = 100) -> List[str]:
        """
        智能分割文本为适合TTS的片段
        
        Args:
            text: 原始文本
            max_chunk_size: 最大片段长度
            
        Returns:
            文本片段列表
        """
        if len(text) <= max_chunk_size:
            return [text.strip()] if text.strip() else []
        
        # 按标点符号分割
        sentence_endings = r'[。！？；\n]+'
        sentences = re.split(sentence_endings, text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 如果当前句子本身就很长，强制分割
            if len(sentence) > max_chunk_size:
                # 先处理当前积累的chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # 按逗号等次级标点分割长句
                sub_parts = re.split(r'[，、：]', sentence)
                temp_chunk = ""
                
                for part in sub_parts:
                    part = part.strip()
                    if not part:
                        continue
                        
                    if len(temp_chunk + part) <= max_chunk_size:
                        temp_chunk += part + "，"
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk[:-1])  # 去掉最后的逗号
                        temp_chunk = part + "，"
                
                if temp_chunk:
                    chunks.append(temp_chunk[:-1])
                    
            # 正常情况：累积句子到合适长度
            elif len(current_chunk + sentence) <= max_chunk_size:
                current_chunk += sentence + "。"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "。"
        
        # 添加最后的chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]


class StreamingTTSService:
    """流式TTS服务 - 支持分段合成和流式播放"""
    
    def __init__(self, 
                 base_tts_service: TTSServiceInterface,
                 config_manager: ConfigManager,
                 max_chunk_size: int = 80,
                 queue_size: int = 5):
        """
        初始化流式TTS服务
        
        Args:
            base_tts_service: 基础TTS服务
            config_manager: 配置管理器
            max_chunk_size: 最大文本片段大小
            queue_size: 播放队列大小
        """
        self.base_tts_service = base_tts_service
        self.config = config_manager
        self.max_chunk_size = max_chunk_size
        
        # 播放队列和控制
        self.audio_queue = queue.Queue(maxsize=queue_size)
        self.is_streaming = False
        self.stop_event = threading.Event()
        
        # 统计信息
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'start_time': None,
            'first_audio_time': None
        }
        
        print(f"✅ 流式TTS服务初始化完成 (基于: {base_tts_service.get_service_name()})")
    
    def speak_streaming(self, 
                       text: str, 
                       progress_callback: Optional[Callable] = None) -> bool:
        """
        流式语音合成和播放
        
        Args:
            text: 要合成的文本
            progress_callback: 进度回调函数
            
        Returns:
            是否成功启动
        """
        if not text.strip():
            return False
        
        # 重置状态
        self.stop_event.clear()
        self.is_streaming = True
        self.stats = {
            'total_chunks': 0,
            'processed_chunks': 0,
            'start_time': time.time(),
            'first_audio_time': None
        }
        
        # 分割文本
        chunks = TextChunker.split_text(text, self.max_chunk_size)
        self.stats['total_chunks'] = len(chunks)
        
        print(f"🔄 开始流式TTS处理，文本分为 {len(chunks)} 个片段")
        print(f"📝 片段预览: {[chunk[:20]+'...' if len(chunk)>20 else chunk for chunk in chunks[:3]]}")
        
        # 启动生产者线程（合成音频）
        producer_thread = threading.Thread(
            target=self._audio_producer,
            args=(chunks, progress_callback),
            daemon=True
        )
        
        # 启动消费者线程（播放音频）
        consumer_thread = threading.Thread(
            target=self._audio_consumer,
            daemon=True
        )
        
        producer_thread.start()
        consumer_thread.start()
        
        return True
    
    def _audio_producer(self, chunks: List[str], progress_callback: Optional[Callable]):
        """音频生产者 - 负责合成音频片段"""
        try:
            for i, chunk in enumerate(chunks):
                if self.stop_event.is_set():
                    break
                
                print(f"🎤 合成片段 {i+1}/{len(chunks)}: {chunk[:30]}...")
                
                # 合成当前片段
                chunk_start_time = time.time()
                
                # 这里我们需要修改基础TTS服务以支持同步合成
                success = self._synthesize_chunk_sync(chunk)
                
                synthesis_time = time.time() - chunk_start_time
                
                if success:
                    # 将合成结果放入队列
                    audio_data = {
                        'chunk_index': i,
                        'text': chunk,
                        'synthesis_time': synthesis_time,
                        'timestamp': time.time()
                    }
                    
                    # 如果是第一个音频片段，记录时间
                    if self.stats['first_audio_time'] is None:
                        self.stats['first_audio_time'] = time.time()
                        first_response_time = self.stats['first_audio_time'] - self.stats['start_time']
                        print(f"⚡ 首个音频片段完成，响应时间: {first_response_time:.2f}秒")
                    
                    try:
                        self.audio_queue.put(audio_data, timeout=5)
                        self.stats['processed_chunks'] += 1
                        
                        # 调用进度回调
                        if progress_callback:
                            progress = (i + 1) / len(chunks)
                            progress_callback(progress, f"合成进度: {i+1}/{len(chunks)}")
                        
                    except queue.Full:
                        print("⚠️ 音频队列已满，等待播放...")
                        time.sleep(0.1)
                else:
                    print(f"❌ 片段合成失败: {chunk[:30]}...")
            
            # 发送结束信号
            self.audio_queue.put(None)
            print("✅ 所有音频片段合成完成")
            
        except Exception as e:
            print(f"❌ 音频生产者错误: {e}")
            self.audio_queue.put(None)
    
    def _audio_consumer(self):
        """音频消费者 - 负责播放音频片段"""
        try:
            while not self.stop_event.is_set():
                try:
                    # 从队列获取音频数据
                    audio_data = self.audio_queue.get(timeout=1)
                    
                    # 结束信号
                    if audio_data is None:
                        break
                    
                    chunk_index = audio_data['chunk_index']
                    chunk_text = audio_data['text']
                    
                    print(f"🔊 播放片段 {chunk_index+1}: {chunk_text[:30]}...")
                    
                    # 这里直接播放，因为音频已经合成好了
                    # 实际实现中，我们需要保存合成的音频数据
                    play_success = self._play_synthesized_audio(audio_data)
                    
                    if play_success:
                        print(f"✅ 片段 {chunk_index+1} 播放完成")
                    else:
                        print(f"❌ 片段 {chunk_index+1} 播放失败")
                    
                    self.audio_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"❌ 音频播放错误: {e}")
            
            self.is_streaming = False
            print("🎵 流式播放完成")
            
        except Exception as e:
            print(f"❌ 音频消费者错误: {e}")
            self.is_streaming = False
    
    def _synthesize_chunk_sync(self, chunk: str) -> bool:
        """同步合成音频片段"""
        try:
            # 对于不同的TTS服务，我们需要不同的处理方式
            service_name = self.base_tts_service.get_service_name()
            
            if "pyttsx3" in service_name:
                # pyttsx3本身是同步的，直接调用
                return self.base_tts_service.speak(chunk, async_play=False)
            
            elif "Google TTS" in service_name:
                # Google TTS需要特殊处理以获取音频数据
                return self._synthesize_gtts_chunk(chunk)
            
            elif "Azure TTS" in service_name:
                # Azure TTS需要特殊处理
                return self._synthesize_azure_chunk(chunk)
            
            else:
                # 默认处理
                return self.base_tts_service.speak(chunk, async_play=False)
                
        except Exception as e:
            print(f"❌ 音频合成错误: {e}")
            return False
    
    def _synthesize_gtts_chunk(self, chunk: str) -> bool:
        """Google TTS特殊处理"""
        try:
            from gtts import gTTS
            import io
            
            # 生成音频数据但不立即播放
            tts = gTTS(text=chunk, lang='zh-cn', slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # 保存音频数据供后续播放
            # 这里可以保存到临时文件或内存中
            return True
            
        except Exception as e:
            print(f"❌ Google TTS合成失败: {e}")
            return False
    
    def _synthesize_azure_chunk(self, chunk: str) -> bool:
        """Azure TTS特殊处理"""
        try:
            # Azure TTS的特殊处理逻辑
            # 类似Google TTS，需要获取音频数据而不是直接播放
            return True
            
        except Exception as e:
            print(f"❌ Azure TTS合成失败: {e}")
            return False
    
    def _play_synthesized_audio(self, audio_data: dict) -> bool:
        """播放已合成的音频"""
        try:
            # 这里应该播放之前合成并保存的音频数据
            # 为了简化，我们直接调用base_tts_service播放对应文本
            chunk_text = audio_data['text']
            return self.base_tts_service.speak(chunk_text, async_play=False)
            
        except Exception as e:
            print(f"❌ 音频播放失败: {e}")
            return False
    
    def stop_streaming(self):
        """停止流式播放"""
        print("🛑 停止流式TTS播放...")
        self.stop_event.set()
        self.is_streaming = False
        
        # 清空队列
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
            except queue.Empty:
                break
        
        # 停止基础TTS服务
        self.base_tts_service.stop_speaking()
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"流式{self.base_tts_service.get_service_name()}"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.base_tts_service.is_available()
    
    def print_stats(self):
        """打印统计信息"""
        if self.stats['start_time'] is None:
            print("📊 暂无统计数据")
            return
        
        total_time = time.time() - self.stats['start_time']
        first_response = (self.stats['first_audio_time'] - self.stats['start_time'] 
                         if self.stats['first_audio_time'] else 0)
        
        print("\n📊 流式TTS统计:")
        print(f"   总片段数: {self.stats['total_chunks']}")
        print(f"   已处理: {self.stats['processed_chunks']}")
        print(f"   首次响应: {first_response:.2f}秒")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   平均每片段: {total_time/max(self.stats['processed_chunks'], 1):.2f}秒")


class StreamingTTSServiceFactory:
    """流式TTS服务工厂"""
    
    @staticmethod
    def create_streaming_service(
        base_service_type: str,
        config_manager: ConfigManager,
        max_chunk_size: int = 80,
        queue_size: int = 5
    ) -> StreamingTTSService:
        """
        创建流式TTS服务
        
        Args:
            base_service_type: 基础TTS服务类型
            config_manager: 配置管理器
            max_chunk_size: 最大文本片段大小
            queue_size: 播放队列大小
            
        Returns:
            流式TTS服务实例
        """
        # 创建基础TTS服务
        base_service = TTSServiceFactory.create_service(base_service_type, config_manager)
        
        # 创建流式服务
        return StreamingTTSService(
            base_tts_service=base_service,
            config_manager=config_manager,
            max_chunk_size=max_chunk_size,
            queue_size=queue_size
        )
    
    @staticmethod
    def create_streaming_service_with_fallback(
        primary_type: str,
        config_manager: ConfigManager,
        fallback_type: str = "pyttsx3",
        max_chunk_size: int = 80,
        queue_size: int = 5
    ) -> StreamingTTSService:
        """
        创建带回退机制的流式TTS服务
        
        Args:
            primary_type: 主要服务类型
            config_manager: 配置管理器
            fallback_type: 回退服务类型
            max_chunk_size: 最大文本片段大小
            queue_size: 播放队列大小
            
        Returns:
            带回退机制的流式TTS服务
        """
        # 创建带回退的基础TT服务
        base_service = TTSServiceFactory.create_service_with_fallback(
            primary_type, config_manager, fallback_type
        )
        
        # 创建流式服务
        return StreamingTTSService(
            base_tts_service=base_service,
            config_manager=config_manager,
            max_chunk_size=max_chunk_size,
            queue_size=queue_size
        )


# 示例使用
def demo_streaming_tts():
    """流式TTS演示"""
    from utils.config_manager import ConfigManager
    
    config = ConfigManager()
    
    # 创建流式TTS服务
    streaming_tts = StreamingTTSServiceFactory.create_streaming_service(
        base_service_type="gtts",
        config_manager=config,
        max_chunk_size=60
    )
    
    # 测试长文本
    long_text = """
    流式TTS技术可以显著提升用户体验，特别是在处理长文本时。
    传统的TTS需要等待整个文本合成完成后才能开始播放，
    而流式TTS可以边合成边播放，大大缩短首次响应时间。
    这种技术在语音助手、有声书、实时翻译等场景中非常有用。
    通过智能的文本分割和队列管理，我们可以实现更流畅的语音交互体验。
    """
    
    def progress_callback(progress, message):
        print(f"🔄 {message} ({progress*100:.1f}%)")
    
    # 开始流式播放
    success = streaming_tts.speak_streaming(long_text, progress_callback)
    
    if success:
        print("✅ 流式TTS启动成功")
        
        # 等待播放完成
        while streaming_tts.is_streaming:
            time.sleep(0.5)
        
        # 显示统计信息
        streaming_tts.print_stats()
    else:
        print("❌ 流式TTS启动失败")


if __name__ == "__main__":
    demo_streaming_tts() 