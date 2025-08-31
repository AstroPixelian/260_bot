# **4. 技术栈 (Updated Tech Stack)**

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

## ** 技术栈选择理由**
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