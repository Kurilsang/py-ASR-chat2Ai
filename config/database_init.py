#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB数据库初始化脚本
用于初始化数据库结构、创建索引和插入测试数据
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_manager import ConfigManager
from utils.database_manager import DatabaseManager


def create_sample_data():
    """创建示例数据"""
    
    # 初始化配置和数据库管理器
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager)
    
    if not db_manager.is_connected():
        print("❌ 数据库连接失败，无法创建示例数据")
        return False
    
    print("📝 创建示例数据...")
    
    # 创建示例用户
    users_collection = db_manager.get_collection('users')
    
    sample_users = [
        {
            'user_id': 'default',
            'username': '默认用户',
            'email': 'default@example.com',
            'created_at': datetime.utcnow(),
            'last_active': datetime.utcnow(),
            'settings': {
                'preferred_language': 'zh',
                'enable_tts': True,
                'asr_service': 'whisper'
            }
        },
        {
            'user_id': 'user001',
            'username': '测试用户1',
            'email': 'user001@example.com',
            'created_at': datetime.utcnow() - timedelta(days=7),
            'last_active': datetime.utcnow() - timedelta(hours=2),
            'settings': {
                'preferred_language': 'zh',
                'enable_tts': True,
                'asr_service': 'traditional'
            }
        }
    ]
    
    for user in sample_users:
        try:
            users_collection.update_one(
                {'user_id': user['user_id']},
                {'$set': user},
                upsert=True
            )
            print(f"✅ 用户创建成功: {user['username']}")
        except Exception as e:
            print(f"❌ 用户创建失败: {e}")
    
    # 创建示例会话
    session_id = db_manager.create_session('default', '示例对话会话')
    
    if session_id:
        # 创建示例聊天记录
        sample_chats = [
            {
                'user_message': '你好，我想测试一下语音识别功能',
                'ai_response': '你好！很高兴为您测试语音识别功能。请说出您想要识别的内容。',
                'asr_service': 'whisper-base',
                'ai_service': 'simple',
                'tts_service': 'pyttsx3'
            },
            {
                'user_message': '识别一下这句中文',
                'ai_response': '好的，我已经成功识别了您说的中文内容："识别一下这句中文"。识别效果很好！',
                'asr_service': 'whisper-base',
                'ai_service': 'simple',
                'tts_service': 'pyttsx3'
            },
            {
                'user_message': 'Can you understand English?',
                'ai_response': 'Yes, I can understand English! The speech recognition works well for both Chinese and English.',
                'asr_service': 'whisper-base',
                'ai_service': 'simple',
                'tts_service': 'pyttsx3'
            }
        ]
        
        for i, chat in enumerate(sample_chats):
            success = db_manager.save_chat_record(
                user_message=chat['user_message'],
                ai_response=chat['ai_response'],
                session_id=session_id,
                user_id='default',
                asr_service=chat['asr_service'],
                ai_service=chat['ai_service'],
                tts_service=chat['tts_service'],
                metadata={
                    'recognition_time': 2.5 + i * 0.3,
                    'response_time': 1.2 + i * 0.2,
                    'confidence_score': 0.95 - i * 0.02
                }
            )
            
            if success:
                print(f"✅ 示例聊天记录 {i+1} 创建成功")
        
        # 更新会话统计
        db_manager.update_session(session_id, message_count=len(sample_chats))
    
    print("✅ 示例数据创建完成")
    return True


def validate_database_structure():
    """验证数据库结构"""
    
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager)
    
    if not db_manager.is_connected():
        print("❌ 数据库连接失败，无法验证结构")
        return False
    
    print("🔍 验证数据库结构...")
    
    # 检查集合是否存在
    database = db_manager.get_database()
    collection_names = database.list_collection_names()
    
    expected_collections = ['chat_records', 'users', 'sessions']
    
    for collection_name in expected_collections:
        if collection_name in collection_names:
            collection = db_manager.get_collection(collection_name)
            count = collection.count_documents({})
            print(f"✅ 集合 '{collection_name}' 存在，包含 {count} 条记录")
            
            # 检查索引
            indexes = list(collection.list_indexes())
            print(f"   索引数量: {len(indexes)}")
            for index in indexes:
                print(f"     - {index['name']}: {list(index['key'].keys())}")
        else:
            print(f"⚠️ 集合 '{collection_name}' 不存在")
    
    return True


