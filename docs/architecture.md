# **全栈架构文档: 360账号批量注册工具**

**版本: 1.0**

## **1. 引言 (Introduction)**

  * **文档目的**: 本文档概述了“360账号批量注册工具”的完整全栈架构，包括应用结构、技术选型、设计模式和部署策略。它是所有后续开发工作的最高技术指南。
  * **项目启动模板**: 本架构基于社区模板 `trin94/PySide6-project-template` 的结构和原则进行设计，并根据我们的具体需求进行定制。

## **2. 高层架构 (High Level Architecture)**

  * **技术摘要**: 本项目将构建一个单体的(Monolithic)桌面应用程序，旨在自动化浏览器操作。其核心技术栈为Python 3.12和PySide6。架构的关键特征是UI展现（通过QML）与业务逻辑（通过Python）的严格分离。应用将通过Playwright库控制一个浏览器实例，并最终由Nuitka打包成一个独立的Windows可执行文件进行分发。
  * **平台与部署 (Platform and Infrastructure)**
      * **目标平台**: Windows 10/11。
      * **部署方式**: 通过Nuitka将整个项目打包成单个`.exe`文件。
  * **仓库结构 (Repository Structure)**: **Polyrepo**。本项目将存在于一个独立的Git仓库中。
  * **高层架构图 (High Level Architecture Diagram)**
    ```mermaid
    graph TD
        subgraph 用户设备
            User[用户] -- 交互 --> GUI[GUI 界面 (QML)];
            GUI -- 调用/绑定 --> AppLogic[应用逻辑 (Python/PySide6)];
            AppLogic -- 控制 --> AutomationService[自动化服务];
            AutomationService -- 操作 --> Browser[浏览器实例 (Playwright)];
        end
        Browser -- HTTP/S --> TargetWebsite[目标网站: wan.360.cn];
    ```
  * **架构与设计模式 (Architectural and Design Patterns)**
      * **视图与逻辑分离 (View-Logic Separation)**: 严格遵循QML（视图）和Python（逻辑）的分离模式，类似于MVVM，使UI和逻辑可以独立开发测试。
      * **服务层模式 (Service Layer Pattern)**: 核心的浏览器自动化和数据生成操作将被封装在专用的“服务”类中。
      * **单例模式 (Singleton Pattern)**: 用于管理应用配置等全局资源。

## **3. 技术栈 (Tech Stack)**

| 类别 | 技术 | 版本 | 目的 |
| :--- | :--- | :--- | :--- |
| 语言 | Python | 3.12 | 主要开发语言 |
| GUI框架 | PySide6 | \~6.7 | 构建桌面用户界面 |
| 浏览器自动化 | Playwright | \~1.44 | 模拟浏览器操作 |
| 依赖管理 | uv | \~0.1.40 | 项目依赖和虚拟环境管理 |
| 打包工具 | Nuitka | \~2.2 | 将项目打包为可执行文件 |
| 测试框架 | pytest | \~8.2 | 单元测试和集成测试 |

## **4. 数据模型 (Data Models)**

应用内核心的数据结构是一个账户对象，定义如下：

```python
# 在 src/models/account.py 中定义
from dataclasses import dataclass
from enum import Enum

class AccountStatus(Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    SUCCESS = "Success"
    FAILED = "Failed"

@dataclass
class Account:
    id: int
    username: str
    password: str
    status: AccountStatus = AccountStatus.QUEUED
    notes: str = ""
```

## **5. 核心组件 (Components)**

  * **GUI视图 (QML Files)**
      * **职责**: 负责界面的所有视觉呈现和布局。接收用户输入（如点击按钮）并将其传递给应用逻辑层。
  * **应用逻辑 (Python - `src/application.py`)**
      * **职责**: 作为QML视图和后端服务的“粘合剂”。处理UI事件，管理应用状态，调用后端服务并更新UI。
  * **自动化服务 (Python - `src/services/automation_service.py`)**
      * **职责**: 封装所有与Playwright相关的浏览器操作逻辑。提供如 `register_account(account)` 等接口。
  * **数据服务 (Python - `src/services/data_service.py`)**
      * **职责**: 负责处理数据，如从CSV文件导入账户，或生成随机账户列表。

## **6. 源代码目录结构 (Source Tree)**

基于选定的模板进行定制，最终结构如下：

```
reg-tool-project/
├── data/                  # 存放应用图标等静态资源
├── i18n/                  # (可选) 国际化语言文件
├── qt/
│   └── qml/               # QML界面文件
│       ├── main.qml
│       └── components/
├── src/
│   ├── models/            # 数据模型 (account.py)
│   │   └── __init__.py
│   ├── services/          # 后端服务
│   │   ├── __init__.py
│   │   ├── automation_service.py
│   │   └── data_service.py
│   ├── viewmodels/        # 连接QML和Python逻辑的视图模型
│   │   └── __init__.py
│   ├── main.py            # 应用主入口
│   └── application.py     # PySide6应用实例
├── test/                  # 测试文件
├── .gitignore
├── Justfile               # (可选) 命令运行器
├── pyproject.toml         # 项目配置与依赖 (uv)
└── README.md
```

## **7. 测试策略 (Test Strategy)**

  * **单元测试**: 使用 `pytest` 对 `services` 和 `models` 中的业务逻辑进行测试。浏览器操作将被模拟(mock)。
  * **集成测试**: 编写少量的测试，运行Playwright驱动的完整注册流程（可能针对一个本地或专用的测试网页），以验证端到端流程。

## **8. 错误处理与日志 (Error Handling & Logging)**

  * **错误处理**: `automation_service` 在遇到问题时（如元素找不到、用户名已存在、需要验证码）将抛出特定的自定义异常。`application` 层将捕获这些异常并更新UI以向用户显示明确的错误信息。
  * **日志**: 使用Python内置的 `logging` 模块。日志将被同时输出到UI的日志视图和本地的 `app.log` 文件中，方便调试。
