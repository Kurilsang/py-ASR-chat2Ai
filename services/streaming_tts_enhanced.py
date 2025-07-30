"""
增强版流式TTS语音合成服务
真正实现音频数据缓存、边合成边播放，大幅提升长对话响应速度
"""

import os
import re
import time
import threading
import queue
import tempfile
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any
from utils.config_manager import ConfigManager
from .tts_service import TTSServiceInterface, TTSServiceFactory


class AudioChunk:
    """音频片段数据类"""
    
    def __init__(self, 
                 chunk_index: int,
                 text: str,
                 audio_file_path: Optional[str] = None,
                 audio_data: Optional[bytes] = None,
                 synthesis_time: float = 0.0):
        self.chunk_index = chunk_index
        self.text = text
        self.audio_file_path = audio_file_path
        self.audio_data = audio_data
        self.synthesis_time = synthesis_time
        self.created_time = time.time()
    
    def has_audio(self) -> bool:
        """检查是否有音频数据"""
        return self.audio_file_path is not None or self.audio_data is not None
    
    def cleanup(self):
        """清理临时文件"""
        if self.audio_file_path and os.path.exists(self.audio_file_path):
            try:
                os.remove(self.audio_file_path)
            except:
                pass


class EnhancedTextChunker:
    """增强文本分割器 - 更智能的文本分割"""
    
    @staticmethod
    def split_text_smart(text: str, max_chunk_size: int = 80) -> List[str]:
        """
        智能分割文本，考虑语义完整性
        
        Args:
            text: 原始文本
            max_chunk_size: 最大片段长度
            
        Returns:
            文本片段列表
        """
        if len(text) <= max_chunk_size:
            return [text.strip()] if text.strip() else []
        
        # 首先按自然段落分割
        paragraphs = text.split('\n')
        chunks = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 如果段落本身就很短，直接添加
            if len(paragraph) <= max_chunk_size:
                chunks.append(paragraph)
                continue
            
            # 按句子分割长段落
            sentences = EnhancedTextChunker._split_into_sentences(paragraph)
            current_chunk = ""
            
            for sentence in sentences:
                # 如果添加这个句子不会超过限制
                if len(current_chunk + sentence) <= max_chunk_size:
                    current_chunk += sentence
                else:
                    # 保存当前chunk
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    
                    # 如果单个句子就很长，需要进一步分割
                    if len(sentence) > max_chunk_size:
                        sub_chunks = EnhancedTextChunker._split_long_sentence(sentence, max_chunk_size)
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        current_chunk = sentence
            
            # 添加最后的chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    @staticmethod
    def _split_into_sentences(text: str) -> List[str]:
        """将文本分割为句子"""
        # 中文句子结束标点
        sentence_endings = r'([。！？；])'
        parts = re.split(sentence_endings, text)
        
        sentences = []
        for i in range(0, len(parts)-1, 2):
            sentence = parts[i] + (parts[i+1] if i+1 < len(parts) else '')
            if sentence.strip():
                sentences.append(sentence.strip())
        
        return sentences
    
    @staticmethod
    def _split_long_sentence(sentence: str, max_size: int) -> List[str]:
        """分割过长的句子"""
        # 按逗号、顿号等分割
        sub_parts = re.split(r'([，、：；])', sentence)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sub_parts), 2):
            part = sub_parts[i] + (sub_parts[i+1] if i+1 < len(sub_parts) else '')
            
            if len(current_chunk + part) <= max_size:
                current_chunk += part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # 如果单个部分还是太长，强制分割
                if len(part) > max_size:
                    # 按字符数强制分割
                    for j in range(0, len(part), max_size):
                        chunks.append(part[j:j+max_size])
                    current_chunk = ""
                else:
                    current_chunk = part
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class EnhancedStreamingTTSService:
    """增强版流式TTS服务 - 真正实现音频缓存和流式播放"""
    
    def __init__(self, 
                 base_tts_service: TTSServiceInterface,
                 config_manager: ConfigManager,
                 max_chunk_size: int = 80,
                 queue_size: int = 10,
                 cache_audio: bool = True):
        """
        初始化增强流式TTS服务
        
        Args:
            base_tts_service: 基础TTS服务
            config_manager: 配置管理器
            max_chunk_size: 最大文本片段大小
            queue_size: 播放队列大小
            cache_audio: 是否缓存音频数据
        """
        self.base_tts_service = base_tts_service
        self.config = config_manager
        self.max_chunk_size = max_chunk_size
        self.cache_audio = cache_audio
        
        # 队列管理
        self.synthesis_queue = queue.Queue(maxsize=queue_size)
        self.playback_queue = queue.Queue(maxsize=queue_size)
        
        # 状态管理
        self.is_streaming = False
        self.stop_event = threading.Event()
        self.temp_files = []
        
        # 统计信息
        self.stats = {
            'total_chunks': 0,
            'synthesized_chunks': 0,
            'played_chunks': 0,
            'start_time': None,
            'first_audio_time': None,
            'first_playback_time': None,
            'total_synthesis_time': 0,
            'total_playback_time': 0
        }
        
        print(f"✅ 增强流式TTS服务初始化完成")
        print(f"   基础服务: {base_tts_service.get_service_name()}")
        print(f"   最大片段: {max_chunk_size}字符")
        print(f"   队列大小: {queue_size}")
        print(f"   音频缓存: {'启用' if cache_audio else '禁用'}")
    
    def speak_streaming(self, 
                       text: str, 
                       progress_callback: Optional[Callable[[float, str], None]] = None) -> bool:
        """
        流式语音合成和播放
        
        Args:
            text: 要合成的文本
            progress_callback: 进度回调函数 (progress, message)
            
        Returns:
            是否成功启动
        """
        if not text.strip():
            return False
        
        # 重置状态
        self.stop_event.clear()
        self.is_streaming = True
        self._reset_stats()
        
        # 智能分割文本
        chunks = EnhancedTextChunker.split_text_smart(text, self.max_chunk_size)
        self.stats['total_chunks'] = len(chunks)
        
        print(f"\n🔄 开始增强流式TTS处理")
        print(f"📝 原文长度: {len(text)}字符")
        print(f"🧩 分割为: {len(chunks)}个片段")
        print(f"📋 片段预览:")
        for i, chunk in enumerate(chunks[:3]):
            print(f"   {i+1}. {chunk[:30]}{'...' if len(chunk)>30 else ''}")
        if len(chunks) > 3:
            print(f"   ... 还有{len(chunks)-3}个片段")
        
        # 启动三个线程：合成、播放、管理
        threads = [
            threading.Thread(target=self._synthesis_worker, args=(chunks, progress_callback), daemon=True),
            threading.Thread(target=self._playback_worker, daemon=True),
            threading.Thread(target=self._management_worker, daemon=True)
        ]
        
        for thread in threads:
            thread.start()
        
        return True
    
    def _reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_chunks': 0,
            'synthesized_chunks': 0,
            'played_chunks': 0,
            'start_time': time.time(),
            'first_audio_time': None,
            'first_playback_time': None,
            'total_synthesis_time': 0,
            'total_playback_time': 0
        }
    
    def _synthesis_worker(self, chunks: List[str], progress_callback: Optional[Callable]):
        """合成工作线程 - 负责音频合成"""
        try:
            for i, chunk_text in enumerate(chunks):
                if self.stop_event.is_set():
                    break
                
                print(f"🎤 合成片段 {i+1}/{len(chunks)}: {chunk_text[:40]}...")
                
                synthesis_start = time.time()
                audio_chunk = self._synthesize_chunk_enhanced(i, chunk_text)
                synthesis_time = time.time() - synthesis_start
                
                self.stats['total_synthesis_time'] += synthesis_time
                
                if audio_chunk and audio_chunk.has_audio():
                    # 记录首次合成时间
                    if self.stats['first_audio_time'] is None:
                        self.stats['first_audio_time'] = time.time()
                        first_response = self.stats['first_audio_time'] - self.stats['start_time']
                        print(f"⚡ 首个音频片段合成完成，响应时间: {first_response:.2f}秒")
                    
                    # 放入播放队列
                    try:
                        self.playback_queue.put(audio_chunk, timeout=10)
                        self.stats['synthesized_chunks'] += 1
                        
                        # 调用进度回调
                        if progress_callback:
                            progress = (i + 1) / len(chunks)
                            progress_callback(progress, f"合成: {i+1}/{len(chunks)}")
                        
                        print(f"✅ 片段 {i+1} 合成完成 (耗时: {synthesis_time:.2f}秒)")
                        
                    except queue.Full:
                        print("⚠️ 播放队列已满，等待...")
                        time.sleep(0.1)
                else:
                    print(f"❌ 片段 {i+1} 合成失败")
            
            # 发送结束信号
            self.playback_queue.put(None)
            print("🎯 所有音频片段合成完成")
            
        except Exception as e:
            print(f"❌ 合成工作线程错误: {e}")
            self.playback_queue.put(None)
    
    def _playback_worker(self):
        """播放工作线程 - 负责音频播放"""
        try:
            while not self.stop_event.is_set():
                try:
                    # 从队列获取音频片段
                    audio_chunk = self.playback_queue.get(timeout=2)
                    
                    # 结束信号
                    if audio_chunk is None:
                        break
                    
                    # 记录首次播放时间
                    if self.stats['first_playback_time'] is None:
                        self.stats['first_playback_time'] = time.time()
                        playback_delay = self.stats['first_playback_time'] - self.stats['start_time']
                        print(f"🔊 开始播放，总延迟: {playback_delay:.2f}秒")
                    
                    # 播放音频
                    playback_start = time.time()
                    success = self._play_audio_chunk(audio_chunk)
                    playback_time = time.time() - playback_start
                    
                    self.stats['total_playback_time'] += playback_time
                    
                    if success:
                        self.stats['played_chunks'] += 1
                        print(f"🎵 片段 {audio_chunk.chunk_index+1} 播放完成 (耗时: {playback_time:.2f}秒)")
                    else:
                        print(f"❌ 片段 {audio_chunk.chunk_index+1} 播放失败")
                    
                    # 清理音频片段
                    audio_chunk.cleanup()
                    
                    self.playback_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"❌ 播放错误: {e}")
            
            print("🎵 播放工作线程结束")
            
        except Exception as e:
            print(f"❌ 播放工作线程错误: {e}")
        finally:
            self.is_streaming = False
    
    def _management_worker(self):
        """管理工作线程 - 负责状态监控和清理"""
        try:
            while self.is_streaming and not self.stop_event.is_set():
                time.sleep(1)
                
                # 定期打印进度
                if self.stats['total_chunks'] > 0:
                    synthesis_progress = self.stats['synthesized_chunks'] / self.stats['total_chunks']
                    playback_progress = self.stats['played_chunks'] / self.stats['total_chunks']
                    
                    if synthesis_progress > 0 or playback_progress > 0:
                        print(f"📊 进度 - 合成: {synthesis_progress*100:.1f}%, 播放: {playback_progress*100:.1f}%")
            
            print("📊 管理工作线程结束")
            
        except Exception as e:
            print(f"❌ 管理工作线程错误: {e}")
    
    def _synthesize_chunk_enhanced(self, chunk_index: int, text: str) -> Optional[AudioChunk]:
        """增强音频片段合成"""
        try:
            service_name = self.base_tts_service.get_service_name()
            
            if "Google TTS" in service_name:
                return self._synthesize_gtts_enhanced(chunk_index, text)
            elif "Azure TTS" in service_name:
                return self._synthesize_azure_enhanced(chunk_index, text)
            elif "pyttsx3" in service_name:
                return self._synthesize_pyttsx3_enhanced(chunk_index, text)
            else:
                # 默认处理：创建虚拟音频片段
                return AudioChunk(chunk_index, text)
                
        except Exception as e:
            print(f"❌ 音频合成错误: {e}")
            return None
    
    def _synthesize_gtts_enhanced(self, chunk_index: int, text: str) -> Optional[AudioChunk]:
        """Google TTS增强合成"""
        try:
            from gtts import gTTS
            import io
            
            # 合成音频
            tts = gTTS(text=text, lang='zh-cn', slow=False)
            
            if self.cache_audio:
                # 保存到临时文件
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.mp3',
                    prefix=f'tts_chunk_{chunk_index}_'
                )
                temp_file.close()
                
                tts.save(temp_file.name)
                self.temp_files.append(temp_file.name)
                
                return AudioChunk(
                    chunk_index=chunk_index,
                    text=text,
                    audio_file_path=temp_file.name
                )
            else:
                # 保存到内存
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_data = audio_buffer.getvalue()
                
                return AudioChunk(
                    chunk_index=chunk_index,
                    text=text,
                    audio_data=audio_data
                )
                
        except Exception as e:
            print(f"❌ Google TTS合成失败: {e}")
            return None
    
    def _synthesize_azure_enhanced(self, chunk_index: int, text: str) -> Optional[AudioChunk]:
        """Azure TTS增强合成"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # 配置
            speech_key = os.getenv('AZURE_SPEECH_KEY')
            service_region = os.getenv('AZURE_SPEECH_REGION', 'eastus')
            
            if not speech_key:
                return None
            
            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, 
                region=service_region
            )
            speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"
            
            if self.cache_audio:
                # 保存到文件
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.wav',
                    prefix=f'azure_tts_chunk_{chunk_index}_'
                )
                temp_file.close()
                
                audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_file.name)
                synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
                
                result = synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    self.temp_files.append(temp_file.name)
                    return AudioChunk(
                        chunk_index=chunk_index,
                        text=text,
                        audio_file_path=temp_file.name
                    )
            
            return None
            
        except Exception as e:
            print(f"❌ Azure TTS合成失败: {e}")
            return None
    
    def _synthesize_pyttsx3_enhanced(self, chunk_index: int, text: str) -> Optional[AudioChunk]:
        """pyttsx3增强合成"""
        # pyttsx3不容易直接获取音频数据，返回文本片段即可
        return AudioChunk(chunk_index, text)
    
    def _play_audio_chunk(self, audio_chunk: AudioChunk) -> bool:
        """播放音频片段"""
        try:
            if audio_chunk.audio_file_path:
                return self._play_audio_file(audio_chunk.audio_file_path)
            elif audio_chunk.audio_data:
                return self._play_audio_data(audio_chunk.audio_data)
            else:
                # 回退到基础TTS服务
                return self.base_tts_service.speak(audio_chunk.text, async_play=False)
                
        except Exception as e:
            print(f"❌ 音频播放失败: {e}")
            return False
    
    def _play_audio_file(self, file_path: str) -> bool:
        """播放音频文件"""
        try:
            import pygame
            
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                if self.stop_event.is_set():
                    pygame.mixer.music.stop()
                    return False
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"❌ 音频文件播放失败: {e}")
            return False
    
    def _play_audio_data(self, audio_data: bytes) -> bool:
        """播放音频数据"""
        try:
            import pygame
            import io
            
            pygame.mixer.init()
            audio_buffer = io.BytesIO(audio_data)
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                if self.stop_event.is_set():
                    pygame.mixer.music.stop()
                    return False
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"❌ 音频数据播放失败: {e}")
            return False
    
    def stop_streaming(self):
        """停止流式播放"""
        print("🛑 停止增强流式TTS播放...")
        self.stop_event.set()
        self.is_streaming = False
        
        # 清空队列
        self._clear_queues()
        
        # 停止基础TTS服务
        self.base_tts_service.stop_speaking()
        
        # 清理临时文件
        self._cleanup_temp_files()
    
    def _clear_queues(self):
        """清空所有队列"""
        for q in [self.synthesis_queue, self.playback_queue]:
            while not q.empty():
                try:
                    item = q.get_nowait()
                    if isinstance(item, AudioChunk):
                        item.cleanup()
                    q.task_done()
                except queue.Empty:
                    break
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        self.temp_files.clear()
    
    def get_service_name(self) -> str:
        """获取服务名称"""
        return f"增强流式{self.base_tts_service.get_service_name()}"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.base_tts_service.is_available()
    
    def print_detailed_stats(self):
        """打印详细统计信息"""
        if self.stats['start_time'] is None:
            print("📊 暂无统计数据")
            return
        
        current_time = time.time()
        total_time = current_time - self.stats['start_time']
        
        first_audio_delay = (self.stats['first_audio_time'] - self.stats['start_time'] 
                           if self.stats['first_audio_time'] else 0)
        first_playback_delay = (self.stats['first_playback_time'] - self.stats['start_time'] 
                              if self.stats['first_playback_time'] else 0)
        
        print("\n📊 增强流式TTS详细统计:")
        print(f"   📝 总片段数: {self.stats['total_chunks']}")
        print(f"   🎤 已合成: {self.stats['synthesized_chunks']}")
        print(f"   🔊 已播放: {self.stats['played_chunks']}")
        print(f"   ⚡ 首次合成延迟: {first_audio_delay:.2f}秒")
        print(f"   🎵 首次播放延迟: {first_playback_delay:.2f}秒")
        print(f"   🕐 总合成时间: {self.stats['total_synthesis_time']:.2f}秒")
        print(f"   🎶 总播放时间: {self.stats['total_playback_time']:.2f}秒")
        print(f"   📈 总耗时: {total_time:.2f}秒")
        
        if self.stats['synthesized_chunks'] > 0:
            avg_synthesis = self.stats['total_synthesis_time'] / self.stats['synthesized_chunks']
            print(f"   📊 平均合成时间: {avg_synthesis:.2f}秒/片段")
        
        if self.stats['played_chunks'] > 0:
            avg_playback = self.stats['total_playback_time'] / self.stats['played_chunks']
            print(f"   📊 平均播放时间: {avg_playback:.2f}秒/片段")
        
        # 性能提升计算
        if first_playback_delay > 0 and total_time > 0:
            traditional_delay = total_time  # 传统方式需要等待全部完成
            improvement = (traditional_delay - first_playback_delay) / traditional_delay * 100
            print(f"   🚀 响应速度提升: {improvement:.1f}%")


class EnhancedStreamingTTSFactory:
    """增强流式TTS工厂"""
    
    @staticmethod
    def create_enhanced_streaming_service(
        base_service_type: str,
        config_manager: ConfigManager,
        max_chunk_size: int = 80,
        queue_size: int = 10,
        cache_audio: bool = True
    ) -> EnhancedStreamingTTSService:
        """创建增强流式TTS服务"""
        base_service = TTSServiceFactory.create_service(base_service_type, config_manager)
        
        return EnhancedStreamingTTSService(
            base_tts_service=base_service,
            config_manager=config_manager,
            max_chunk_size=max_chunk_size,
            queue_size=queue_size,
            cache_audio=cache_audio
        )
    
    @staticmethod
    def create_enhanced_streaming_with_fallback(
        primary_type: str,
        config_manager: ConfigManager,
        fallback_type: str = "pyttsx3",
        max_chunk_size: int = 80,
        queue_size: int = 10,
        cache_audio: bool = True
    ) -> EnhancedStreamingTTSService:
        """创建带回退的增强流式TTS服务"""
        base_service = TTSServiceFactory.create_service_with_fallback(
            primary_type, config_manager, fallback_type
        )
        
        return EnhancedStreamingTTSService(
            base_tts_service=base_service,
            config_manager=config_manager,
            max_chunk_size=max_chunk_size,
            queue_size=queue_size,
            cache_audio=cache_audio
        )


# 演示函数
def demo_enhanced_streaming():
    """增强流式TTS演示"""
    from utils.config_manager import ConfigManager
    
    config = ConfigManager()
    
    # 创建增强流式TTS服务
    streaming_tts = EnhancedStreamingTTSFactory.create_enhanced_streaming_service(
        base_service_type="gtts",
        config_manager=config,
        max_chunk_size=60,
        queue_size=8,
        cache_audio=True
    )
    
    # 测试长文本
    long_text = """
    增强版的流式TTS技术是语音交互系统的重要突破。它不仅解决了传统TTS系统在处理长文本时响应缓慢的问题，
    更通过智能的文本分割、音频缓存和并行处理，实现了真正的边合成边播放。
    
    这种技术的核心优势在于：首先，它能够将长文本智能分割为语义完整的片段，确保每个片段都具有良好的语音连贯性。
    其次，通过多线程并行处理，合成和播放可以同时进行，大大缩短了用户的等待时间。
    
    在实际应用中，用户可以明显感受到响应速度的提升，特别是在语音助手、在线教育、有声读物等场景中，
    这种技术能够提供更加流畅和自然的交互体验。
    
    未来，我们还可以进一步优化算法，引入预测性缓存、自适应分割等技术，让语音合成变得更加智能和高效。
    """
    
    def progress_callback(progress: float, message: str):
        print(f"🔄 {message} - 进度: {progress*100:.1f}%")
    
    print("🚀 开始增强流式TTS演示")
    success = streaming_tts.speak_streaming(long_text, progress_callback)
    
    if success:
        print("✅ 增强流式TTS启动成功，开始播放...")
        
        # 等待播放完成
        while streaming_tts.is_streaming:
            time.sleep(1)
        
        # 显示详细统计
        streaming_tts.print_detailed_stats()
    else:
        print("❌ 增强流式TTS启动失败")


if __name__ == "__main__":
    demo_enhanced_streaming() 