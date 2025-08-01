#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper ASR功能测试脚本
用于独立测试Whisper语音识别功能
"""

import sys
import os
from utils import ConfigManager
from services import ASRServiceFactory, WhisperASRService


def test_whisper_installation():
    """测试Whisper依赖是否安装正确"""
    print("🧪 测试Whisper依赖安装...")
    
    try:
        import whisper
        print("✅ openai-whisper 已安装")
        
        import torch
        print(f"✅ torch 已安装，版本: {torch.__version__}")
        
        # 检查CUDA可用性
        if torch.cuda.is_available():
            print(f"✅ CUDA 可用，设备数量: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            print("⚠️ CUDA 不可用，将使用CPU")
        
        return True
        
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        print("请运行: pip install openai-whisper torch torchaudio")
        return False


def test_whisper_models():
    """测试可用的Whisper模型"""
    print("\n🧪 测试Whisper模型...")
    
    try:
        import whisper
        
        available_models = whisper.available_models()
        print(f"✅ 可用模型: {', '.join(available_models)}")
        
        # 测试加载tiny模型（最小的模型）
        print("\n🔧 测试加载tiny模型...")
        model = whisper.load_model("tiny")
        print("✅ tiny模型加载成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
        return False


def test_whisper_service():
    """测试WhisperASRService"""
    print("\n🧪 测试WhisperASRService...")
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager()
        
        # 临时设置为使用tiny模型（快速测试）
        # 确保WHISPER_SETTINGS section存在
        if not config_manager.has_section('WHISPER_SETTINGS'):
            config_manager.set_value('WHISPER_SETTINGS', 'model_size', 'tiny')
            config_manager.set_value('WHISPER_SETTINGS', 'use_api', 'false') 
            config_manager.set_value('WHISPER_SETTINGS', 'device', 'auto')
            config_manager.set_value('WHISPER_SETTINGS', 'language', 'zh')
        else:
            # 临时覆盖配置
            config_manager.set_value('WHISPER_SETTINGS', 'model_size', 'tiny')
        
        # 创建Whisper服务
        whisper_service = WhisperASRService(config_manager)
        
        print(f"✅ WhisperASRService创建成功")
        print(f"   服务名称: {whisper_service.get_service_name()}")
        print(f"   服务状态: {'可用' if whisper_service.is_available() else '不可用'}")
        
        # 显示服务信息
        whisper_service.print_service_info()
        
        return True
        
    except Exception as e:
        print(f"❌ WhisperASRService测试失败: {e}")
        return False


def test_asr_factory():
    """测试ASR服务工厂"""
    print("\n🧪 测试ASR服务工厂...")
    
    try:
        config_manager = ConfigManager()
        
        # 测试工厂创建Whisper服务
        print("🔧 通过工厂创建Whisper服务...")
        whisper_service = ASRServiceFactory.create_service('whisper', config_manager)
        
        if whisper_service:
            print("✅ 工厂创建Whisper服务成功")
            print(f"   服务类型: {type(whisper_service).__name__}")
        else:
            print("❌ 工厂创建Whisper服务失败")
            return False
        
        # 测试带回退的创建
        print("\n🔧 测试带回退机制的服务创建...")
        service = ASRServiceFactory.create_service_with_fallback(
            'whisper', config_manager, fallback_type='traditional'
        )
        
        if service:
            print(f"✅ 带回退机制的服务创建成功: {type(service).__name__}")
        else:
            print("❌ 带回退机制的服务创建失败")
            return False
        
        # 显示支持的服务
        ASRServiceFactory.print_supported_services()
        ASRServiceFactory.print_service_comparison()
        
        return True
        
    except Exception as e:
        print(f"❌ ASR服务工厂测试失败: {e}")
        return False


def test_performance():
    """性能测试"""
    print("\n🧪 Whisper性能测试...")
    
    try:
        import time
        import whisper
        
        # 测试不同模型的加载时间
        models_to_test = ['tiny', 'base']
        
        for model_name in models_to_test:
            print(f"\n⏱️ 测试 {model_name} 模型加载时间...")
            
            start_time = time.time()
            model = whisper.load_model(model_name)
            load_time = time.time() - start_time
            
            print(f"✅ {model_name} 模型加载完成，耗时: {load_time:.2f}秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🎤 Whisper ASR功能测试")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        ("依赖安装测试", test_whisper_installation),
        ("模型测试", test_whisper_models),
        ("服务类测试", test_whisper_service),
        ("工厂类测试", test_asr_factory),
        ("性能测试", test_performance)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            if test_func():
                print(f"✅ {test_name} 通过")
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！Whisper集成成功！")
        print("\n💡 现在可以运行主程序并选择Whisper ASR:")
        print("   python main.py")
    else:
        print("⚠️ 部分测试失败，请检查依赖安装")
        print("\n🔧 修复建议:")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 检查网络连接（首次下载模型需要）")
        print("3. 确保有足够的磁盘空间存储模型")


if __name__ == '__main__':
    main() 