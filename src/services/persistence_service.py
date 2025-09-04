"""
Persistence service for saving account registration results to CSV files.

Provides safe, reliable CSV persistence with:
- Pandas DataFrame for efficient CSV operations
- File locking to prevent concurrent access issues
- Signal handling for graceful shutdown on Ctrl-C
- Batch saving (configurable batch_size, default 5)
- Append-only operations to prevent data loss
"""

import atexit
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pandas as pd
from filelock import FileLock

from ..models.account import Account


class PersistenceService:
    """Service for persisting account registration results to CSV files"""
    
    def __init__(self, output_dir: str = ".", batch_size: int = 5):
        """
        Initialize persistence service
        
        Args:
            output_dir: Directory to save CSV files (default: current directory)
            batch_size: Number of results to buffer before auto-save (default: 5)
        """
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        
        # Generate timestamp-based filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = timestamp
        self.csv_file = self.output_dir / f"registration_results_{timestamp}.csv"
        self.lock_file = self.output_dir / f"registration_results_{timestamp}.csv.lock"
        
        # 使用pandas DataFrame作为内存缓冲区
        self.buffer_df = pd.DataFrame()
        
        # 创建文件锁
        self.file_lock = FileLock(self.lock_file)
        
        # 设置信号处理
        self._setup_signal_handlers()
        
        # 注册程序正常退出时的清理
        atexit.register(self.force_save)
        
        print(f"💾 结果将保存到: {self.csv_file}")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def emergency_save(signum=None, frame=None):
            print(f"\n🚨 接收到信号 {signum}，正在紧急保存...")
            success = self.force_save()
            if success:
                print("✅ 数据保存完成，程序安全退出")
            else:
                print("⚠️ 保存可能不完整，请检查文件")
            sys.exit(0)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, emergency_save)   # Ctrl-C
        signal.signal(signal.SIGTERM, emergency_save)  # 程序终止
    
    def add_result(self, account: Account, duration: float, backend: str):
        """添加注册结果到缓冲区"""
        # 创建新记录
        new_record = {
            'timestamp': datetime.now().isoformat(),
            'username': account.username,
            'password': account.password,
            'status': account.status.value,
            'notes': account.notes,
            'duration_seconds': round(duration, 2),
            'backend': backend,
            'session_id': self.session_id
        }
        
        # 添加到DataFrame缓冲区
        new_df = pd.DataFrame([new_record])
        self.buffer_df = pd.concat([self.buffer_df, new_df], ignore_index=True)
        
        print(f"📝 缓冲区: {len(self.buffer_df)}/{self.batch_size}")
        
        # 检查是否需要批量保存
        if len(self.buffer_df) >= self.batch_size:
            self.force_save()
        else:
            # 如果没有达到batch_size，立即保存单条记录防止数据丢失
            # 但保存后不清空缓冲区，这样atexit时就不会重复保存
            self._save_single_record_immediate(new_record)
    
    def _save_single_record_immediate(self, record: Dict[str, Any]):
        """立即保存单条记录（防止数据丢失），并标记已保存"""
        try:
            single_df = pd.DataFrame([record])
            with self.file_lock:
                single_df.to_csv(
                    self.csv_file,
                    mode='a',
                    header=not self.csv_file.exists(),
                    index=False,
                    encoding='utf-8'
                )
            # 记录这条数据已经被单独保存过了，避免重复保存
            self._mark_record_saved(record)
        except Exception as e:
            print(f"⚠️ 单条记录保存失败: {e}")
    
    def _mark_record_saved(self, record: Dict[str, Any]):
        """标记记录已保存，在force_save时跳过"""
        if not hasattr(self, '_saved_records'):
            self._saved_records = set()
        # 使用timestamp + username作为唯一标识
        record_id = f"{record['timestamp']}_{record['username']}"
        self._saved_records.add(record_id)
    
    def _is_record_saved(self, record: Dict[str, Any]) -> bool:
        """检查记录是否已经被保存过"""
        if not hasattr(self, '_saved_records'):
            return False
        record_id = f"{record['timestamp']}_{record['username']}"
        return record_id in self._saved_records
    
    def force_save(self):
        """强制保存缓冲区所有数据"""
        if self.buffer_df.empty:
            print("📝 缓冲区为空，无需保存")
            return True
        
        # 过滤掉已经单独保存过的记录
        unsaved_records = []
        for _, row in self.buffer_df.iterrows():
            record = row.to_dict()
            if not self._is_record_saved(record):
                unsaved_records.append(record)
        
        if not unsaved_records:
            print("📝 缓冲区中所有记录已保存，清空缓冲区")
            self.buffer_df = pd.DataFrame()
            return True
        
        try:
            # 只保存未保存的记录
            unsaved_df = pd.DataFrame(unsaved_records)
            with self.file_lock:  # filelock自动处理跨进程文件锁
                unsaved_df.to_csv(
                    self.csv_file,
                    mode='a',  # 追加模式，永不覆盖
                    header=not self.csv_file.exists(),  # 文件不存在时写表头
                    index=False,  # 不写行索引
                    encoding='utf-8'
                )
            
            count = len(unsaved_records)
            # 清空缓冲区
            self.buffer_df = pd.DataFrame()
            
            if count > 0:
                print(f"💾 成功保存 {count} 条新记录到 {self.csv_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_saved = 0
        if self.csv_file.exists():
            try:
                # 读取已保存的记录数
                df = pd.read_csv(self.csv_file)
                total_saved = len(df)
            except:
                total_saved = 0
        
        # 计算真正未保存的缓冲区记录数
        unsaved_buffer_count = 0
        if not self.buffer_df.empty:
            for _, row in self.buffer_df.iterrows():
                record = row.to_dict()
                if not self._is_record_saved(record):
                    unsaved_buffer_count += 1
        
        return {
            'file_path': str(self.csv_file),
            'buffer_count': unsaved_buffer_count,  # 只计算真正未保存的
            'total_saved': total_saved,
            'batch_size': self.batch_size
        }
    
    def get_csv_filepath(self) -> Path:
        """Get the path to the CSV file being used"""
        return self.csv_file
    
    def cleanup(self):
        """Cleanup service resources and save any remaining buffer"""
        self.force_save()