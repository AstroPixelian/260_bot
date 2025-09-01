#!/usr/bin/python
# -*- coding: utf-8 -*-
import random
import string
from pathlib import Path
from faker import Faker


class AccountGenerator:
    def __init__(self, config=None):
        """Initialize generator with configuration."""
        self.config = config or {}
        self.fake = Faker('en_US')  # Initialize Faker with English locale
        
        self.output_dir = Path("output")
        self.output_file = self.output_dir / "accounts.csv"

        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)

    def generate_username(self):
        """Generate a realistic and diverse username using Faker."""
        config = self.config.get("account_generator", {})
        min_length = config.get("username_min_length", 8)
        max_length = config.get("username_max_length", 16)
        
        # More diverse and realistic username patterns with higher uniqueness
        patterns = [
            # Basic name combinations with numbers
            lambda: self.fake.first_name().lower() + str(random.randint(100, 9999)),
            lambda: self.fake.last_name().lower() + str(random.randint(10, 999)),
            lambda: self.fake.first_name().lower() + self.fake.last_name().lower() + str(random.randint(1, 99)),
            
            # Name with separators and numbers
            lambda: self.fake.first_name().lower() + "_" + str(random.randint(1000, 9999)),
            # lambda: self.fake.first_name().lower() + "." + self.fake.last_name().lower() + str(random.randint(1, 999)),
            lambda: self.fake.first_name().lower() + "_" + self.fake.last_name().lower() + str(random.randint(10, 99)),
            
            # Multiple word combinations
            lambda: self.fake.first_name().lower() + self.fake.color_name().lower() + str(random.randint(1, 999)),
            lambda: self.fake.first_name().lower() + random.choice(["pro", "dev", "user", "player", "master"]) + str(random.randint(1, 999)),
            lambda: random.choice(["the", "cool", "real", "pro"]) + self.fake.first_name().lower() + str(random.randint(1, 9999)),
            
            # Year-based combinations (realistic birth years)
            lambda: self.fake.first_name().lower() + str(random.randint(1990, 2005)),
            lambda: self.fake.last_name().lower() + str(random.randint(1985, 2000)),
            lambda: self.fake.first_name().lower() + "_" + str(random.randint(1992, 2003)),
            
            # Initial + name + numbers
            lambda: self.fake.first_name().lower()[0] + self.fake.last_name().lower() + str(random.randint(100, 9999)),
            lambda: self.fake.first_name().lower()[0] + "_" + self.fake.last_name().lower() + str(random.randint(10, 999)),
            
            # Double numbers for more uniqueness
            lambda: self.fake.first_name().lower() + str(random.randint(10, 99)) + str(random.randint(10, 99)),
            lambda: self.fake.last_name().lower() + str(random.randint(100, 999)) + str(random.randint(10, 99)),
            
            # Common username patterns with numbers
            lambda: self.fake.first_name().lower() + random.choice(["123", "456", "789", "321", "999", "777", "888"]),
            lambda: random.choice(["user", "player", "gamer"]) + self.fake.first_name().lower() + str(random.randint(1, 9999)),
            
            # Random date-based (month+day combinations)
            lambda: self.fake.first_name().lower() + str(random.randint(1, 12)) + str(random.randint(1, 31)),
            lambda: self.fake.last_name().lower() + str(random.randint(101, 1231)),  # MMDD format
            
            # Faker's built-in user_name for variety
            lambda: self.fake.user_name(),
            lambda: self.fake.user_name() + str(random.randint(1, 999)),
        ]
        
        username = random.choice(patterns)()
        
        # Clean up any potential issues
        username = username.replace(" ", "").replace("-", "_")
        
        # Ensure username meets length requirements
        while len(username) < min_length:
            username += str(random.randint(0, 9))
        
        if len(username) > max_length:
            username = username[:max_length]
        
        return username.lower()

    def generate_password(self):
        """Generate a random password containing letters and numbers (AC requirement)."""
        config = self.config.get("account_generator", {})
        # Set default length to around 10 characters as specified in story
        min_length = config.get("password_min_length", 8)
        max_length = config.get("password_max_length", 12)
        length = random.randint(min_length, max_length)
        
        # Basic character sets - letters and numbers as minimum requirement
        letters = string.ascii_lowercase + string.ascii_uppercase
        numbers = string.digits
        special_chars = config.get("password_special_chars", "!@#$%^&*")
        
        # Generate password ensuring it contains both letters and numbers
        password = ""
        
        # Ensure at least one letter and one number
        password += random.choice(letters)
        password += random.choice(numbers)
        
        # Fill the rest with random chars from all sets
        all_chars = letters + numbers + special_chars
        for _ in range(length - 2):
            password += random.choice(all_chars)
        
        # Shuffle the password to randomize positions
        password_list = list(password)
        random.shuffle(password_list)
        password = ''.join(password_list)
        
        # Final validation to ensure complexity requirements
        password = self._ensure_password_complexity(password)
        return password

    def _ensure_password_complexity(self, password):
        """Ensure password meets complexity requirements (letters + numbers minimum).
        
        This method guarantees passwords contain at least one lowercase letter,
        one uppercase letter, and one digit as per AC requirements.
        """
        config = self.config.get("account_generator", {})
        
        # Ensure minimum requirements: letters and numbers (AC requirement)
        if not any(c.islower() for c in password):
            password = password[:-1] + random.choice(string.ascii_lowercase)
        if not any(c.isupper() for c in password):
            password = password[:-1] + random.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + random.choice(string.digits)
        
        # Only enforce special characters if explicitly configured
        special_chars = config.get("password_special_chars", "")
        if special_chars and not any(c in special_chars for c in password):
            password = password[:-1] + random.choice(special_chars)
        
        return password

    def generate_unique_accounts(self, num_accounts) -> list[dict]:
        """Generate specified number of accounts with username uniqueness guarantee.
        
        Args:
            num_accounts (int): Number of accounts to generate (must be non-negative)
            
        Returns:
            list[dict]: List of account dictionaries with 'username' and 'password' keys
            
        Raises:
            ValueError: If num_accounts is negative
        """
        if num_accounts < 0:
            raise ValueError("Number of accounts must be non-negative")
        
        try:
            accounts = []
            used_usernames = set()
            # Reasonable retry limit to prevent infinite loops
            max_attempts = num_accounts * 5 if num_accounts > 0 else 0
            attempts = 0
            
            print(f"Generating {num_accounts} unique accounts...")
            
            while len(accounts) < num_accounts and attempts < max_attempts:
                username = self.generate_username()
                attempts += 1
                
                # Skip duplicate usernames within this batch
                if username in used_usernames:
                    continue
                
                used_usernames.add(username)
                account = {
                    "username": username,
                    "password": self.generate_password()
                }
                accounts.append(account)
            
            # Warn if we couldn't generate the requested number of unique accounts
            if len(accounts) < num_accounts:
                print(f"Warning: Only generated {len(accounts)} unique accounts out of {num_accounts} requested")
            else:
                print(f"Generated {num_accounts} unique accounts")
                
            return accounts
        except Exception as e:
            print(f"Error generating unique accounts: {str(e)}")
            raise

    def generate_accounts(self, num_accounts) -> list[dict]:
        """Generate specified number of accounts and save to CSV."""
        try:
            accounts = []
            print(f"Generating {num_accounts} accounts...")
            for _ in range(num_accounts):
                account = {
                    "username": self.generate_username(),
                    "password": self.generate_password()
                }
                accounts.append(account)
            print(f"Generated {num_accounts} accounts")
            return accounts
        except Exception as e:
            print(f"Error generating accounts: {str(e)}")
            raise
    
    def save_to_csv(self, accounts):
        """Save accounts to CSV file"""
        # Save to file using custom separator to avoid comma conflicts
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write("username,password\n")
            for account in accounts:
                f.write(f"{account['username']},{account['password']}\n")
        print(f"Generated accounts are saved to {self.output_file}")
        return accounts

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate random accounts and save to CSV.")
    parser.add_argument("--generate", type=int, help="Number of accounts to generate (outputs in '账号 --- 密码' format)")
    parser.add_argument("--num", type=int, default=10, help="Number of accounts to generate")
    parser.add_argument("--save-csv", action="store_true", help="Save accounts to CSV file (default: False)")
    parser.add_argument("--output", type=str, default="accounts.csv", help="Output CSV filename (default: accounts.csv)")
    args = parser.parse_args()

    generator = AccountGenerator()
    # Set custom output file if specified
    if args.output != "accounts.csv":
        generator.output_file = generator.output_dir / args.output
    
    # Determine number of accounts to generate
    num_accounts = args.generate if args.generate is not None else args.num
    
    # Generate accounts with collision detection
    accounts = generator.generate_unique_accounts(num_accounts)
    
    # Check if this is the new --generate mode (Story 1.4 format)
    if args.generate is not None:
        # Output in the required format for Story 1.4: "账号 --- 密码"
        print(f"\nGenerated {len(accounts)} accounts:")
        print("-" * 50)
        for i, account in enumerate(accounts, 1):
            print(f"{i:2d}. {account['username']} --- {account['password']}")
        print("-" * 50)
        
        # Save to CSV if requested
        if args.save_csv:
            generator.save_to_csv(accounts)
            print(f"Accounts also saved to {generator.output_file}")
    else:
        # Legacy format for backward compatibility
        print(f"\nGenerated {len(accounts)} accounts:")
        print("-" * 50)
        for i, account in enumerate(accounts, 1):
            print(f"{i:2d}. Username: {account['username']}, Password: {account['password']}")
        print("-" * 50)
        
        # Save to CSV if requested
        if args.save_csv:
            generator.save_to_csv(accounts)
            print(f"Accounts also saved to {generator.output_file}")
        else:
            print("Accounts not saved to file (use --save-csv to save)")

if __name__ == "__main__":
    main()