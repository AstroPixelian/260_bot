# **全栈架构文档: 360批量账号注册工具 (更新版)**

**版本: 1.0 - 重新实现版本**

## **1. 引言 (Introduction)**

  * **文档目的**: 本文档详细描述了"360账号批量注册工具"的架构设计，包括MVVM设计模式、多语言支持、完整的UI功能和严格的分层架构。
  * **架构原则**: 基于MVVM模式实现UI与业务逻辑的完全分离，确保代码的可维护性、可测试性和可扩展性。

## **2. 高层架构 (High Level Architecture)**

  * **架构模式**: 采用 **MVVM (Model-View-ViewModel)** 设计模式
  * **技术架构**: 单体桌面应用程序 + 服务层 + 数据层
  * **核心特征**: 
    - 严格的分层架构，低耦合高内聚
    - 完整的多语言国际化支持
    - 基于信号槽的响应式UI更新
    - 模块化的服务层设计

### **2.1 架构层次图**
```mermaid
graph TD
    subgraph "表示层 (Presentation Layer)"
        UI[主窗口 GUI<br/>batch_creator_gui.py]
        Widgets[自定义组件<br/>CopyableTextWidget<br/>PasswordWidget<br/>StatusIcon]
    end
    
    subgraph "视图模型层 (ViewModel Layer)"  
        VM[BatchCreatorViewModel<br/>业务逻辑协调<br/>UI状态管理]
    end
    
    subgraph "服务层 (Service Layer)"
        DataSvc[DataService<br/>数据操作]
        AutoSvc[AutomationService<br/>自动化逻辑]
        I18nSvc[TranslationManager<br/>国际化服务]
    end
    
    subgraph "模型层 (Model Layer)"
        Account[Account<br/>账户数据模型]
        Status[AccountStatus<br/>状态枚举]
    end
    
    subgraph "外部资源 (External Resources)"
        CSV[CSV文件]
        Browser[浏览器<br/>(Playwright)]
        I18n[翻译文件<br/>zh-CN.qm/en-US.qm]
    end
    
    UI --> VM
    Widgets --> VM
    VM --> DataSvc
    VM --> AutoSvc
    VM --> I18nSvc
    DataSvc --> Account
    AutoSvc --> Account
    Account --> Status
    DataSvc --> CSV
    AutoSvc --> Browser
    I18nSvc --> I18n
```

## **3. 详细架构设计**

### **3.1 MVVM模式实现**

#### **Model层 (数据模型)**
- **Account**: 账户数据模型，包含用户名、密码、状态、备注
- **AccountStatus**: 状态枚举，支持国际化翻译
- **数据验证**: 内置字段验证和业务规则检查

#### **ViewModel层 (视图模型)**
- **BatchCreatorViewModel**: 主视图模型
  - 管理应用程序状态
  - 协调多个服务层
  - 处理UI事件到业务逻辑的转换
  - 通过信号槽模式通知UI更新

#### **View层 (视图)**
- **BatchCreatorMainWindow**: 主窗口视图
  - 纯UI逻辑，不包含业务代码
  - 响应ViewModel的信号进行UI更新
  - 将用户操作委托给ViewModel处理

### **3.2 服务层架构**

#### **DataService (数据服务)**

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


#### **AutomationService (自动化服务)**

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


#### **TranslationManager (国际化服务)**

职责:
- 多语言翻译管理
- 语言切换
- 翻译文件加载
- 系统语言检测

支持语言:
- 中文 (zh-CN)
- 英文 (en-US)


## **4. 技术栈 (Updated Tech Stack)**

| 类别 | 技术 | 版本 | 用途 |
| :--- | :--- | :--- | :--- |
| 语言 | Python | 3.12 | 主要开发语言 |
| GUI框架 | PySide6 | ~6.7 | 桌面用户界面 |
| 架构模式 | MVVM | - | 代码组织架构 |
| 国际化 | Qt Linguist | - | 多语言支持 |
| 自动化引擎 | Playwright | ~1.44 | 浏览器自动化 (预留) |
| 依赖管理 | uv | ~0.1.40 | 项目依赖管理 |
| 打包工具 | Nuitka | ~2.2 | 可执行文件打包 |
| 测试框架 | pytest | ~8.2 | 单元测试 |

