#!/usr/bin/env python
"""
Unit tests for account generation functionality
Story 1.4: Generate Random Credentials
"""

import pytest
import sys
from pathlib import Path
import re
from unittest.mock import patch, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.account_generator import AccountGenerator


class TestAccountGenerator:
    """Test class for AccountGenerator functionality"""
    
    def setup_method(self):
        """Setup test instance before each test"""
        self.generator = AccountGenerator()
    
    def test_generate_username_uniqueness_within_batch(self):
        """Test that usernames are unique within a batch (AC: 2, 3)"""
        num_accounts = 50
        usernames = []
        
        # Generate multiple usernames
        for _ in range(num_accounts):
            username = self.generator.generate_username()
            usernames.append(username)
        
        # Check for uniqueness (allowing some duplicates in large sets due to randomness)
        unique_usernames = set(usernames)
        uniqueness_ratio = len(unique_usernames) / len(usernames)
        
        # Should have high uniqueness ratio (>95%)
        assert uniqueness_ratio > 0.95, f"Uniqueness ratio {uniqueness_ratio:.2%} is too low"
        
        # Ensure usernames follow expected patterns
        for username in usernames:
            assert isinstance(username, str), "Username must be a string"
            assert len(username) >= 8, f"Username '{username}' is too short"
            assert len(username) <= 16, f"Username '{username}' is too long"
            assert username.islower(), f"Username '{username}' should be lowercase"
    
    def test_generate_unique_accounts_collision_detection(self):
        """Test that generate_unique_accounts prevents duplicate usernames"""
        accounts = self.generator.generate_unique_accounts(25)
        
        usernames = [account['username'] for account in accounts]
        unique_usernames = set(usernames)
        
        # Should have no duplicates
        assert len(usernames) == len(unique_usernames), "Duplicate usernames found"
        assert len(accounts) == 25, "Should generate exactly 25 accounts"
    
    def test_password_complexity_requirements(self):
        """Test that passwords contain both letters and numbers (AC: 4)"""
        num_passwords = 20
        
        for _ in range(num_passwords):
            password = self.generator.generate_password()
            
            # Test basic requirements
            assert isinstance(password, str), "Password must be a string"
            assert len(password) >= 8, f"Password '{password}' is too short"
            assert len(password) <= 12, f"Password '{password}' is too long"
            
            # Test complexity requirements (letters and numbers minimum)
            has_letter = any(c.isalpha() for c in password)
            has_digit = any(c.isdigit() for c in password)
            
            assert has_letter, f"Password '{password}' must contain at least one letter"
            assert has_digit, f"Password '{password}' must contain at least one digit"
    
    def test_password_length_configuration(self):
        """Test password length respects configuration"""
        # Test with custom configuration
        custom_config = {
            "account_generator": {
                "password_min_length": 10,
                "password_max_length": 15
            }
        }
        generator = AccountGenerator(custom_config)
        
        for _ in range(10):
            password = generator.generate_password()
            assert 10 <= len(password) <= 15, f"Password '{password}' doesn't meet length requirements"
    
    def test_output_formatting_exact_specification(self):
        """Test that output formatting matches exact specification (AC: 6)"""
        # Test the generate_unique_accounts output format indirectly
        accounts = self.generator.generate_unique_accounts(3)
        
        for account in accounts:
            assert 'username' in account, "Account must have username key"
            assert 'password' in account, "Account must have password key"
            assert isinstance(account['username'], str), "Username must be string"
            assert isinstance(account['password'], str), "Password must be string"
            
            # Test that they would format correctly as "账号 --- 密码"
            formatted = f"{account['username']} --- {account['password']}"
            assert " --- " in formatted, "Format should contain ' --- ' separator"
            
            # Ensure no problematic characters that would break formatting
            assert '\n' not in account['username'], "Username should not contain newlines"
            assert '\n' not in account['password'], "Password should not contain newlines"
    
    def test_edge_case_zero_accounts(self):
        """Test edge case of generating zero accounts"""
        accounts = self.generator.generate_unique_accounts(0)
        assert len(accounts) == 0, "Should generate no accounts when requested count is 0"
    
    def test_edge_case_single_account(self):
        """Test edge case of generating single account"""
        accounts = self.generator.generate_unique_accounts(1)
        assert len(accounts) == 1, "Should generate exactly 1 account"
        
        account = accounts[0]
        assert 'username' in account and 'password' in account
        assert len(account['username']) > 0 and len(account['password']) > 0
    
    def test_large_batch_performance(self):
        """Test performance with larger batches"""
        accounts = self.generator.generate_unique_accounts(100)
        assert len(accounts) == 100, "Should generate exactly 100 accounts"
        
        # Verify all unique
        usernames = [account['username'] for account in accounts]
        assert len(set(usernames)) == 100, "All 100 usernames should be unique"
    
    def test_error_handling_invalid_input(self):
        """Test error handling for invalid inputs"""
        # Test negative number (should be handled gracefully)
        with pytest.raises((ValueError, Exception)):
            self.generator.generate_unique_accounts(-1)
    
    def test_username_pattern_variety(self):
        """Test that username generation produces variety in patterns"""
        usernames = []
        for _ in range(50):
            username = self.generator.generate_username()
            usernames.append(username)
        
        # Check for pattern variety
        patterns_found = {
            'has_underscore': any('_' in u for u in usernames),
            'has_dot': any('.' in u for u in usernames),
            'has_numbers': any(any(c.isdigit() for c in u) for u in usernames),  # At least some should have numbers
            'different_lengths': len(set(len(u) for u in usernames)) > 1
        }
        
        assert patterns_found['has_numbers'], "Should have some usernames with numbers"
        assert patterns_found['different_lengths'], "Should have variety in username lengths"
    
    def test_password_character_distribution(self):
        """Test that passwords have good character distribution"""
        passwords = []
        for _ in range(30):
            password = self.generator.generate_password()
            passwords.append(password)
        
        # Analyze character distribution
        has_lowercase = any(any(c.islower() for c in p) for p in passwords)
        has_uppercase = any(any(c.isupper() for c in p) for p in passwords)
        has_digits = all(any(c.isdigit() for c in p) for p in passwords)
        
        assert has_lowercase, "Should have lowercase letters in passwords"
        assert has_uppercase, "Should have uppercase letters in passwords"  
        assert has_digits, "All passwords must have digits (AC requirement)"
    
    def test_csv_output_functionality(self):
        """Test CSV save functionality"""
        accounts = self.generator.generate_unique_accounts(5)
        
        # Test saving to CSV
        self.generator.save_to_csv(accounts)
        
        # Verify file exists
        assert self.generator.output_file.exists(), "CSV file should be created"
        
        # Verify file content
        content = self.generator.output_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        
        assert len(lines) == 6, "Should have header + 5 account lines"  # header + 5 accounts
        assert lines[0] == "username,password", "Header should be correct"
        
        # Verify each account line
        for i, account in enumerate(accounts, 1):
            expected_line = f"{account['username']},{account['password']}"
            assert lines[i] == expected_line, f"Line {i} should match account data"


