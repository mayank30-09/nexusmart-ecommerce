"""
tests/test_auth.py - Module 1: Customer Registration & Authentication Test Suite.
Covers:
  - Local customer registration validations and hashing
  - Local customer authentication, session management, and logout
  - Protected route access control
  - Google OAuth 2.0 flow, CSRF state verification, token verification, and safe account linking
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import requests

# Add ecommerce_practical10 to path
PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app
from tests.conftest import BaseTestCase


class TestCustomerAuth(BaseTestCase, unittest.TestCase):
    """Test suite for Module 1: Customer Registration and Authentication."""

    # --------------------------------------------------------------------------
    # 1. Registration Tests
    # --------------------------------------------------------------------------

    def test_01_valid_registration(self):
        """BB-AUTH-01 / WB: Valid registration stores customer and redirects to login."""
        res = self.register(name="John Smith", email="john@test.com", password="password123", confirm="password123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)

        # Verify record in database
        conn = database.get_db_connection()
        user = conn.execute("SELECT * FROM customers WHERE email = 'john@test.com';").fetchone()
        conn.close()
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "John Smith")
        self.assertIsNotNone(user["password_hash"])
        self.assertNotEqual(user["password_hash"], "password123")  # Hashed!

    def test_02_empty_fields_registration(self):
        """BB-AUTH-02 / WB: Empty required fields show validation error."""
        # Missing name
        res1 = self.register(name="", email="noname@test.com", password="password123", confirm="password123")
        self.assertIn(b"All fields are required", res1.data)

        # Missing email
        res2 = self.register(name="No Email", email="", password="password123", confirm="password123")
        self.assertIn(b"All fields are required", res2.data)

        # Missing password
        res3 = self.register(name="No Pwd", email="nopwd@test.com", password="", confirm="")
        self.assertIn(b"All fields are required", res3.data)

    def test_03_invalid_email_registration(self):
        """BB-AUTH-03 / WB: Invalid email formats are rejected by regex pattern."""
        invalid_emails = ["not-an-email", "missingat.com", "@nodomain.com", "user@"]
        for bad_email in invalid_emails:
            res = self.register(name="Invalid Email User", email=bad_email, password="password123", confirm="password123")
            self.assertIn(b"Please enter a valid email address", res.data, f"Failed for {bad_email}")

    def test_04_password_mismatch_registration(self):
        """BB-AUTH-04 / WB: Non-matching confirmation password triggers validation failure."""
        res = self.register(name="Mismatch User", email="mismatch@test.com", password="password123", confirm="different456")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Passwords do not match", res.data)

    def test_05_password_length_validation(self):
        """BB-AUTH-05 / WB: Passwords under 6 characters are rejected."""
        res = self.register(name="Short Pwd", email="short@test.com", password="12345", confirm="12345")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Password must be at least 6 characters long", res.data)

    def test_06_duplicate_email_registration(self):
        """BB-AUTH-06 / WB: Duplicate email registration is prevented."""
        # Register original
        self.register(name="First User", email="dup@test.com", password="password123", confirm="password123")
        # Attempt duplicate registration with same email
        res = self.register(name="Second User", email="dup@test.com", password="password456", confirm="password456")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"An account with this email already exists", res.data)

    def test_07_email_case_insensitivity(self):
        """BB-AUTH-07 / WB: Emails are normalized to lowercase during registration."""
        self.register(name="Case User", email="CASE@TEST.COM", password="password123", confirm="password123")
        conn = database.get_db_connection()
        user = conn.execute("SELECT email FROM customers WHERE email = 'case@test.com';").fetchone()
        conn.close()
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "case@test.com")

    # --------------------------------------------------------------------------
    # 2. Login, Session, and Access Control Tests
    # --------------------------------------------------------------------------

    def test_08_valid_login(self):
        """BB-AUTH-08 / WB: Valid login credentials initialize session and redirect to dashboard."""
        self.register(name="Valid Shopper", email="shopper@test.com", password="password123", confirm="password123")
        res = self.login(email="shopper@test.com", password="password123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome back, Valid Shopper", res.data)
        self.assertIn(b"Customer Dashboard", res.data)

        # Check session transaction
        with self.client.session_transaction() as sess:
            self.assertIn("customer_id", sess)
            self.assertEqual(sess["customer_name"], "Valid Shopper")
            self.assertEqual(sess["customer_email"], "shopper@test.com")

    def test_09_invalid_password_login(self):
        """BB-AUTH-09 / WB: Incorrect password displays authentication error."""
        self.register(name="Secret User", email="secret@test.com", password="realpassword", confirm="realpassword")
        res = self.login(email="secret@test.com", password="wrongpassword")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid email or password", res.data)

    def test_10_nonexistent_email_login(self):
        """BB-AUTH-10 / WB: Unregistered email displays authentication error."""
        res = self.login(email="nonexistent@test.com", password="password123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid email or password", res.data)

    def test_11_empty_login_fields(self):
        """BB-AUTH-11 / WB: Blank credentials display required fields message."""
        res = self.login(email="", password="")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Please enter both email and password", res.data)

    def test_12_oauth_only_account_password_login(self):
        """BB-AUTH-12 / WB: Accounts registered purely via Google cannot log in with password."""
        conn = database.get_db_connection()
        conn.execute(
            "INSERT INTO customers (name, email, password_hash, google_id) VALUES (?, ?, NULL, ?);",
            ("Google Only", "googleonly@test.com", "sub_google_999")
        )
        conn.commit()
        conn.close()

        res = self.login(email="googleonly@test.com", password="anypassword")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"This account was created with Google Sign-In", res.data)

    def test_13_logout(self):
        """BB-AUTH-13 / WB: Logout clears session and redirects to login."""
        self.register(name="Logout User", email="logout@test.com", password="password123", confirm="password123")
        self.login(email="logout@test.com", password="password123")

        res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"You have been logged out successfully", res.data)

        # Confirm session is empty
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)

    def test_14_protected_pages_access_without_login(self):
        """BB-AUTH-14 / WB: Protected routes redirect unauthenticated visitors to login."""
        protected_endpoints = ["/dashboard", "/products", "/cart"]
        for endpoint in protected_endpoints:
            res = self.client.get(endpoint, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Please login to access this page", res.data, f"Failed for {endpoint}")

    def test_15_home_route_routing(self):
        """BB-AUTH-15 / WB: Home route redirects based on session presence."""
        # Unauthenticated -> redirects to login
        res1 = self.client.get("/", follow_redirects=True)
        self.assertIn(b"Customer Login", res1.data)

        # Authenticated -> redirects to dashboard
        self.register(name="Home User", email="home@test.com", password="password123", confirm="password123")
        self.login(email="home@test.com", password="password123")
        res2 = self.client.get("/", follow_redirects=True)
        self.assertIn(b"Customer Dashboard", res2.data)

    def test_16_authenticated_user_accessing_auth_pages(self):
        """BB-AUTH-16 / WB: Authenticated users accessing /login or /register are redirected to dashboard."""
        self.register(name="Active User", email="active@test.com", password="password123", confirm="password123")
        self.login(email="active@test.com", password="password123")

        res_login = self.client.get("/login", follow_redirects=True)
        self.assertIn(b"Customer Dashboard", res_login.data)

        res_reg = self.client.get("/register", follow_redirects=True)
        self.assertIn(b"Customer Dashboard", res_reg.data)

    # --------------------------------------------------------------------------
    # 3. Google OAuth 2.0 Flow Tests
    # --------------------------------------------------------------------------

    def test_17_google_login_missing_config(self):
        """BB-AUTH-17 / WB: Missing GOOGLE_CLIENT_ID fails gracefully with error message."""
        self.app.config["GOOGLE_CLIENT_ID"] = ""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": ""}):
            res = self.client.get("/auth/google/login", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Google OAuth is not configured on this server", res.data)

    def test_18_google_login_redirection(self):
        """BB-AUTH-18 / WB: Configured Google OAuth initiates authorization URL with CSRF state."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
        res = self.client.get("/auth/google/login")
        self.assertEqual(res.status_code, 302)
        location = res.headers.get("Location", "")
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", location)
        self.assertIn("client_id=test-client-id.apps.googleusercontent.com", location)
        self.assertIn("response_type=code", location)
        self.assertIn("scope=openid+email+profile", location)

        with self.client.session_transaction() as sess:
            self.assertIn("oauth_state", sess)
            self.assertTrue(len(sess["oauth_state"]) >= 32)

    def test_19_google_callback_user_cancellation(self):
        """BB-AUTH-19 / WB: User cancelling Google OAuth redirects with warning."""
        res = self.client.get("/auth/google/callback?error=access_denied", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Google sign-in was cancelled by the user", res.data)

    def test_20_google_callback_generic_error(self):
        """BB-AUTH-20 / WB: OAuth server error returned in callback displays error."""
        res = self.client.get("/auth/google/callback?error=server_error", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Google authentication failed: server_error", res.data)

    def test_21_google_callback_csrf_mismatch(self):
        """BB-AUTH-21 / WB: State mismatch / CSRF attack is blocked."""
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "legitimate-token-12345"

        res = self.client.get("/auth/google/callback?code=mock_code&state=forged-state-67890", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"State parameter mismatch", res.data)

    def test_22_google_callback_missing_code(self):
        """BB-AUTH-22 / WB: Callback without authorization code is rejected."""
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?state=state-token", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Missing authorization code from Google", res.data)

    def test_23_google_callback_missing_server_credentials(self):
        """BB-AUTH-23 / WB: Missing server secret during callback halts flow."""
        self.app.config["GOOGLE_CLIENT_ID"] = "some-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = ""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET": ""}):
            with self.client.session_transaction() as sess:
                sess["oauth_state"] = "state-token"

            res = self.client.get("/auth/google/callback?code=mock_code&state=state-token", follow_redirects=True)
            self.assertIn(b"Google OAuth credentials are missing from server configuration", res.data)

    @patch("app.requests.post")
    def test_24_google_callback_network_error_on_token_exchange(self, mock_post):
        """BB-AUTH-24 / WB: Network exception during token exchange fails gracefully."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"
        mock_post.side_effect = requests.RequestException("Connection timed out")

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertIn(b"Unable to reach Google OAuth servers", res.data)

    @patch("app.requests.post")
    def test_25_google_callback_non_200_token_response(self, mock_post):
        """BB-AUTH-25 / WB: Non-200 HTTP response from Google token endpoint fails gracefully."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_post.return_value = mock_resp

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=bad_code&state=state-token", follow_redirects=True)
        self.assertIn(b"Failed to retrieve authentication tokens from Google", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_26_google_callback_token_verification_failure(self, mock_verify, mock_post):
        """BB-AUTH-26 / WB: Token verification failure (tampered or expired) is handled."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "expired_jwt"}
        mock_post.return_value = mock_post_resp

        mock_verify.side_effect = ValueError("Token has expired")

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertIn(b"Google ID token verification failed", res.data)
        self.assertIn(b"Token has expired", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_27_google_callback_unverified_email_rejected(self, mock_verify, mock_post):
        """BB-AUTH-27 / WB: Google accounts with unverified emails are rejected."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "jwt_token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "sub-unverified",
            "email": "unverified@test.com",
            "name": "Unverified",
            "email_verified": False,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertIn(b"Google email is not verified", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_28_google_callback_first_time_user(self, mock_verify, mock_post):
        """BB-AUTH-28 / WB: First-time Google user creates account and is signed in."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "jwt_token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "sub-first-time-111",
            "email": "firsttime@test.com",
            "name": "First User",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your account has been created with Google", res.data)
        self.assertIn(b"First User", res.data)

        # Check in DB
        conn = database.get_db_connection()
        user = conn.execute("SELECT * FROM customers WHERE email = 'firsttime@test.com';").fetchone()
        conn.close()
        self.assertIsNotNone(user)
        self.assertEqual(user["google_id"], "sub-first-time-111")
        self.assertIsNone(user["password_hash"])

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_29_google_callback_returning_user(self, mock_verify, mock_post):
        """BB-AUTH-29 / WB: Returning Google user signs in directly without duplicate creation."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        # Pre-seed user
        conn = database.get_db_connection()
        conn.execute(
            "INSERT INTO customers (name, email, password_hash, google_id) VALUES (?, ?, NULL, ?);",
            ("Returning Google User", "returning@test.com", "sub-returning-222")
        )
        conn.commit()
        conn.close()

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "jwt_token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "sub-returning-222",
            "email": "returning@test.com",
            "name": "Returning Google User",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome back, Returning Google User!", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_30_safe_account_linking_workflow(self, mock_verify, mock_post):
        """BB-AUTH-30 / WB: Safe account linking prevents auto-merge and requires password validation."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        # 1. Existing local customer
        self.register(name="Existing User", email="linkuser@test.com", password="password123", confirm="password123")

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "jwt_token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "sub-link-333",
            "email": "linkuser@test.com",
            "name": "Existing User",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-link"

        # Should redirect to link page
        res = self.client.get("/auth/google/callback?code=code123&state=state-link", follow_redirects=True)
        self.assertIn(b"Link Google Account", res.data)
        self.assertIn(b"Existing Account Detected", res.data)

        # 2. Submit wrong password -> reject
        res_wrong = self.client.post("/auth/google/link", data={"password": "wrongpassword"}, follow_redirects=True)
        self.assertIn(b"Incorrect password", res_wrong.data)

        # 3. Submit correct password -> success
        res_correct = self.client.post("/auth/google/link", data={"password": "password123"}, follow_redirects=True)
        self.assertIn(b"Google account successfully linked!", res_correct.data)

        # Verify DB
        conn = database.get_db_connection()
        user = conn.execute("SELECT google_id FROM customers WHERE email = 'linkuser@test.com';").fetchone()
        conn.close()
        self.assertEqual(user["google_id"], "sub-link-333")

    def test_31_cancel_account_linking(self):
        """BB-AUTH-31 / WB: Cancelling pending link redirects to login cleanly."""
        with self.client.session_transaction() as sess:
            sess["pending_google_link"] = {"email": "pending@test.com"}

        res = self.client.get("/auth/google/cancel-link", follow_redirects=True)
        self.assertIn(b"Google account linking was cancelled", res.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("pending_google_link", sess)

    def test_32_register_page_get_request(self):
        """WB: GET request to /register renders registration form for guest."""
        res = self.client.get("/register")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Customer Registration", res.data)
        self.assertIn(b"Create Account", res.data)

    def test_33_google_login_with_action_param(self):
        """WB: Google login with action=link sets oauth_action in session."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
        res = self.client.get("/auth/google/login?action=link")
        self.assertEqual(res.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("oauth_action"), "link")

    @patch("app.requests.post")
    def test_34_google_callback_missing_id_token_in_json(self, mock_post):
        """WB: Google token exchange response without id_token fails gracefully."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access_token": "only-access-token"}
        mock_post.return_value = mock_resp

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertIn(b"Google authentication response did not contain an ID token", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_35_google_callback_invalid_issuer(self, mock_verify, mock_post):
        """WB: Token with invalid issuer is rejected."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "jwt_token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "sub-invalid-iss",
            "email": "badiss@test.com",
            "name": "Bad Issuer",
            "email_verified": True,
            "iss": "https://untrusted-issuer.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-token"

        res = self.client.get("/auth/google/callback?code=code123&state=state-token", follow_redirects=True)
        self.assertIn(b"Invalid Google token issuer", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_36_google_callback_explicit_link_action_success_and_conflict(self, mock_verify, mock_post):
        """WB: In-session explicit linking links Google ID and blocks conflicting IDs."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-secret"

        # Register User A and User B
        self.register(name="User A", email="usera@test.com", password="password123", confirm="password123")
        self.login(email="usera@test.com", password="password123")

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "jwt_token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "sub-shared-google",
            "email": "usera@test.com",
            "name": "User A",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-link-act"
            sess["oauth_action"] = "link"

        # Successfully links to User A
        res_link_a = self.client.get("/auth/google/callback?code=code123&state=state-link-act", follow_redirects=True)
        self.assertIn(b"Google account successfully linked to your profile!", res_link_a.data)

        # Now User B logs in and tries to link the same Google ID
        self.client.get("/logout", follow_redirects=True)
        self.register(name="User B", email="userb@test.com", password="password123", confirm="password123")
        self.login(email="userb@test.com", password="password123")

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-link-conflict"
            sess["oauth_action"] = "link"

        res_conflict = self.client.get("/auth/google/callback?code=code456&state=state-link-conflict", follow_redirects=True)
        self.assertIn(b"This Google account is already linked to another customer profile", res_conflict.data)

    def test_37_link_account_edge_cases(self):
        """WB: Accessing /auth/google/link without pending session and POST with empty password."""
        # Accessing /auth/google/link without pending session
        res_none = self.client.get("/auth/google/link", follow_redirects=True)
        self.assertIn(b"No pending account link request found", res_none.data)

        # Setting pending session then posting empty password
        self.register(name="Pending Tester", email="pendingtest@test.com", password="password123", confirm="password123")
        conn = database.get_db_connection()
        user = conn.execute("SELECT id FROM customers WHERE email = 'pendingtest@test.com';").fetchone()
        conn.close()

        with self.client.session_transaction() as sess:
            sess["pending_google_link"] = {
                "customer_id": user["id"],
                "google_id": "google_sub_pend",
                "email": "pendingtest@test.com",
                "name": "Pending Tester",
                "existing_name": "Pending Tester"
            }

        res_empty = self.client.post("/auth/google/link", data={"password": ""}, follow_redirects=True)
        self.assertIn(b"Please enter your existing account password", res_empty.data)

    def test_38_configured_redirect_uri(self):
        """WB: get_google_redirect_uri respects configured custom URI."""
        self.app.config["GOOGLE_REDIRECT_URI"] = "https://myshop.com/auth/google/callback"
        uri = flask_app.get_google_redirect_uri()
        self.assertEqual(uri, "https://myshop.com/auth/google/callback")
        self.app.config["GOOGLE_REDIRECT_URI"] = None


if __name__ == "__main__":
    unittest.main(verbosity=2)
