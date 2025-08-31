# AutomationService Backend Support

The `AutomationService` class now supports two different automation backends:

1. **Playwright** (default) - Fast, reliable, good for development
2. **Selenium with undetected_chromedriver** - Better anti-detection, bypasses more bot protection

## Installation

### Playwright (Default)
Already included in the project dependencies.

### Selenium Backend
```bash
pip install undetected-chromedriver
```

## Usage

### Basic Backend Selection

```python
from src.services.automation_service import AutomationService

# Use default playwright backend
service = AutomationService()

# Use selenium backend
service = AutomationService(backend="selenium")

# Check available backends
print(service.get_available_backends())  # ['playwright', 'selenium'] if selenium installed

# Switch backends (only when not running)
service.set_backend("selenium")
```

### Account Registration

Both backends use the same interface:

```python
# Set up callbacks
service.set_callbacks(
    on_log_message=lambda msg: print(f"LOG: {msg}"),
    on_account_start=lambda acc: print(f"Starting: {acc.username}"),
    on_account_complete=lambda acc: print(f"Complete: {acc.username} - {acc.status}")
)

# Register a single account (works with both backends)
account = Account(id=1, username="testuser", password="testpass123!")
success = await service.register_single_account(account)
```

### Batch Processing

The batch processing workflow works identically with both backends:

```python
accounts = service.generate_test_accounts(5)

# Start batch processing
service.start_batch_registration(accounts)

# Process accounts one by one
while service.process_next_account(accounts):
    service.complete_current_account(accounts)
    # Add delay between accounts if needed
    time.sleep(1)
```

## Backend Comparison

| Feature | Playwright | Selenium/UC |
|---------|------------|-------------|
| Speed | Fast | Moderate |
| Anti-detection | Good | Excellent |
| Stability | High | High |
| Resource usage | Low | Moderate |
| Setup complexity | Simple | Simple |
| Bot detection bypass | Standard | Advanced |

## Best Practices

1. **Use Playwright for development and testing** - faster feedback loop
2. **Use Selenium for production** - better success rates against anti-bot systems
3. **Always test both backends** - ensures compatibility
4. **Handle backend switching gracefully** - check availability before switching
5. **Monitor success rates** - switch backends if one performs better

## Error Handling

```python
try:
    service.set_backend("selenium")
except ImportError as e:
    print(f"Selenium not available: {e}")
    # Fall back to playwright
    service.set_backend("playwright")
except ValueError as e:
    print(f"Cannot switch backend: {e}")
    # Backend switching not allowed while running
```

## Advanced Configuration

### Selenium-specific Methods

```python
# Only available when using selenium backend
if service.get_backend() == "selenium":
    success = service.register_single_account_selenium(account)
```

### Custom Chrome Options

The selenium backend automatically configures undetected_chromedriver with optimal anti-detection settings. The configuration includes:

- Disabled automation flags
- Anti-fingerprinting measures  
- Realistic browser arguments
- Proper window sizing
- Background process management

## Troubleshooting

### Common Issues

1. **"Selenium backend not available"** - Install undetected-chromedriver
2. **"Cannot change backend while running"** - Stop automation first
3. **Chrome driver version mismatch** - Update undetected-chromedriver
4. **High resource usage** - Consider adjusting batch size or adding delays

### Debug Logging

Both backends provide extensive debug logging through the callback system:

```python
def debug_callback(message: str):
    if "DEBUG:" in message:
        print(f"[DEBUG] {message}")

service.set_callbacks(on_log_message=debug_callback)
```

## Example Script

See `example_selenium_usage.py` for a complete working example that demonstrates:

- Backend availability checking
- Switching between backends
- Account generation and registration
- Error handling and logging
- Success rate comparison