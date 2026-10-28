"""
tests/test_session_and_security.py - Comprehensive Automated Tests for:
  - Priority 1: Session persistence, logout invalidation, cookie deletion, and cache headers
  - Priority 4: Admin role authorization, database role verification, and admin CLI tools
  - Security hardening: Defense-in-depth against stale sessions and client-side privilege escalation
"""

import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app
from tests.conftest import BaseTestCase
import manage_admin


class TestSessionPersistenceAndLogout(BaseTestCase, unittest.TestCase):
    """Regression tests for Priority 1: Session persistence, logout, and bfcache defenses."""

    def setUp(self):
        super().setUp()
        # Register a test customer
        self.register(name="Session Tester", email="session_test@test.com", password="Password123!", confirm="Password123!")
        conn = database.get_db_connection()
        row = conn.execute("SELECT id FROM customers WHERE email = 'session_test@test.com';").fetchone()
        self.customer_id = row["id"]
        conn.close()

    def test_01_logout_clears_session_and_deletes_cookie(self):
        """Priority 1: /logout invalidates session and sends deletion for session cookie."""
        # 1. Log in
        self.login(email="session_test@test.com", password="Password123!")

        # Verify authenticated access
        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"Session Tester", res_dash.data)

        # 2. Log out
        res_logout = self.client.get("/logout")
        self.assertEqual(res_logout.status_code, 302)
        self.assertTrue(res_logout.headers["Location"].endswith("/login"))

        # Verify session is empty
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)
            self.assertNotIn("customer_name", sess)

        # Verify cookie deletion header in logout response
        set_cookie = res_logout.headers.get("Set-Cookie", "")
        # Flask delete_cookie sets expires in the past or max-age=0
        self.assertTrue(
            "session=;" in set_cookie or "Expires=Thu, 01 Jan 1970" in set_cookie or "Max-Age=0" in set_cookie,
            "Expected Set-Cookie header to explicitly delete or expire the session cookie."
        )

    def test_02_access_protected_pages_after_logout_is_blocked(self):
        """Priority 1: Direct navigation to protected routes after logout must redirect to login."""
        self.login(email="session_test@test.com", password="Password123!")
        self.client.get("/logout", follow_redirects=True)

        protected_urls = [
            "/dashboard",
            "/profile",
            "/orders",
            "/cart",
            "/checkout"
        ]

        for url in protected_urls:
            res = self.client.get(url, follow_redirects=False)
            self.assertEqual(res.status_code, 302, f"Expected 302 redirect for {url} after logout")
            self.assertTrue(res.headers["Location"].endswith("/login"), f"Expected {url} to redirect to /login")

            # Check message when following redirect
            res_followed = self.client.get(url, follow_redirects=True)
            self.assertIn(b"Please login to access this page", res_followed.data, f"Missing login flash for {url}")

    def test_03_cache_control_headers_on_authenticated_and_sensitive_pages(self):
        """Priority 1: Sensitive & authenticated pages must send strict no-cache/no-store headers."""
        self.login(email="session_test@test.com", password="Password123!")

        sensitive_urls = [
            "/dashboard",
            "/profile",
            "/orders",
            "/checkout",
            "/cart"
        ]

        for url in sensitive_urls:
            res = self.client.get(url)
            cache_header = res.headers.get("Cache-Control", "")
            self.assertIn("no-store", cache_header, f"Missing no-store in Cache-Control for {url}")
            self.assertIn("no-cache", cache_header, f"Missing no-cache in Cache-Control for {url}")
            self.assertEqual(res.headers.get("Pragma"), "no-cache", f"Missing Pragma: no-cache for {url}")
            self.assertEqual(res.headers.get("Expires"), "0", f"Missing Expires: 0 for {url}")

        # Test security headers
        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res_dash.headers.get("X-Frame-Options"), "SAMEORIGIN")

    def test_04_deleted_or_stale_customer_session_rejected_on_every_request(self):
        """Priority 1: Backend verifies customer existence in DB on every request and purges stale sessions."""
        self.login(email="session_test@test.com", password="Password123!")

        # Simulate customer deletion from database while session cookie remains
        conn = database.get_db_connection()
        conn.execute("DELETE FROM customers WHERE id = ?;", (self.customer_id,))
        conn.commit()
        conn.close()

        # Attempt to access dashboard with orphaned session
        res = self.client.get("/dashboard", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Session expired or customer account not found", res.data)

        # Verify session was automatically cleaned up
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)

    def test_05_admin_logout_clears_session_and_deletes_cookie(self):
        """Priority 1: /admin/logout invalidates session and prevents admin page access."""
        # Create and login an admin
        conn = database.get_db_connection()
        conn.execute("""
            INSERT INTO customers (name, email, password_hash, is_admin)
            VALUES ('Super Admin', 'superadmin@test.com', 'dummyhash', 1);
        """)
        conn.commit()
        admin_id = conn.execute("SELECT id FROM customers WHERE email = 'superadmin@test.com';").fetchone()["id"]
        conn.close()

        # Set admin session
        with self.client.session_transaction() as sess:
            sess["customer_id"] = admin_id
            sess["customer_name"] = "Super Admin"
            sess["is_admin"] = True

        res_dash = self.client.get("/admin/dashboard")
        self.assertEqual(res_dash.status_code, 200)

        # Logout admin
        res_logout = self.client.get("/admin/logout")
        self.assertEqual(res_logout.status_code, 302)
        self.assertTrue(res_logout.headers["Location"].endswith("/admin/login"))

        # Verify cookie deletion
        set_cookie = res_logout.headers.get("Set-Cookie", "")
        self.assertTrue("session=;" in set_cookie or "Expires=Thu, 01 Jan 1970" in set_cookie or "Max-Age=0" in set_cookie)

        # Verify admin routes reject access now
        res_after = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(res_after.status_code, 302)
        self.assertTrue(res_after.headers["Location"].endswith("/admin/login"))


