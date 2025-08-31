# **3. 详细架构设计**

## **3.1 MVVM模式实现**

### **Model层 (数据模型)**
- **Account**: 账户数据模型，包含用户名、密码、状态、备注
- **AccountStatus**: 状态枚举，支持国际化翻译
- **数据验证**: 内置字段验证和业务规则检查

### **ViewModel层 (视图模型)**
- **BatchCreatorViewModel**: 主视图模型
  - 管理应用程序状态
  - 协调多个服务层
  - 处理UI事件到业务逻辑的转换
  - 通过信号槽模式通知UI更新

### **View层 (视图)**
- **BatchCreatorMainWindow**: 主窗口视图
  - 纯UI逻辑，不包含业务代码
  - 响应ViewModel的信号进行UI更新
  - 将用户操作委托给ViewModel处理

## **3.2 服务层架构**

### **DataService (数据服务)**

职责:
- CSV文件导入/导出
- 随机账户生成
- 账户数据管理和验证
- 统计信息计算

核心方法:
- import_from_csv()
- generate_random_accounts()
- export_to_csv()
- get_statistics()


### **AutomationService (自动化服务)**

职责:
- 批量注册流程管理
- 状态控制 (开始/暂停/停止)
- 进度追踪
- 回调机制处理UI更新

核心方法:
- start_batch_registration()
- pause_registration()
- stop_registration()
- process_next_account()


### **TranslationManager (国际化服务)**

职责:
- 多语言翻译管理
- 语言切换
- 翻译文件加载
- 系统语言检测

支持语言:
- 中文 (zh-CN)
- 英文 (en-US)