## **5. 数据模型 (Enhanced Data Models)**

```python
# 完整的账户数据模型
@dataclass
class Account:
    id: int
    username: str
    password: str
    status: AccountStatus = AccountStatus.QUEUED
    notes: str = ""
    
    # 业务方法
    def mark_processing(self, notes: str = "")
    def mark_success(self, notes: str = "")
    def mark_failed(self, notes: str = "")
    def reset_status(self)

class AccountStatus(Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing" 
    SUCCESS = "Success"
    FAILED = "Failed"
    
    def get_translated_name(self):
        """支持国际化的状态名称"""
        return tr(self.value, "AccountStatus")
```

## **6. 最终源代码目录结构**

```
360-account-batch-creator/
├── docs/                          # 项目文档
│   ├── architecture.md            # 架构文档 (本文档)
│   ├── prd.md                      # 产品需求文档
│   ├── front-end-spec.md           # 前端设计规范
│   └── development.md              # 开发指南
├── i18n/                           # 国际化翻译文件
│   ├── zh-CN.ts/qm                 # 中文翻译
│   └── en-US.ts/qm                 # 英文翻译
├── src/                            # 源代码
│   ├── models/                     # 数据模型层
│   │   ├── __init__.py
│   │   └── account.py              # 账户模型
│   ├── services/                   # 服务层
│   │   ├── __init__.py
│   │   ├── data_service.py         # 数据服务
│   │   └── automation_service.py   # 自动化服务
│   ├── viewmodels/                 # 视图模型层
│   │   ├── __init__.py
│   │   └── batch_creator_viewmodel.py
│   ├── translation_manager.py      # 国际化管理
│   └── batch_creator_gui.py  # 主GUI (MVVM版)
├── tests/                          # 测试目录
├── logs/                           # 日志目录
├── data/                           # 静态资源
├── demo_accounts.csv               # 示例数据
├── main.py                         # 应用入口
├── test_gui.py                     # GUI测试入口
├── pyproject.toml                  # 项目配置
└── README.md                       # 项目说明
```

## **7. 核心功能实现**

### **7.1 用户界面特性**
- **四列表格**: 用户名、密码、状态、备注
- **密码管理**: 星号显示、可见性切换、一键复制
- **用户名复制**: 一键复制用户名到剪贴板
- **状态可视化**: 图标+颜色+文字的综合状态显示
- **实时进度**: 进度条+统计数据实时更新
- **多语言切换**: 界面右上角语言切换按钮

### **7.2 业务功能特性**
- **数据导入**: CSV文件格式支持
- **随机生成**: 可配置数量的测试账户生成
- **批量注册**: 模拟的批量注册流程
- **流程控制**: 开始/暂停/恢复/停止
- **结果导出**: 包含状态和时间戳的CSV导出
- **数据验证**: 导入前的数据格式验证

### **7.3 国际化特性**
- **双语支持**: 完整的中英文界面
- **动态切换**: 运行时语言切换
- **状态保存**: 语言选择持久化
- **翻译覆盖**: 所有UI元素完全翻译

### **7.4 MVVM架构 (MVVM Architecture)**
**Model层** → **ViewModel层** → **View层**
- **Model**: Account, AccountStatus (数据模型)
- **Services**: DataService, AutomationService (业务服务)  
- **ViewModel**: BatchCreatorViewModel (业务逻辑协调)
- **View**: BatchCreatorMainWindow (纯UI界面)

### **7.5 核心技术特色 (Core Technical Features)**
- **信号槽机制**: Qt原生的响应式UI更新
- **服务层模式**: 业务逻辑完全与UI分离
- **国际化系统**: Qt Linguist完整支持
- **模块化设计**: 高内聚低耦合架构

## **8. 设计模式和最佳实践**

### **8.1 采用的设计模式**
- **MVVM模式**: 视图与业务逻辑完全分离
- **服务层模式**: 业务逻辑封装在专用服务中
- **观察者模式**: 基于Qt信号槽的响应式更新
- **单例模式**: TranslationManager的全局访问
- **工厂模式**: 账户生成和状态管理

