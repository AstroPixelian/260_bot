#!/usr/bin/env python3
"""
Nuitka 打包脚本 - 将 rich_cli.py 打包成独立的 Windows exe 文件
Build script for packaging rich_cli.py into standalone Windows exe using Nuitka
"""

import subprocess
import sys
import os
from pathlib import Path
import shutil

def check_nuitka():
    """检查 Nuitka 是否已安装"""
    try:
        result = subprocess.run([sys.executable, "-m", "nuitka", "--version"], 
                              capture_output=True, text=True)
        print(f"✅ Nuitka 版本: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print("❌ Nuitka 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "nuitka>=2.7.13"])
        return True
    except Exception as e:
        print(f"❌ 检查 Nuitka 失败: {e}")
        return False

def build_exe():
    """使用 Nuitka 构建 exe 文件"""
    
    # 项目根目录
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    rich_cli_path = src_dir / "rich_cli.py"
    
    if not rich_cli_path.exists():
        print(f"❌ 找不到源文件: {rich_cli_path}")
        return False
    
    print("🚀 开始使用 Nuitka 打包...")
    
    # Nuitka 构建命令
    nuitka_cmd = [
        sys.executable, "-m", "nuitka",
        
        # 基本选项
        "--standalone",                    # 独立可执行文件
        "--onefile",                      # 单文件模式
        "--assume-yes-for-downloads",     # 自动同意下载
        "--show-progress",                # 显示进度
        "--show-memory",                  # 显示内存使用
        
        # 输出选项
        "--output-filename=360-账号批量注册工具.exe",
        "--output-dir=dist",
        
        # Windows 特定选项
        "--windows-console-mode=attach",  # 附加到控制台
        "--enable-console",              # 启用控制台输出
        
        # 包含路径和模块
        f"--include-package-data=faker",     # Faker 数据文件
        f"--include-package-data=rich",      # Rich 资源文件
        f"--include-package=transitions",    # 状态机
        f"--include-package=pandas",         # 数据处理
        f"--include-package=filelock",       # 文件锁
        
        # Playwright 相关 (关键!)
        f"--include-package=playwright",     # Playwright 核心
        "--include-package-data=playwright", # Playwright 数据文件
        
        # 添加项目源码路径
        f"--include-plugin-directory={src_dir}",
        
        # 性能选项
        "--lto=no",                      # 禁用链接时优化 (避免 Playwright 问题)
        "--jobs=4",                      # 并行编译
        
        # 调试选项 (可选，发布时可移除)
        # "--debug",
        # "--verbose",
        
        # 源文件
        str(rich_cli_path)
    ]
    
    print("📝 Nuitka 命令:")
    print(" ".join(nuitka_cmd))
    print()
    
    try:
        # 执行构建
        result = subprocess.run(nuitka_cmd, cwd=project_root, check=True)
        print("✅ Nuitka 构建成功!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Nuitka 构建失败: {e}")
        print("\n🔍 常见解决方案:")
        print("1. 确保安装了最新版本的 Nuitka")
        print("2. 检查 Python 版本兼容性")
        print("3. 尝试清理缓存: rm -rf ~/.nuitka/")
        return False
    
    except Exception as e:
        print(f"❌ 构建过程发生异常: {e}")
        return False

def create_playwright_installer():
    """创建 Playwright 浏览器安装脚本"""
    
    installer_script = '''@echo off
chcp 65001 > nul
echo 正在安装 Playwright 浏览器...
echo Installing Playwright browsers...
echo.

REM 设置环境变量
set PLAYWRIGHT_SKIP_BROWSER_GC=1

REM 安装浏览器 (自动选择合适的版本)
echo 🔧 正在下载和安装 Chromium 浏览器...
playwright install chromium

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ 浏览器安装失败!
    echo    请手动运行: playwright install chromium
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Playwright 浏览器安装完成!
echo    现在可以运行 360-账号批量注册工具.exe
echo.
pause
'''
    
    installer_path = Path("dist/安装浏览器.bat")
    installer_path.parent.mkdir(exist_ok=True)
    
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_script)
    
    print(f"✅ 创建了浏览器安装脚本: {installer_path}")

def create_usage_readme():
    """创建用户使用说明"""
    
    readme_content = '''# 360 账号批量注册工具 - 使用说明

## 📦 文件说明

- `360-账号批量注册工具.exe` - 主程序
- `安装浏览器.bat` - 首次使用必须运行此脚本安装浏览器

## 🚀 首次使用步骤

1. **安装浏览器** (重要!)
   ```
   双击运行 "安装浏览器.bat"
   等待浏览器下载和安装完成
   ```

2. **运行主程序**
   ```
   双击运行 "360-账号批量注册工具.exe"
   按照界面提示操作
   ```

## ⚙️ 功能特性

- 🎨 **Rich 界面**: 美观的终端界面，支持实时日志显示
- 📊 **批量处理**: 支持 1-100 个账号批量注册
- 🔄 **实时反馈**: 注册过程实时显示进度和日志
- 💾 **结果保存**: 自动保存注册结果到 CSV 文件
- 🎯 **智能生成**: 自动生成符合360平台要求的账号信息

## 📋 操作流程

1. 启动程序后显示欢迎界面
2. 配置注册数量 (1-100)
3. 选择是否启用详细日志显示
4. 确认配置信息
5. 自动开始批量注册
6. 实时查看进度和日志
7. 完成后查看结果统计

## ⚠️ 注意事项

- **首次运行必须安装浏览器**
- 程序需要网络连接
- 建议在稳定的网络环境下使用
- 注册过程中可能遇到验证码，按提示操作即可

## 🐛 故障排除

### 程序无法启动
1. 确保已运行 "安装浏览器.bat"
2. 检查网络连接
3. 以管理员身份运行

### 浏览器相关错误
1. 重新运行 "安装浏览器.bat"
2. 清理临时文件后重试
3. 确保有足够的磁盘空间

### 注册失败
1. 检查网络连接状态
2. 稍后重试（可能是服务器繁忙）
3. 启用详细日志查看具体错误信息

## 📊 输出文件

程序会生成以下文件：
- `registration_results_YYYYMMDD_HHMMSS.csv` - 注册结果详情
- 临时日志文件 (程序退出后自动清理)

## 💡 使用技巧

1. **开启详细日志**: 可以看到实时的注册过程
2. **批量数量**: 建议每次不超过50个账号以提高成功率
3. **网络环境**: 使用稳定的网络连接可提高成功率

---

如有问题请查看日志输出或联系开发者。
'''
    
    readme_path = Path("dist/使用说明.txt")
    readme_path.parent.mkdir(exist_ok=True)
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print(f"✅ 创建了使用说明: {readme_path}")

def main():
    """主函数"""
    print("🎯 360 账号批量注册工具 - Nuitka 打包脚本")
    print("=" * 50)
    
    # 检查 Nuitka
    if not check_nuitka():
        return False
    
    # 构建 exe
    if not build_exe():
        return False
    
    # 创建辅助文件
    print("\n📝 创建辅助文件...")
    create_playwright_installer()
    create_usage_readme()
    
    print("\n🎉 打包完成!")
    print("\n📦 生成的文件:")
    print("  📁 dist/")
    print("    ├─ 360-账号批量注册工具.exe")
    print("    ├─ 安装浏览器.bat")
    print("    └─ 使用说明.txt")
    
    print("\n✅ 下一步:")
    print("1. 将整个 dist 文件夹分发给用户")
    print("2. 用户首次使用需要运行 '安装浏览器.bat'")
    print("3. 然后就可以直接运行主程序了")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)