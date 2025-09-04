#!/usr/bin/env python3
"""
PyInstaller 打包脚本 - 替代 Nuitka 的方案
PyInstaller Build Script - Alternative to Nuitka
"""

import subprocess
import sys
import os
from pathlib import Path

def build_with_pyinstaller():
    """使用 PyInstaller 构建 exe 文件"""
    
    # 项目根目录
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    rich_cli_path = src_dir / "rich_cli.py"
    
    if not rich_cli_path.exists():
        print(f"❌ 找不到源文件: {rich_cli_path}")
        return False
    
    print("🚀 开始使用 PyInstaller 打包...")
    
    # PyInstaller 构建命令
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        
        # 基本选项
        "--onefile",                    # 单文件模式
        "--windowed",                   # Windows GUI 模式
        "--name=360-账号批量注册工具",
        
        # 路径选项
        f"--distpath=dist",
        f"--workpath=build",
        f"--specpath=build",
        
        # 包含数据和模块
        f"--add-data={src_dir};src",
        "--hidden-import=playwright",
        "--hidden-import=playwright.async_api",
        "--hidden-import=transitions",
        "--hidden-import=rich",
        "--hidden-import=faker",
        "--hidden-import=pandas",
        "--hidden-import=filelock",
        
        # 排除不需要的模块
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        
        # Windows 特定
        "--console",                    # 保留控制台
        
        # 源文件
        str(rich_cli_path)
    ]
    
    try:
        # 执行构建
        result = subprocess.run(pyinstaller_cmd, cwd=project_root, check=True)
        print("✅ PyInstaller 构建成功!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ PyInstaller 构建失败: {e}")
        return False

def main():
    """主函数"""
    print("🎯 PyInstaller 打包脚本 (Nuitka 替代方案)")
    print("=" * 50)
    
    # 检查 PyInstaller
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                      capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 构建
    if build_with_pyinstaller():
        print("\n🎉 打包完成!")
        print("\n📝 注意: PyInstaller 在 macOS 上同样无法生成 Windows exe")
        print("       建议使用 GitHub Actions 进行跨平台构建")
    
    return True

if __name__ == "__main__":
    main()