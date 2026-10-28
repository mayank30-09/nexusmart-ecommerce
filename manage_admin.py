"""
manage_admin.py - Standalone Command-Line Tool for Secure NexusMart Administrator Management.
Usage:
    python manage_admin.py list
    python manage_admin.py promote user@example.com
    python manage_admin.py demote user@example.com
    python manage_admin.py create --name "Admin Name" --email "admin@example.com" [--password "SecretPass!"]
"""

import os
import sys
import argparse
import getpass
from werkzeug.security import generate_password_hash

# Ensure ecommerce_practical10 is in path
PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from database import get_db_connection, init_db


def list_admins():
    """List all current administrators with masked email addresses."""
    init_db()
    conn = get_db_connection()
    admins = conn.execute("SELECT id, name, email, is_admin, created_at FROM customers WHERE is_admin = 1 ORDER BY id ASC;").fetchall()
    conn.close()

    if not admins:
        print("No administrator accounts found.")
        return

    print("=" * 65)
    print(f" NexusMart Administrator Accounts ({len(admins)} total)")
    print("=" * 65)
    for a in admins:
        parts = a["email"].split("@")
        masked_email = f"{parts[0][:3]}***@{parts[1]}" if len(parts) == 2 else "***"
        print(f"  - ID: {a['id']:<4} | Name: {a['name']:<20} | Email: {masked_email:<22} | Created: {str(a['created_at'])[:10]}")
    print("=" * 65)


def promote_admin(email):
    """Promote an existing customer account to administrator."""
    init_db()
    email = email.strip().lower()
    conn = get_db_connection()
    customer = conn.execute("SELECT id, name, email, is_admin FROM customers WHERE email = ?;", (email,)).fetchone()

    if not customer:
        conn.close()
        print(f"[ERROR] Customer account with email '{email}' does not exist.")
        sys.exit(1)

    if customer["is_admin"]:
        conn.close()
        print(f"[INFO] Customer '{customer['name']}' ({email}) is already an administrator.")
        return

    conn.execute("UPDATE customers SET is_admin = 1 WHERE id = ?;", (customer["id"],))
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Customer '{customer['name']}' ({email}) has been promoted to Administrator.")


def demote_admin(email):
    """Demote an administrator account back to a regular customer."""
    init_db()
    email = email.strip().lower()
    conn = get_db_connection()
    customer = conn.execute("SELECT id, name, email, is_admin FROM customers WHERE email = ?;", (email,)).fetchone()

    if not customer:
        conn.close()
        print(f"[ERROR] Customer account with email '{email}' does not exist.")
        sys.exit(1)

    if not customer["is_admin"]:
        conn.close()
        print(f"[INFO] Customer '{customer['name']}' ({email}) is not an administrator.")
        return

    # Check that we do not demote the last remaining admin
    admin_count = conn.execute("SELECT COUNT(*) AS count FROM customers WHERE is_admin = 1;").fetchone()["count"]
    if admin_count <= 1:
        conn.close()
        print("[ERROR] Cannot demote the only remaining administrator account.")
        sys.exit(1)

    conn.execute("UPDATE customers SET is_admin = 0 WHERE id = ?;", (customer["id"],))
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Demoted '{customer['name']}' ({email}) to regular customer.")


def create_admin(name, email, password=None):
    """Securely create a new administrator account."""
    init_db()
    email = email.strip().lower()
    name = name.strip()

    if not password:
        password = getpass.getpass("Enter administrator password: ")
        confirm = getpass.getpass("Confirm administrator password: ")
        if password != confirm:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    if len(password) < 8:
        print("[ERROR] Administrator password must be at least 8 characters long.")
        sys.exit(1)

    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM customers WHERE email = ?;", (email,)).fetchone()
    if existing:
        conn.close()
        print(f"[ERROR] An account with email '{email}' already exists. Use 'promote' instead.")
        sys.exit(1)

    password_hash = generate_password_hash(password)
    conn.execute("""
        INSERT INTO customers (name, email, password_hash, is_admin)
        VALUES (?, ?, ?, 1);
    """, (name, email, password_hash))
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Administrator account for '{name}' ({email}) created successfully.")


def reset_admin_password(email, password=None):
    """Securely reset the password for an existing administrator account."""
    init_db()
    email = email.strip().lower()
    conn = get_db_connection()
    customer = conn.execute("SELECT id, name, email, is_admin FROM customers WHERE email = ?;", (email,)).fetchone()

    if not customer:
        conn.close()
        print(f"[ERROR] Account with email '{email}' does not exist.")
        sys.exit(1)

    if not customer["is_admin"]:
        conn.close()
        print(f"[ERROR] Account '{email}' is not an administrator. Use promote first or regular customer password reset.")
        sys.exit(1)

    if not password:
        password = getpass.getpass(f"Enter new password for administrator '{customer['name']}': ")
        confirm = getpass.getpass("Confirm new password: ")
        if password != confirm:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    if len(password) < 8:
        print("[ERROR] Administrator password must be at least 8 characters long.")
        sys.exit(1)

    password_hash = generate_password_hash(password)
    conn.execute("UPDATE customers SET password_hash = ? WHERE id = ?;", (password_hash, customer["id"]))
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Password for administrator '{customer['name']}' ({email}) has been successfully updated.")


def main():
    parser = argparse.ArgumentParser(description="NexusMart Administrator CLI Management Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list
    subparsers.add_parser("list", help="List all administrator accounts")

    # promote
    promote_parser = subparsers.add_parser("promote", help="Promote customer to administrator")
    promote_parser.add_argument("email", help="Email of existing customer account to promote")

    # demote
    demote_parser = subparsers.add_parser("demote", help="Demote administrator to customer")
    demote_parser.add_argument("email", help="Email of administrator account to demote")

    # create
    create_parser = subparsers.add_parser("create", help="Create new administrator account")
    create_parser.add_argument("--name", required=True, help="Full name of administrator")
    create_parser.add_argument("--email", required=True, help="Email address of administrator")
    create_parser.add_argument("--password", required=False, help="Password (optional, will prompt securely if omitted)")

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Reset password for an existing administrator")
    reset_parser.add_argument("email", help="Email of administrator account")
    reset_parser.add_argument("--password", required=False, help="New password (optional, will prompt securely if omitted)")

    args = parser.parse_args()

    if args.command == "list":
        list_admins()
    elif args.command == "promote":
        promote_admin(args.email)
    elif args.command == "demote":
        demote_admin(args.email)
    elif args.command == "create":
        create_admin(args.name, args.email, args.password)
    elif args.command == "reset-password":
        reset_admin_password(args.email, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

