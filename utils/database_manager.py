"""
MongoDB数据库管理器 - 单例模式
负责管理数据库连接、操作和数据模型
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import (
    ConnectionFailure, 
    ServerSelectionTimeoutError, 
    DuplicateKeyError,
    PyMongoError
)
from utils.config_manager import ConfigManager


class DatabaseManager:
    """MongoDB数据库管理器 - 单例模式"""
    
    _instance: Optional['DatabaseManager'] = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None
    _config: Optional[ConfigManager] = None
    
    def __new__(cls, config_manager: ConfigManager = None):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize(config_manager)
        return cls._instance
    
    def _initialize(self, config_manager: ConfigManager):
        """初始化数据库管理器"""
        self._config = config_manager or ConfigManager()
        self._connection_string = None
        self._database_name = None
        self._is_connected = False
        self._stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0
        }
        
        # 从配置文件加载设置
        self._load_config()
        
        # 初始化数据库连接
        if self._config.get_bool('MONGODB_SETTINGS', 'enable_database', True):
            self._connect()
    
    def _load_config(self):
        """加载数据库配置"""
        self._connection_string = self._config.get_string(
            'MONGODB_SETTINGS', 'connection_string', 'mongodb://localhost:27017/'
        )
        self._database_name = self._config.get_string(
            'MONGODB_SETTINGS', 'database_name', 'py-asr-chat2ai'
        )
        self._connection_timeout = self._config.get_int(
            'MONGODB_SETTINGS', 'connection_timeout', 5000
        )
        self._server_selection_timeout = self._config.get_int(
            'MONGODB_SETTINGS', 'server_selection_timeout', 5000
        )
        self._auto_create_indexes = self._config.get_bool(
            'MONGODB_SETTINGS', 'auto_create_indexes', True
        )
        self._data_retention_days = self._config.get_int(
            'MONGODB_SETTINGS', 'data_retention_days', 30
        )
    
    def _connect(self):
        """连接到MongoDB数据库"""
        try:
            print("🔌 正在连接MongoDB数据库...")
            self._stats['connection_attempts'] += 1
            
            # 创建MongoDB客户端
            self._client = MongoClient(
                self._connection_string,
                connectTimeoutMS=self._connection_timeout,
                serverSelectionTimeoutMS=self._server_selection_timeout,
                maxPoolSize=50,
                retryWrites=True
            )
            
            # 测试连接
            self._client.admin.command('ping')
            
            # 获取数据库实例
            self._database = self._client[self._database_name]
            
            self._is_connected = True
            self._stats['successful_connections'] += 1
            
            print(f"✅ MongoDB连接成功")
            print(f"   数据库: {self._database_name}")
            print(f"   连接字符串: {self._connection_string}")
            
            # 创建索引
            if self._auto_create_indexes:
                self._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self._stats['failed_connections'] += 1
            print(f"❌ MongoDB连接失败: {e}")
            self._is_connected = False
        except Exception as e:
            self._stats['failed_connections'] += 1
            print(f"❌ MongoDB初始化失败: {e}")
            self._is_connected = False
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            print("🔧 创建数据库索引...")
            
            # 聊天记录索引
            chat_collection = self.get_collection('chat_records')
            chat_collection.create_index([
                ('session_id', ASCENDING),
                ('timestamp', DESCENDING)
            ])
            chat_collection.create_index('user_id')
            chat_collection.create_index('timestamp')
            
            # 用户信息索引
            user_collection = self.get_collection('users')
            user_collection.create_index('user_id', unique=True)
            user_collection.create_index('created_at')
            
            # 会话信息索引
            session_collection = self.get_collection('sessions')
            session_collection.create_index('session_id', unique=True)
            session_collection.create_index([
                ('user_id', ASCENDING),
                ('created_at', DESCENDING)
            ])
            
            print("✅ 数据库索引创建完成")
            
        except Exception as e:
            print(f"⚠️ 索引创建失败: {e}")
    
    def is_connected(self) -> bool:
        """检查数据库连接状态"""
        if not self._is_connected or not self._client:
            return False
        
        try:
            # 测试连接
            self._client.admin.command('ping')
            return True
        except:
            self._is_connected = False
            return False
    
    def get_database(self) -> Optional[Database]:
        """获取数据库实例"""
        if not self.is_connected():
            return None
        return self._database
    
    def get_collection(self, collection_name: str = None) -> Optional[Collection]:
        """获取集合实例"""
        if not self.is_connected():
            return None
        
        # 如果没有指定集合名，使用默认的聊天记录集合
        if collection_name is None:
            collection_name = self._config.get_string(
                'MONGODB_SETTINGS', 'chat_collection', 'chat_records'
            )
        
        return self._database[collection_name]
    
    def save_chat_record(self, user_message: str, ai_response: str, 
                        session_id: str = None, user_id: str = "default",
                        asr_service: str = None, ai_service: str = None,
                        tts_service: str = None, metadata: Dict = None) -> bool:
        """
        保存聊天记录
        
        Args:
            user_message: 用户消息
            ai_response: AI回复
            session_id: 会话ID
            user_id: 用户ID
            asr_service: ASR服务名称
            ai_service: AI服务名称
            tts_service: TTS服务名称
            metadata: 附加元数据
            
        Returns:
            是否保存成功
        """
        if not self.is_connected():
            return False
        
        try:
            self._stats['total_operations'] += 1
            
            # 生成会话ID（如果没有提供）
            if session_id is None:
                session_id = f"session_{int(time.time())}"
            
            # 构建聊天记录
            chat_record = {
                'session_id': session_id,
                'user_id': user_id,
                'user_message': user_message,
                'ai_response': ai_response,
                'timestamp': datetime.utcnow(),
                'services': {
                    'asr': asr_service,
                    'ai': ai_service,
                    'tts': tts_service
                },
                'metadata': metadata or {}
            }
            
            # 保存到数据库
            collection = self.get_collection('chat_records')
            result = collection.insert_one(chat_record)
            
            if result.inserted_id:
                self._stats['successful_operations'] += 1
                print(f"💾 聊天记录已保存 (ID: {result.inserted_id})")
                return True
            
        except Exception as e:
            self._stats['failed_operations'] += 1
            print(f"❌ 保存聊天记录失败: {e}")
        
        return False
    
    def get_chat_history(self, session_id: str = None, user_id: str = None,
                        limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        获取聊天历史记录
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            limit: 返回记录数限制
            offset: 偏移量
            
        Returns:
            聊天记录列表
        """
        if not self.is_connected():
            return []
        
        try:
            collection = self.get_collection('chat_records')
            
            # 构建查询条件
            query = {}
            if session_id:
                query['session_id'] = session_id
            if user_id:
                query['user_id'] = user_id
            
            # 执行查询
            cursor = collection.find(query).sort('timestamp', DESCENDING)
            
            if offset > 0:
                cursor = cursor.skip(offset)
            if limit > 0:
                cursor = cursor.limit(limit)
            
            records = list(cursor)
            
            # 转换ObjectId为字符串
            for record in records:
                record['_id'] = str(record['_id'])
            
            return records
            
        except Exception as e:
            print(f"❌ 获取聊天历史失败: {e}")
            return []
    
    def create_session(self, user_id: str = "default", 
                      session_name: str = None) -> Optional[str]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            session_name: 会话名称
            
        Returns:
            会话ID
        """
        if not self.is_connected():
            return None
        
        try:
            session_id = f"session_{user_id}_{int(time.time())}"
            
            session_record = {
                'session_id': session_id,
                'user_id': user_id,
                'session_name': session_name or f"会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'message_count': 0,
                'is_active': True
            }
            
            collection = self.get_collection('sessions')
            result = collection.insert_one(session_record)
            
            if result.inserted_id:
                print(f"📝 新会话已创建: {session_id}")
                return session_id
            
        except Exception as e:
            print(f"❌ 创建会话失败: {e}")
        
        return None
    
    def update_session(self, session_id: str, **updates):
        """更新会话信息"""
        if not self.is_connected():
            return False
        
        try:
            collection = self.get_collection('sessions')
            updates['updated_at'] = datetime.utcnow()
            
            result = collection.update_one(
                {'session_id': session_id},
                {'$set': updates}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"❌ 更新会话失败: {e}")
            return False
    
    def get_user_stats(self, user_id: str) -> Dict:
        """获取用户统计信息"""
        if not self.is_connected():
            return {}
        
        try:
            collection = self.get_collection('chat_records')
            
            # 聚合查询获取统计信息
            pipeline = [
                {'$match': {'user_id': user_id}},
                {'$group': {
                    '_id': None,
                    'total_messages': {'$sum': 1},
                    'total_sessions': {'$addToSet': '$session_id'},
                    'first_message': {'$min': '$timestamp'},
                    'last_message': {'$max': '$timestamp'}
                }}
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                return {
                    'total_messages': stats['total_messages'],
                    'total_sessions': len(stats['total_sessions']),
                    'first_message': stats['first_message'],
                    'last_message': stats['last_message']
                }
            
        except Exception as e:
            print(f"❌ 获取用户统计失败: {e}")
        
        return {}
    
    def cleanup_old_data(self):
        """清理过期数据"""
        if not self.is_connected() or self._data_retention_days <= 0:
            return
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self._data_retention_days)
            
            collection = self.get_collection('chat_records')
            result = collection.delete_many({'timestamp': {'$lt': cutoff_date}})
            
            if result.deleted_count > 0:
                print(f"🗑️ 已清理 {result.deleted_count} 条过期聊天记录")
            
        except Exception as e:
            print(f"❌ 清理过期数据失败: {e}")
    
    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        stats = {
            'connected': self.is_connected(),
            'database_name': self._database_name,
            'connection_string': self._connection_string,
            **self._stats
        }
        
        if self.is_connected():
            try:
                # 获取集合统计
                collections_stats = {}
                for collection_name in ['chat_records', 'users', 'sessions']:
                    collection = self.get_collection(collection_name)
                    collections_stats[collection_name] = collection.count_documents({})
                
                stats['collections'] = collections_stats
                
            except Exception as e:
                print(f"⚠️ 获取数据库统计失败: {e}")
        
        return stats
    
    def print_database_info(self):
        """打印数据库信息"""
        print(f"\n💾 MongoDB数据库信息:")
        
        stats = self.get_database_stats()
        
        print(f"   连接状态: {'✅ 已连接' if stats['connected'] else '❌ 未连接'}")
        print(f"   数据库名: {stats['database_name']}")
        print(f"   连接字符串: {stats['connection_string']}")
        
        if stats['connected'] and 'collections' in stats:
            print(f"   集合统计:")
            for collection, count in stats['collections'].items():
                print(f"     {collection}: {count} 条记录")
        
        print(f"   操作统计:")
        print(f"     连接尝试: {stats['connection_attempts']}")
        print(f"     成功连接: {stats['successful_connections']}")
        print(f"     总操作数: {stats['total_operations']}")
        print(f"     成功操作: {stats['successful_operations']}")
    
    def close(self):
        """关闭数据库连接"""
        if self._client:
            try:
                self._client.close()
                print("🔌 MongoDB连接已关闭")
            except:
                pass
            finally:
                self._client = None
                self._database = None
                self._is_connected = False
    
    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        self.close() 