### **8.2 代码质量保证**
- **分层架构**: 严格的层次划分和依赖方向
- **低耦合**: 各层通过接口通信，减少直接依赖
- **高内聚**: 相关功能集中在同一模块中
- **可测试性**: 业务逻辑与UI分离，便于单元测试
- **可扩展性**: 模块化设计支持功能扩展

## **9. 性能优化策略**

### **9.1 UI性能**
- **异步处理**: 长时间操作不阻塞UI线程
- **批量更新**: 减少频繁的UI刷新
- **内存管理**: 合理的对象生命周期管理
- **响应式设计**: 基于信号槽的高效更新机制

### **9.2 数据处理性能**
- **流式处理**: 大文件的流式读取和处理
- **批量操作**: 数据库操作的批量提交
- **缓存策略**: 频繁访问数据的内存缓存
- **验证优化**: 高效的数据验证算法

## **10. 测试策略 (Enhanced)**

### **10.1 单元测试**
- **Model层**: 数据模型的验证逻辑测试
- **Service层**: 业务逻辑的独立测试
- **ViewModel层**: 状态管理和协调逻辑测试
- **国际化**: 翻译功能的完整性测试

### **10.2 集成测试**
- **端到端流程**: 完整业务流程的集成测试
- **UI交互**: 关键用户交互场景测试
- **多语言**: 语言切换功能的集成测试
- **文件操作**: CSV导入导出的集成测试

## **11. 安全性考虑**

### **11.1 数据安全**
- **本地存储**: 所有数据仅存储在本地
- **内存管理**: 敏感数据的安全清理
- **文件权限**: 适当的文件访问权限控制
- **日志安全**: 避免在日志中记录敏感信息

### **11.2 应用安全**
- **输入验证**: 严格的用户输入验证
- **异常处理**: 全面的错误处理机制
- **权限控制**: 最小权限原则
- **依赖安全**: 定期更新和安全扫描

## **12. 部署和维护**

### **12.1 打包部署**
- **单文件打包**: 使用Nuitka打包为独立可执行文件
- **依赖隔离**: 所有依赖内置，无需外部安装
- **跨平台**: 支持Windows 10/11系统
- **自动更新**: 预留自动更新机制接口

### **12.2 维护策略**
- **日志系统**: 完善的日志记录便于问题诊断
- **错误报告**: 结构化的错误信息收集
- **版本控制**: 语义化版本管理
- **向后兼容**: 数据格式的向后兼容性

---

## **附录: 技术决策记录**

### **A1. 架构选择理由**
- **选择MVVM**: 相比MVP/MVC，MVVM更适合Qt的信号槽机制
- **服务层设计**: 将业务逻辑从UI中完全分离，提高可测试性
- **组合优于继承**: 使用组合模式避免深度继承层次

### **A2. 技术栈选择理由**
  * **仓库结构 (Repository Structure): Polyrepo**
  * **服务架构 (Service Architecture): MVVM模式的单体应用** 
  * **测试要求 (Testing Requirements): 架构预留**
  * **最终技术栈 (Final Tech Stack)**
      * **编程语言**: **Python 3.12**
      * **GUI框架**: **PySide6 (Qt6)**
      * **架构模式**: **MVVM (Model-View-ViewModel)**
      * **国际化**: **Qt Linguist (.ts/.qm文件)**
      * **浏览器自动化**: **Playwright** 🔄 **架构预留** - 服务层已预留接口
      * **依赖管理**: **uv**
      * **打包与分发**: **Nuitka** 🔄 **计划中** - 可执行文件打包
  * **架构特色 (Architecture Highlights)**
      * **MVVM模式**: Model层(数据模型) → ViewModel层(业务逻辑) → View层(UI界面)
      * **Service层模式**: DataService(数据操作) + AutomationService(自动化流程) 
      * **信号槽机制**: Qt原生的响应式UI更新机制
      * **模块化设计**: 高内聚低耦合，便于维护和扩展

这份架构文档为项目的实现提供了完整的技术参考，为后续的开发和维护奠定基础。
