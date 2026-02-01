"""
Example: Vulnerable Payment Service

This file contains INTENTIONAL security issues for demonstration purposes.
DO NOT use this code in production!

Issues included:
- SQL injection
- Hardcoded credentials
- Missing input validation
- Insecure crypto
- Sensitive data logging
- Command injection
- Race condition
"""

import os
import sqlite3
import subprocess
import hashlib
from typing import Optional

# ISSUE: Hardcoded credentials
DATABASE_PASSWORD = "admin123"
API_SECRET = "sk_live_abc123xyz789"
ADMIN_EMAIL = "admin@company.com"


class PaymentService:
    def __init__(self):
        # ISSUE: Hardcoded database path with credentials
        self.db = sqlite3.connect("payments.db")
        self.secret_key = "super_secret_key_12345"

    def get_user_balance(self, user_id: str) -> float:
        """Get user balance - VULNERABLE TO SQL INJECTION."""
        # ISSUE: SQL injection vulnerability
        query = f"SELECT balance FROM users WHERE id = '{user_id}'"
        cursor = self.db.execute(query)
        result = cursor.fetchone()
        return result[0] if result else 0.0

    def process_payment(self, user_id: str, amount: float, recipient: str) -> bool:
        """Process payment - multiple issues."""

        # ISSUE: No input validation
        # amount could be negative, user_id could be SQL injection

        # ISSUE: Logging sensitive data
        print(f"Processing payment: user={user_id}, amount={amount}, to={recipient}")

        # ISSUE: Weak hashing for transaction ID
        txn_id = hashlib.md5(f"{user_id}{amount}".encode()).hexdigest()

        # ISSUE: Race condition - check and update not atomic
        balance = self.get_user_balance(user_id)
        if balance >= amount:
            # Another request could modify balance here!
            new_balance = balance - amount
            # ISSUE: More SQL injection
            self.db.execute(
                f"UPDATE users SET balance = {new_balance} WHERE id = '{user_id}'"
            )
            return True
        return False

    def export_transactions(self, user_id: str, format: str) -> str:
        """Export transactions - COMMAND INJECTION."""
        # ISSUE: Command injection vulnerability
        output_file = f"/tmp/export_{user_id}.{format}"
        cmd = f"mysqldump payments --user={user_id} > {output_file}"
        subprocess.os.system(cmd)  # Dangerous!
        return output_file

    def verify_password(self, password: str) -> bool:
        """Verify password - timing attack vulnerable."""
        # ISSUE: Timing attack vulnerability
        stored = "correct_password_123"
        if len(password) != len(stored):
            return False
        for i in range(len(password)):
            if password[i] != stored[i]:
                return False
        return True

    def get_admin_data(self, admin_token: Optional[str] = None) -> dict:
        """Get admin data - broken authentication."""
        # ISSUE: Authentication bypass
        if admin_token == "" or admin_token is None:
            # Empty token grants admin access!
            pass

        # ISSUE: Exposing sensitive data
        return {
            "database_password": DATABASE_PASSWORD,
            "api_secret": API_SECRET,
            "all_users": self._get_all_users(),
        }

    def _get_all_users(self) -> list:
        """Get all users with sensitive data."""
        # ISSUE: Returns passwords in response
        cursor = self.db.execute("SELECT id, email, password, ssn FROM users")
        return [
            {"id": row[0], "email": row[1], "password": row[2], "ssn": row[3]}
            for row in cursor.fetchall()
        ]


def create_backup(path: str) -> None:
    """Create backup - path traversal vulnerability."""
    # ISSUE: Path traversal
    backup_path = f"/backups/{path}"
    # Attacker could use: "../../../etc/passwd"
    with open(backup_path, "w") as f:
        f.write("backup data")


# ISSUE: Debug mode left enabled
DEBUG = True
if DEBUG:
    print(f"API Secret: {API_SECRET}")
    print(f"DB Password: {DATABASE_PASSWORD}")
