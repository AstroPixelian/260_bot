# **4. 技术实现 (Technical Implementation)**

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
