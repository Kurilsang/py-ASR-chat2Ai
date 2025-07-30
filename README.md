# 🎙️ 中文语音识别+AI对话+TTS合成演示程序

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

一个功能完整的语音AI助手系统，支持中文语音识别、多种AI对话服务和语音合成。采用模块化架构设计，易于扩展和维护。

## ✨ 功能特性

- 🎤 **智能语音识别** - 支持Google ASR，带离线回退
- 🤖 **多种AI对话服务** - 简单AI/Ollama/OpenAI，自动回退
- 🔊 **多种语音合成** - pyttsx3/Google TTS/Azure TTS
- ⚡ **流式TTS技术** - 边合成边播放，响应速度提升50-80%
- 🎯 **智能语音活动检测** - 免按键自动连续对话
- 🔄 **完善的错误处理** - 多重备选方案
- ⚙️ **灵活配置管理** - 支持配置文件定制
- 📊 **详细统计监控** - 对话性能分析
- 🏗️ **模块化架构** - 采用设计模式，易于扩展

## 🏗️ 项目架构

```
├── main.py                     # 🚀 程序启动入口
├── config/
│   └── config.ini             # ⚙️ 配置文件
├── requirements.txt           # 📦 依赖包列表
├── utils/                     # 🛠️ 工具模块
│   ├── __init__.py
│   ├── config_manager.py      # 🔧 配置管理器(单例模式)
│   ├── menu_helper.py         # 📋 菜单工具
│   └── dependency_checker.py  # 🔍 依赖检查工具
├── services/                  # 🎯 服务层
│   ├── __init__.py
│   ├── asr_service.py         # 🎤 ASR语音识别服务
│   ├── ai_service.py          # 🤖 AI对话服务(策略模式)
│   ├── tts_service.py         # 🔊 TTS语音合成服务(策略模式)
│   ├── streaming_tts_enhanced.py # ⚡ 增强版流式TTS服务
│   └── vad_service.py         # 🎯 语音活动检测服务
└── core/                      # 💎 核心业务层
    ├── __init__.py
    └── conversation_manager.py # 🎭 对话管理器
```

## 🎯 设计模式

- **🏗️ 工厂模式** - AI服务和TTS服务的创建
- **📋 策略模式** - 不同AI和TTS算法的切换
- **🔒 单例模式** - 配置管理器确保全局唯一
- **🔄 装饰器模式** - 服务回退机制

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- Windows/Linux/macOS
- 麦克风设备

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/Kurilsang/py-ASR-chat2Ai.git
cd py-ASR-chat2Ai

# 安装基础依赖
pip install -r requirements.txt

# 可选：安装额外TTS支持
pip install gtts pygame                    # Google TTS + 流式TTS音频播放
pip install azure-cognitiveservices-speech # Azure TTS
```

### 3. 运行程序

```bash
# 启动程序
python main.py

# 查看帮助
python main.py --help

# 查看版本
python main.py --version
```

### 4. 配置服务

程序支持多种服务组合：

#### AI对话服务
- **简单AI** - 本地免费，立即可用
- **Ollama** - 本地大模型，需要安装Ollama
- **OpenAI** - 在线服务，需要API Key

#### TTS语音合成
- **pyttsx3** - Windows内置，免费
- **Google TTS** - 在线服务，音质好
- **Azure TTS** - 高质量，需要API Key
- **流式TTS** - 智能分割+并行处理，大幅提升长对话响应速度

#### 语音检测
- **智能VAD** - 自动检测语音开始/结束
- **可配置参数** - 通过config.ini调整

## ⚡ 流式TTS新特性

### 🎯 核心优势
- **响应速度提升**: 50-80%，长文本从40秒等待减少到1.77秒
- **智能文本分割**: 按语义完整性分割，保持语音自然连贯
- **边合成边播放**: 无需等待完整合成，实时音频输出
- **自动模式切换**: 短文本传统模式，长文本自动启用流式

### 🏗️ 技术实现
- **多线程并行**: 合成、播放、监控三线程协作
- **音频缓存**: 支持临时文件和内存缓存
- **智能回退**: 服务不可用时自动降级
- **详细统计**: 完整的性能监控和分析

## ⚙️ 配置说明

编辑 `config/config.ini` 文件：

```ini
[VOICE_DETECTION]
# 语音结束后等待时间（秒）
silence_timeout = 2.0
# 最小语音时长（秒）
min_speech_duration = 0.5
# 能量阈值调节因子
energy_threshold_multiplier = 1.5