def cleanup_database():
    """清理数据库（仅用于测试）"""
    
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager)
    
    if not db_manager.is_connected():
        print("❌ 数据库连接失败，无法清理")
        return False
    
    print("🗑️ 清理数据库...")
    
    database = db_manager.get_database()
    
    # 删除所有集合的数据（保留结构）
    collections = ['chat_records', 'users', 'sessions']
    
    for collection_name in collections:
        try:
            collection = database[collection_name]
            result = collection.delete_many({})
            print(f"✅ 清理集合 '{collection_name}': 删除了 {result.deleted_count} 条记录")
        except Exception as e:
            print(f"❌ 清理集合 '{collection_name}' 失败: {e}")
    
    print("✅ 数据库清理完成")
    return True


def test_database_operations():
    """测试数据库操作"""
    
    print("🧪 测试数据库操作...")
    
    config_manager = ConfigManager()
    db_manager = DatabaseManager(config_manager)
    
    if not db_manager.is_connected():
        print("❌ 数据库连接失败，无法进行测试")
        return False
    
    # 测试保存聊天记录
    test_session_id = f"test_session_{int(datetime.now().timestamp())}"
    
    success = db_manager.save_chat_record(
        user_message="这是一条测试消息",
        ai_response="这是AI的测试回复",
        session_id=test_session_id,
        user_id="test_user",
        asr_service="test_asr",
        ai_service="test_ai",
        tts_service="test_tts",
        metadata={"test": True}
    )
    
    if success:
        print("✅ 聊天记录保存测试通过")
        
        # 测试查询聊天历史
        history = db_manager.get_chat_history(session_id=test_session_id)
        if history:
            print(f"✅ 聊天历史查询测试通过，找到 {len(history)} 条记录")
        else:
            print("❌ 聊天历史查询测试失败")
        
        # 测试用户统计
        stats = db_manager.get_user_stats("test_user")
        if stats:
            print(f"✅ 用户统计测试通过: {stats}")
        else:
            print("❌ 用户统计测试失败")
    else:
        print("❌ 聊天记录保存测试失败")
    
    return True


def main():
    """主函数"""
    print("🔧 MongoDB数据库初始化工具")
    print("=" * 50)
    
    # 检查参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        # 显示菜单
        print("\n请选择操作:")
        print("1. 初始化数据库（创建索引和示例数据）")
        print("2. 验证数据库结构")
        print("3. 清理数据库")
        print("4. 测试数据库操作")
        print("5. 显示数据库信息")
        
        choice = input("\n请输入选择（1-5）: ").strip()
        
        command_map = {
            '1': 'init',
            '2': 'validate',
            '3': 'cleanup',
            '4': 'test',
            '5': 'info'
        }
        
        command = command_map.get(choice, 'info')
    
    # 执行对应操作
    try:
        if command == 'init':
            print("\n🚀 开始初始化数据库...")
            create_sample_data()
            validate_database_structure()
            
        elif command == 'validate':
            print("\n🔍 验证数据库结构...")
            validate_database_structure()
            
        elif command == 'cleanup':
            print("\n⚠️ 警告：这将删除所有数据！")
            confirm = input("确认清理数据库？(y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                cleanup_database()
            else:
                print("操作已取消")
                
        elif command == 'test':
            print("\n🧪 测试数据库操作...")
            test_database_operations()
            
        elif command == 'info':
            print("\n💾 显示数据库信息...")
            config_manager = ConfigManager()
            db_manager = DatabaseManager(config_manager)
            db_manager.print_database_info()
            
        else:
            print(f"❌ 未知命令: {command}")
            print("可用命令: init, validate, cleanup, test, info")
    
    except KeyboardInterrupt:
        print("\n\n👋 操作被用户中断")
    except Exception as e:
        print(f"❌ 执行失败: {e}")
    
    print("\n✨ 数据库初始化工具执行完成")


if __name__ == '__main__':
    main() 