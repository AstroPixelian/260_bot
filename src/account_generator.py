#!/usr/bin/python
# -*- coding: utf-8 -*-
import random
import string
import pandas as pd
import os
from pathlib import Path
from faker import Faker
from src.utils.config import load_config
from src.utils.logger import setup_logger

class AccountGenerator:
    def __init__(self, config_path="config/config.yaml"):
        """Initialize generator with configuration."""
        self.config = load_config(config_path)
        self.logger = setup_logger("AccountGenerator")
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
            lambda: self.fake.first_name().lower() + "." + self.fake.last_name().lower() + str(random.randint(1, 999)),
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
        """Generate a random password based on config."""
        config = self.config.get("account_generator", {})
        length = random.randint(
            config.get("password_min_length", 12),
            config.get("password_max_length", 20)
        )
        chars = (
            string.ascii_lowercase +
            string.ascii_uppercase +
            string.digits +
            config.get("password_special_chars", "!@#$%^&*")
        )
        password = ''.join(random.choice(chars) for _ in range(length))
        # Ensure at least one of each required character type
        password = self._ensure_password_complexity(password)
        return password

    def _ensure_password_complexity(self, password):
        """Ensure password meets complexity requirements."""
        if not any(c.islower() for c in password):
            password = password[:-1] + random.choice(string.ascii_lowercase)
        if not any(c.isupper() for c in password):
            password = password[:-1] + random.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + random.choice(string.digits)
        if not any(c in self.config.get("account_generator", {}).get("password_special_chars", "!@#$%^&*") for c in password):
            password = password[:-1] + random.choice(self.config.get("account_generator", {}).get("password_special_chars", "!@#$%^&*"))
        return password

    def generate_accounts(self, num_accounts)->list[dict]:
        """Generate specified number of accounts and save to CSV."""
        try:
            accounts = []
            self.logger.info(f"Generating {num_accounts} accounts...")
            for _ in range(num_accounts):
                account = {
                    "username": self.generate_username(),
                    "password": self.generate_password()
                }
                accounts.append(account)
            self.logger.info(f"Generated {num_accounts} accounts")
        except Exception as e:
            self.logger.error(f"Error generating accounts: {str(e)}")
            raise
    def save_to_csv(self, accounts):

        # Save to file using custom separator to avoid comma conflicts
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write("username,password\n")
            for account in accounts:
                f.write(f"{account['username']},{account['password']}\n")
        self.logger.info(f"Generated accounts are saved to {self.output_file}")
        return accounts

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate random accounts and save to CSV.")
    parser.add_argument("--num", type=int, default=10, help="Number of accounts to generate")
    args = parser.parse_args()

    generator = AccountGenerator()
    accounts = generator.generate_accounts(args.num)
    generator.save_to_csv(accounts)
    print(f"Generated {len(accounts)} accounts. Saved to {generator.output_file}")

if __name__ == "__main__":
    main()