class TestAdminSecurityAndPrivilegeEnforcement(BaseTestCase, unittest.TestCase):
    """Tests for Priority 4: Admin role authorization, DB role checking, and CLI provisioning."""

    def setUp(self):
        super().setUp()
        # Normal user
        self.register(name="Regular User", email="regular@test.com", password="Password123!", confirm="Password123!")
        conn = database.get_db_connection()
        self.regular_id = conn.execute("SELECT id FROM customers WHERE email = 'regular@test.com';").fetchone()["id"]
        conn.close()

    def test_01_non_admin_cannot_access_admin_portal(self):
        """Priority 4: Regular authenticated user receives 403 Forbidden on all admin routes."""
        self.login(email="regular@test.com", password="Password123!")

        admin_routes = [
            "/admin/dashboard",
            "/admin/products",
            "/admin/orders",
            "/admin/coupons"
        ]

        for route in admin_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 403, f"Non-admin unexpectedly accessed {route}")
            self.assertIn(b"Access denied. Administrator privileges required", res.data)

    def test_02_session_tampering_for_admin_rejected_by_db_check(self):
        """Priority 4: Client-side session tampering with is_admin=True is rejected by DB check."""
        self.login(email="regular@test.com", password="Password123!")

        # Attacker injects is_admin=True in session while database has is_admin=0
        with self.client.session_transaction() as sess:
            sess["is_admin"] = True

        # Server-side decorator queries DB, detects fraud, revokes session flag, and returns 403
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 403)
        self.assertIn(b"Access denied. Administrator privileges required", res.data)

        # Flag is revoked from session
        with self.client.session_transaction() as sess:
            self.assertNotIn("is_admin", sess)

    def test_03_admin_cli_promote_and_demote(self):
        """Priority 4: CLI promote and demote tools work accurately with database."""
        # 1. Promote regular user
        manage_admin.promote_admin("regular@test.com")

        conn = database.get_db_connection()
        user_after = conn.execute("SELECT is_admin FROM customers WHERE email = 'regular@test.com';").fetchone()
        self.assertEqual(user_after["is_admin"], 1)

        # 2. Demote regular user back
        manage_admin.demote_admin("regular@test.com")
        user_demoted = conn.execute("SELECT is_admin FROM customers WHERE email = 'regular@test.com';").fetchone()
        self.assertEqual(user_demoted["is_admin"], 0)
        conn.close()

    def test_04_admin_cli_list(self):
        """Priority 4: CLI list outputs admins without exposing passwords."""
        f = StringIO()
        with patch("sys.stdout", f):
            manage_admin.list_admins()
        output = f.getvalue()
        self.assertIn("NexusMart Administrator Accounts", output)
        self.assertNotIn("password", output.lower())
        self.assertNotIn("AdminPass123!", output)

    def test_05_admin_cli_reset_password(self):
        """Priority 4: CLI reset-password securely updates administrator password hash."""
        new_pass = "FacultyDemo2026!"
        manage_admin.reset_admin_password("admin@nexusmart.com", new_pass)

        # Verify login succeeds with the new password (follows redirect to admin dashboard, status 200)
        res = self.login(email="admin@nexusmart.com", password=new_pass)
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertIn("customer_id", sess)
            self.assertTrue(sess.get("is_admin"))

    def test_06_cannot_demote_only_admin(self):
        """Priority 4: CLI refuses to demote the sole remaining administrator."""
        with self.assertRaises(SystemExit):
            manage_admin.demote_admin("admin@nexusmart.com")


if __name__ == "__main__":
    unittest.main()

