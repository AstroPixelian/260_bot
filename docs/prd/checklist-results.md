# **7. 项目架构概览 (Project Architecture Overview)**

## **7.1 目录结构 (Directory Structure)**
```
360-account-batch-creator/
├── docs/                          # 项目文档
│   ├── architecture.md            # 架构文档
│   ├── prd.md                      # 产品需求文档 (本文档)
│   └── front-end-spec.md           # 前端设计规范
├── i18n/                           # 国际化翻译文件
│   ├── zh-CN.ts/qm                 # 中文翻译
│   └── en-US.ts/qm                 # 英文翻译
├── src/                            # 源代码
│   ├── models/                     # 数据模型层
│   │   └── account.py              # 账户模型
│   ├── services/                   # 服务层
│   │   ├── data_service.py         # 数据服务
│   │   └── automation_service.py   # 自动化服务
│   ├── viewmodels/                 # 视图模型层
│   │   └── batch_creator_viewmodel.py
│   ├── translation_manager.py      # 国际化管理
│   └── batch_creator_gui.py  # 主GUI
├── main.py                         # 应用入口
├── test_gui.py                     # GUI测试入口
└── pyproject.toml                  # 项目配置
```

## **7.2 MVVM架构实现 (MVVM Architecture Implementation)**

**Model层** → **ViewModel层** → **View层**
- **Model**: Account, AccountStatus (数据模型)
- **Services**: DataService, AutomationService (业务服务)  
- **ViewModel**: BatchCreatorViewModel (业务逻辑协调)
- **View**: BatchCreatorMainWindow (纯UI界面)

## **7.3 核心技术特色 (Core Technical Features)**
- **信号槽机制**: Qt原生的响应式UI更新
- **服务层模式**: 业务逻辑完全与UI分离
- **国际化系统**: Qt Linguist完整支持
- **模块化设计**: 高内聚低耦合架构
