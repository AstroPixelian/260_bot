# CLI 使用手册 - Command Line Interface Usage Guide

## 📋 概述 | Overview

360账户批量创建工具的命令行界面为开发者和高级用户提供了一个快速、简洁的方式来注册单个账户，无需启动完整的图形用户界面。

The CLI interface for 360 Account Batch Creator provides developers and advanced users with a fast, streamlined way to register individual accounts without launching the full GUI.

## 🚀 Quick Start

### 基本用法 | Basic Usage

```bash
# 基本注册命令 | Basic registration command
python main.py --username <用户名> --password <密码>

# 示例 | Example
python main.py --username testuser123 --password mySecurePass123
```

### 获取帮助 | Get Help

```bash
python main.py --help
```

## 📖 详细使用说明 | Detailed Usage Instructions

### 1. 环境要求 | Prerequisites

确保您已经：
- 安装了Python 3.12或更高版本
- 安装了项目依赖 (`uv sync` 或类似命令)
- 浏览器环境已配置(CLI会自动启动浏览器进行注册)

Make sure you have:
- Python 3.12 or higher installed
- Project dependencies installed (`uv sync` or similar)
- Browser environment configured (CLI automatically launches browser for registration)

### 2. 命令参数 | Command Parameters

| 参数 Parameter | 必需 Required | 描述 Description |
|----------------|---------------|-------------------|
| `--username` | ✅ 是 Yes | 注册用户名 (Registration username) |
| `--password` | ✅ 是 Yes | 注册密码 (最少6位字符 - min 6 characters) |
| `--help` / `-h` | ❌ 否 No | 显示帮助信息 (Show help message) |

### 3. 使用示例 | Usage Examples

#### 成功注册 | Successful Registration
```bash
$ python main.py --username john_doe123 --password SecurePass2024

Starting registration for account: john_doe123
Success
```

#### 密码太短错误 | Password Too Short Error
```bash
$ python main.py --username testuser --password short

Error: Password must be at least 6 characters long
```

#### 用户名为空错误 | Empty Username Error
```bash
$ python main.py --username "" --password validPassword123

Error: Username cannot be empty
```

#### 注册失败 | Registration Failure
```bash
$ python main.py --username existinguser --password validPass123

Starting registration for account: existinguser
Error: Username already exists
```

## 🧪 测试用账户生成 | Test Account Generation

**重要 | Important**: 为了安全起见，请使用内置的账户生成器来创建测试账户，而不是使用真实的个人信息。

For security purposes, use the built-in account generator to create test accounts instead of using real personal information.

### 生成测试账户 | Generate Test Accounts

```bash
# 生成单个测试账户 | Generate a single test account
python src/account_generator.py --num 1

# 生成10个测试账户 | Generate 10 test accounts
python src/account_generator.py --num 10
```

### 使用生成的账户 | Using Generated Accounts

生成的账户会保存在 `output/accounts.csv` 文件中：

```bash
# 查看生成的账户 | View generated accounts
cat output/accounts.csv

# 使用生成的账户进行测试 | Use generated account for testing
python main.py --username john_doe1234 --password XyZ9#mK2$qR8
```

## 🔧 高级功能 | Advanced Features

### 退出码 | Exit Codes

CLI遵循标准的退出码约定：
- `0`: 注册成功 | Registration successful
- `1`: 注册失败或错误 | Registration failed or error occurred

```bash
# 检查最后一次操作的结果 | Check result of last operation
echo $?  # Linux/Mac
echo %ERRORLEVEL%  # Windows
```

### 脚本集成 | Script Integration

CLI可以轻松集成到Shell脚本中：

```bash
#!/bin/bash
# 批量注册脚本示例 | Example batch registration script

# 从CSV文件读取账户并注册 | Read accounts from CSV and register
while IFS=',' read -r username password; do
    echo "Registering: $username"
    if python main.py --username "$username" --password "$password"; then
        echo "✅ Success: $username"
    else
        echo "❌ Failed: $username"
    fi
    sleep 2  # 避免请求过快 | Avoid too frequent requests
done < accounts.csv
```

### 静默模式集成 | Silent Mode Integration

虽然CLI已经保持了简洁的输出，但您可以进一步控制输出：

```bash
# 只显示错误 | Show only errors
python main.py --username test --password valid123 2>&1 >/dev/null

# 记录所有输出到文件 | Log all output to file
python main.py --username test --password valid123 > registration.log 2>&1
```

## ⚠️ 注意事项 | Important Notes

### 安全建议 | Security Recommendations

1. **测试用账户 | Test Accounts**: 
   - ✅ 使用 `src/account_generator.py` 生成测试账户
   - ❌ 不要使用真实的个人账户信息

