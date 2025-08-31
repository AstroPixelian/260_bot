# **6. 最终源代码目录结构**

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
