# 360 Batch Account Creator - 多语言支持

## 概述

360批量账号注册工具现在支持多语言界面，包括中文和英文。用户可以在运行时动态切换语言。

## 支持的语言

- **English** (en-US) - 英文
- **中文** (zh-CN) - 中文简体

## 如何使用

### 1. 启动应用程序
```bash
python main.py
# 或者
python src/batch_creator_gui.py
```

### 2. 切换语言
1. 点击菜单栏中的"设置"或"Settings"
2. 选择"语言"或"Language"子菜单
3. 点击所需的语言（中文或English）
4. 界面将立即切换到选定的语言

### 3. 语言自动检测
应用程序会自动检测系统语言：
- 如果系统语言是中文，默认使用中文界面
- 如果系统语言是英文或其他语言，默认使用英文界面
- 用户的语言选择会被保存，下次启动时自动使用上次选择的语言

## 技术实现

### 核心组件

1. **翻译管理器** (`src/translation_manager.py`)
   - 负责加载和管理翻译文件
   - 处理语言切换逻辑
   - 提供便捷的翻译函数

2. **翻译文件**
   - `i18n/zh-CN.ts` - 中文翻译源文件
   - `i18n/zh-CN.qm` - 中文翻译编译文件
   - `i18n/en-US.ts` - 英文翻译源文件
   - `i18n/en-US.qm` - 英文翻译编译文件

3. **GUI集成**
   - 所有界面文本使用 `tr()` 函数标记为可翻译
   - 支持运行时语言切换
   - 菜单栏集成语言选择功能

### 翻译的界面元素

- 窗口标题
- 所有按钮文本和工具提示
- 菜单和子菜单
- 表格标题
- 状态信息和进度显示
- 对话框和消息框
- 日志消息

## 开发者指南

### 添加新的可翻译文本

1. 在代码中使用 `tr()` 函数：
```python
from src.translation_manager import tr

# 简单翻译
text = tr("Hello World")

# 带上下文的翻译（推荐）
text = tr("Save", "ButtonText")
```

2. 更新翻译文件：
```bash
# 扫描代码并更新 .ts 文件
just update-translations

# 或手动运行
pyside6-lupdate -project project.json
```

3. 编辑翻译文件：
```bash
# 使用 Qt Linguist 编辑翻译
linguist i18n/zh-CN.ts
```

4. 编译翻译文件：
```bash
# 编译为 .qm 文件
pyside6-lrelease i18n/zh-CN.ts -qm i18n/zh-CN.qm
```

### 添加新语言

1. 创建新语言的翻译文件：
```bash
just add-translation ja-JP  # 例：日文
```

2. 在翻译管理器中注册新语言：
```python
# 在 translation_manager.py 中更新 available_languages
self.available_languages = {
    'en-US': {'name': 'English', 'display_name': 'English'},
    'zh-CN': {'name': 'Chinese', 'display_name': '中文'},
    'ja-JP': {'name': 'Japanese', 'display_name': '日本語'},  # 新语言
}
```

## 测试

运行以下脚本测试多语言功能：

```bash
# 测试核心翻译功能（无GUI）
python test_translation_core.py

# 测试完整GUI功能（有界面）
python test_i18n.py
```

## 文件结构

```
├── i18n/                      # 翻译文件目录
│   ├── zh-CN.ts              # 中文翻译源文件
│   ├── zh-CN.qm              # 中文翻译编译文件
│   ├── en-US.ts              # 英文翻译源文件
│   └── en-US.qm              # 英文翻译编译文件
├── src/
│   ├── translation_manager.py # 翻译管理器
│   └── batch_creator_gui.py   # 主GUI（已集成多语言）
├── test_translation_core.py   # 核心翻译测试
└── test_i18n.py              # GUI翻译测试
```

## 注意事项

1. **字体兼容性**: 确保系统安装了支持中文显示的字体
2. **编码格式**: 所有翻译文件使用UTF-8编码
3. **翻译更新**: 修改翻译后需要重新编译.qm文件
4. **上下文管理**: 使用适当的翻译上下文避免歧义

## 故障排除

### 翻译不显示
1. 检查.qm文件是否存在
2. 检查翻译文件是否编译成功
3. 验证翻译管理器是否正确初始化

### 乱码问题
1. 确认文件编码为UTF-8
2. 检查系统是否支持中文显示
3. 验证字体设置

### 语言切换失败
1. 检查翻译文件路径
2. 验证翻译管理器配置
3. 查看控制台错误信息