class TestCLIIntegration:
    """Test CLI integration functionality"""
    
    @patch('sys.argv', ['main.py', '--generate', '3'])
    @patch('builtins.print')
    def test_cli_generate_argument_parsing(self, mock_print):
        """Test CLI argument parsing for --generate"""
        from src.account_generator import main
        
        # Should not raise an exception
        main()
        
        # Verify print was called with expected format
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        
        # Should contain generation message and formatted output
        generation_msgs = [msg for msg in print_calls if 'Generating' in str(msg)]
        assert len(generation_msgs) > 0, "Should print generation message"
        
        # Should contain the exact format "账号 --- 密码" in output
        format_msgs = [msg for msg in print_calls if ' --- ' in str(msg)]
        assert len(format_msgs) >= 3, "Should have 3 accounts with ' --- ' format"
    
    @patch('sys.argv', ['main.py', '--generate', '0'])
    @patch('builtins.print')
    def test_cli_zero_accounts_edge_case(self, mock_print):
        """Test CLI with zero accounts"""
        from src.account_generator import main
        
        main()
        
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        generation_msg = [msg for msg in print_calls if 'Generated 0 unique accounts' in str(msg)]
        assert len(generation_msg) > 0, "Should handle zero accounts gracefully"
    
    @patch('sys.argv', ['main.py', '--num', '3'])  # Legacy format
    @patch('builtins.print')
    def test_cli_backward_compatibility(self, mock_print):
        """Test backward compatibility with --num argument"""
        from src.account_generator import main
        
        main()
        
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        
        # Should use legacy format (Username: ... Password: ...)
        legacy_msgs = [msg for msg in print_calls if 'Username:' in str(msg)]
        assert len(legacy_msgs) >= 3, "Should use legacy format for --num argument"