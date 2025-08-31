# **2. 高层架构 (High Level Architecture)**

  * **架构模式**: 采用 **MVVM (Model-View-ViewModel)** 设计模式
  * **技术架构**: 单体桌面应用程序 + 服务层 + 数据层
  * **核心特征**: 
    - 严格的分层架构，低耦合高内聚
    - 完整的多语言国际化支持
    - 基于信号槽的响应式UI更新
    - 模块化的服务层设计

## **2.1 架构层次图**
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