2. **密码安全 | Password Security**:
   - 密码最少6个字符 | Minimum 6 characters
   - 避免在Shell历史中保存密码 | Avoid saving passwords in shell history
   - 考虑使用环境变量 | Consider using environment variables

```bash
# 使用环境变量 | Using environment variables
export TEST_USERNAME="generated_user123"
export TEST_PASSWORD="SecureTestPass456"
python main.py --username "$TEST_USERNAME" --password "$TEST_PASSWORD"
```

### 性能考虑 | Performance Considerations

- CLI每次运行都会启动一个新的浏览器实例
- 建议在注册间隔之间等待2-3秒以避免被限制
- 对于大批量注册，考虑使用GUI版本的批量功能

- CLI starts a new browser instance for each run
- Recommend waiting 2-3 seconds between registrations to avoid rate limiting
- For large batch registrations, consider using the GUI version's batch functionality

## 🐛 故障排除 | Troubleshooting

### 常见问题 | Common Issues

#### 1. 浏览器启动失败 | Browser Launch Failure
```bash
Error: Failed to initialize browser
```

**解决方案 | Solution**:
```bash
# 检查Playwright是否已安装 | Check if Playwright is installed
pip show playwright

# 安装浏览器 | Install browsers
playwright install
```

#### 2. 模块导入错误 | Module Import Error
```bash
ModuleNotFoundError: No module named 'src.cli'
```

**解决方案 | Solution**:
```bash
# 确保从项目根目录运行 | Make sure to run from project root
cd /path/to/tanke_260_bot
python main.py --username test --password test123
```

#### 3. 权限错误 | Permission Error
```bash
PermissionError: [Errno 13] Permission denied
```

**解决方案 | Solution**:
```bash
# 检查文件权限 | Check file permissions
chmod +x main.py

# 或者明确使用python | Or explicitly use python
python main.py --username test --password test123
```

### 调试模式 | Debug Mode

虽然CLI没有内置调试标志，但您可以通过以下方式获得更多信息：

```bash
# 启用Python详细输出 | Enable Python verbose output
python -v main.py --username test --password test123

# 查看所有Python警告 | Show all Python warnings
python -W all main.py --username test --password test123
```

## 📚 相关文档 | Related Documentation

- **完整GUI用户手册**: GUI版本的详细使用说明
- **开发者文档**: `docs/architecture/` - 技术架构文档
- **测试策略**: `docs/architecture/test-strategy.md` - 测试相关信息
- **故事文档**: `docs/stories/1.3.cli-interface.md` - CLI功能的技术实现详情

## 💡 最佳实践 | Best Practices

### 1. 自动化脚本 | Automation Scripts
```bash
# 创建可重复使用的注册函数 | Create reusable registration function
register_account() {
    local username=$1
    local password=$2
    echo "🔄 Registering: $username"
    
    if python main.py --username "$username" --password "$password"; then
        echo "✅ Successfully registered: $username"
        return 0
    else
        echo "❌ Failed to register: $username"
        return 1
    fi
}

# 使用函数 | Use the function
register_account "testuser1" "securepass123"
```

### 2. 错误处理 | Error Handling
```bash
# 带有重试机制的注册 | Registration with retry mechanism
register_with_retry() {
    local username=$1
    local password=$2
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt/$max_attempts for $username"
        
        if python main.py --username "$username" --password "$password"; then
            echo "Success on attempt $attempt"
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            echo "Failed, waiting before retry..."
            sleep 5
        fi
        
        ((attempt++))
    done
    
    echo "Failed after $max_attempts attempts"
    return 1
}
```

### 3. 日志记录 | Logging
```bash
# 带时间戳的日志记录 | Timestamped logging
log_registration() {
    local username=$1
    local password=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local logfile="registration-$(date +%Y%m%d).log"
    
    echo "[$timestamp] Starting registration for: $username" >> "$logfile"
    
    if python main.py --username "$username" --password "$password" 2>&1 | tee -a "$logfile"; then
        echo "[$timestamp] SUCCESS: $username" >> "$logfile"
    else
        echo "[$timestamp] FAILED: $username" >> "$logfile"
    fi
}
```

---

## 📞 支持 | Support

如果您在使用CLI时遇到问题，请：
1. 检查此文档的故障排除部分
2. 查看项目的GitHub Issues
3. 确保使用生成的测试账户而非真实账户

If you encounter issues using the CLI:
1. Check the troubleshooting section in this document  
2. Review the project's GitHub Issues
3. Ensure you're using generated test accounts, not real accounts

**版本**: CLI v1.0 (对应 Story 1.3)
**最后更新**: 2025-08-31