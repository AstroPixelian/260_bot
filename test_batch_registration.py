#!/usr/bin/env python3
"""
测试脚本：测试完整的批量账号注册流程
验证修复后的逻辑：
1. 每个账号注册完成后关闭浏览器
2. 遇到验证码时暂停批量处理
3. 继续下一个账号使用全新的浏览器实例
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.account import Account
from src.services.data_service import DataService
from src.services.automation_service import AutomationService
from src.viewmodels.batch_creator_viewmodel import BatchCreatorViewModel

def create_test_accounts(count=3):
    """创建测试账号"""
    accounts = []
    for i in range(count):
        account = Account(
            id=i+1,
            username=f"testuser{i+1}_2025",
            password=f"TestPass{i+1}23!"
        )
        accounts.append(account)
    return accounts

def main():
    print("🚀 Testing Batch Registration Workflow")
    print("=" * 60)
    
    # 创建测试账号
    test_accounts = create_test_accounts(3)
    
    print(f"📝 Created {len(test_accounts)} test accounts:")
    for i, account in enumerate(test_accounts, 1):
        print(f"  {i}. {account.username} / {account.password}")
    
    print("\n" + "=" * 60)
    print("🔧 Initializing services...")
    
    # 初始化服务
    data_service = DataService()
    automation_service = AutomationService()
    view_model = BatchCreatorViewModel(data_service, automation_service)
    
    # 添加测试账号到数据服务
    data_service.add_accounts(test_accounts)
    
    print(f"✅ Added {len(test_accounts)} accounts to data service")
    
    # 设置日志回调
    def log_callback(message):
        print(f"[LOG] {message}")
    
    view_model.log_message.connect(log_callback)
    
    # 设置账号完成回调
    def account_complete_callback(account):
        print(f"[ACCOUNT] {account.username} -> {account.status.value}")
        if account.notes:
            print(f"[NOTES] {account.notes}")
    
    view_model.account_processing_completed.connect(account_complete_callback)
    
    # 设置批量完成回调
    def batch_complete_callback(success_count, failed_count):
        print(f"\n🎉 BATCH COMPLETE!")
        print(f"✅ Success: {success_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Total: {success_count + failed_count}")
    
    view_model.batch_processing_completed.connect(batch_complete_callback)
    
    print("\n" + "=" * 60)
    print("🎯 Starting batch registration...")
    print("Expected behavior:")
    print("1. Each account should use a fresh browser instance")
    print("2. Browser should close after each account (success/failure)")  
    print("3. If captcha detected, batch processing pauses")
    print("4. User can manually solve captcha and continue")
    print("5. Next account uses completely new browser")
    
    try:
        # 启动批量处理
        success = view_model.start_batch_processing()
        if success:
            print("✅ Batch processing started successfully")
            
            # 保持程序运行
            print("\n💡 Batch processing is running...")
            print("💡 Watch for browser behavior:")
            print("   - Each account gets fresh browser")
            print("   - Browser closes after completion")
            print("   - Captcha pauses processing")
            print("\n💡 Press Ctrl+C to stop")
            
            # 简单的事件循环来保持程序运行
            import time
            while automation_service.is_running:
                time.sleep(1)
                
                # 检查统计信息
                stats = data_service.get_statistics()
                if stats['total'] > 0:
                    progress = (stats['success'] + stats['failed']) / stats['total'] * 100
                    print(f"\r📊 Progress: {progress:.1f}% ({stats['success']} success, {stats['failed']} failed, {stats['processing']} processing)", end='', flush=True)
            
            print(f"\n🏁 Batch processing completed!")
            
        else:
            print("❌ Failed to start batch processing")
            
    except KeyboardInterrupt:
        print(f"\n👋 Stopping batch processing...")
        view_model.stop_batch_processing()
        print("✅ Stopped")
    
    print("\n" + "=" * 60)
    print("📊 Final Statistics:")
    final_stats = data_service.get_statistics()
    print(f"Total: {final_stats['total']}")
    print(f"Success: {final_stats['success']}")  
    print(f"Failed: {final_stats['failed']}")
    print(f"Processing: {final_stats['processing']}")
    print(f"Queued: {final_stats['queued']}")
    
    print(f"\n📝 Account Details:")
    for account in data_service.get_accounts():
        print(f"  {account.username}: {account.status.value}")
        if account.notes:
            print(f"    Notes: {account.notes}")

if __name__ == "__main__":
    main()