[CONVERSATION]
# 对话间隔时间（秒）
response_pause_time = 1.0
# 对话超时时间（秒）
conversation_timeout = 300

[TTS_SETTINGS]
# TTS播放完成后等待时间（秒）
tts_completion_wait = 0.5
```

## 📊 测试结果

从最新测试可以看到：

```
📋 服务测试总结：
   ASR: ✅ 可用      # 语音识别正常
   AI: ✅ 可用       # AI回复正常（Ollama→简单AI回退）
   TTS: ✅ 可用      # 语音合成正常（Google TTS→pyttsx3回退）
   VAD: ⚠️ 可配置    # 语音检测可调优

📊 对话统计信息：
   总轮数: 1
   总时长: 68.4 秒
   平均识别时间: 3.59 秒
   平均AI响应时间: 5.35 秒
   平均TTS时间: 18.41 秒 (传统模式)
   对话频率: 0.9 轮/分钟

⚡ 流式TTS性能提升：
   首次响应时间: 1.77秒 (vs 41.60秒传统方式)
   响应速度提升: 95.7%
   用户体验: 显著改善
```

## 🎯 使用模式

### 1. 单次对话
适合测试和简单交互

### 2. 智能连续对话 (推荐)
- 自动语音检测
- 无需按键交互
- 智能对话循环
- 流式TTS优化长回复

### 3. 手动连续对话
- 手动控制对话节奏
- 适合调试和精确控制

## 🔧 开发指南

### 扩展AI服务

```python
from services.ai_service import AIServiceInterface

class CustomAIService(AIServiceInterface):
    def get_response(self, message: str) -> str:
        # 实现自定义AI逻辑
        return "自定义回复"
    
    def get_service_name(self) -> str:
        return "自定义AI"
    
    def is_available(self) -> bool:
        return True
```

### 扩展TTS服务

```python
from services.tts_service import TTSServiceInterface

class CustomTTSService(TTSServiceInterface):
    def speak(self, text: str, async_play: bool = True) -> bool:
        # 实现自定义TTS逻辑
        return True
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📝 更新日志

### v2.1.0 (2024-12-19)
- ⚡ **新增流式TTS技术** - 长对话响应速度提升50-80%
- 🧩 智能文本分割算法，保持语义完整性
- 🔄 边合成边播放，大幅改善用户体验
- 📊 详细的流式TTS性能统计和监控
- 🎯 自动模式切换，短文本传统模式，长文本流式模式

### v2.0.0 (2024-12-19)
- ✨ 重构为模块化架构
- 🏭 采用工厂模式和策略模式
- 🔧 单例配置管理器
- 📊 完善的统计和监控
- 🎯 智能语音活动检测
- 🔄 自动回退机制

### v1.0.0 (2024-12-18)
- 🎤 基础语音识别功能
- 🤖 AI对话集成
- 🔊 TTS语音合成

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [SpeechRecognition](https://github.com/Uberi/speech_recognition) - 语音识别库
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) - 文本转语音
- [gTTS](https://github.com/pndurette/gTTS) - Google文本转语音
- [Ollama](https://ollama.ai/) - 本地大语言模型
- [pygame](https://www.pygame.org/) - 音频播放支持

## 📞 联系方式

- 项目地址：[https://github.com/Kurilsang/py-ASR-chat2Ai](https://github.com/Kurilsang/py-ASR-chat2Ai)
- 问题反馈：[Issues](https://github.com/Kurilsang/py-ASR-chat2Ai/issues)

---

⭐ 如果这个项目对你有帮助，请给个星标支持！ 