"""
test_app.py - Automated Test Suite for Practical-10.
Executes and validates all 25 required test cases:
  - Registration (5 tests)
  - Login & Session (3 tests)
  - Products Search & Filter (8 tests)
  - Cart Management (9 tests)
"""

import os
import sys
import unittest
import sqlite3
from unittest.mock import patch, MagicMock

# Set test environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

import database
import app as flask_app


class EcommerceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize database before tests."""
        database.init_db()

    def setUp(self):
        """Set up test client with clean testing session."""
        self.app = flask_app.app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

        # Clean customer & cart tables for predictable test runs
        conn = database.get_db_connection()
        conn.execute("DELETE FROM cart_items;")
        conn.execute("DELETE FROM customers WHERE email LIKE 'test%@example.com';")
        conn.commit()
        conn.close()

    def register_user(self, name="Test User", email="testuser@example.com", password="password123", confirm_password="password123"):
        return self.client.post("/register", data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": confirm_password
        }, follow_redirects=True)

    def login_user(self, email="testuser@example.com", password="password123"):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)

    # ==========================================
    # REGISTRATION TESTS (Test Cases 1-5)
    # ==========================================

    def test_01_valid_registration(self):
        """Test Case 1: Valid registration creates customer and redirects to login."""
        res = self.register_user(name="John Doe", email="testjohn@example.com", password="secret123", confirm_password="secret123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)

        # Check DB
        conn = database.get_db_connection()
        row = conn.execute("SELECT * FROM customers WHERE email = 'testjohn@example.com';").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], "John Doe")

    def test_02_empty_fields_registration(self):
        """Test Case 2: Registration with empty fields shows validation error."""
        res = self.register_user(name="", email="testempty@example.com", password="secret123", confirm_password="secret123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"All fields are required", res.data)

    def test_03_invalid_email_registration(self):
        """Test Case 3: Registration with invalid email format shows error."""
        res = self.register_user(name="Jane Doe", email="not-an-email", password="secret123", confirm_password="secret123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Please enter a valid email address", res.data)

    def test_04_password_mismatch_registration(self):
        """Test Case 4: Password confirmation mismatch shows error."""
        res = self.register_user(name="Jane Doe", email="testmismatch@example.com", password="password123", confirm_password="different123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Passwords do not match", res.data)

    def test_05_duplicate_email_registration(self):
        """Test Case 5: Duplicate email shows already exists error."""
        self.register_user(name="User One", email="testdup@example.com", password="password123", confirm_password="password123")
        res = self.register_user(name="User Two", email="testdup@example.com", password="password456", confirm_password="password456")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"An account with this email already exists", res.data)

    # ==========================================
    # LOGIN & LOGOUT TESTS (Test Cases 6-8)
    # ==========================================

    def test_06_correct_credentials_login(self):
        """Test Case 6: Login with correct credentials sets session and redirects to dashboard."""
        self.register_user(name="Alice Smith", email="testalice@example.com", password="password123", confirm_password="password123")
        res = self.login_user(email="testalice@example.com", password="password123")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome back, Alice Smith", res.data)
        self.assertIn(b"Available Products", res.data)

    def test_07_incorrect_password_login(self):
        """Test Case 7: Login with incorrect password displays error."""
        self.register_user(name="Bob Smith", email="testbob@example.com", password="correctpassword", confirm_password="correctpassword")
        res = self.login_user(email="testbob@example.com", password="wrongpassword")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid email or password", res.data)

    def test_08_logout(self):
        """Test Case 8: Logout clears session and redirects to login."""
        self.register_user(name="Charlie", email="testcharlie@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcharlie@example.com", password="password123")
        res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"You have been logged out successfully", res.data)

        # Confirm dashboard is now inaccessible without login
        dash_res = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"Please login to access this page", dash_res.data)

    # ==========================================
    # PRODUCT SEARCH & FILTER TESTS (Test Cases 9-16)
    # ==========================================

    def test_09_display_products(self):
        """Test Case 9: Catalog displays all seed products."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertIn(b"Water-Resistant Laptop Backpack", res.data)

    def test_10_search_product_by_name(self):
        """Test Case 10: Search by product name keyword filters catalog."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products?search=Headphones")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertNotIn(b"Classic Cotton Crewneck T-Shirt", res.data)

    def test_11_category_filter(self):
        """Test Case 11: Filter by category returns products matching that category only."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products?category=Footwear")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Lightweight Running Sports Shoes", res.data)
        self.assertIn(b"Casual Canvas Low-Top Sneakers", res.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res.data)

    def test_12_minimum_price_filter(self):
        """Test Case 12: Filter by minimum price excludes items below threshold."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products?min_price=2000")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)  # 2999
        self.assertNotIn(b"Classic Cotton Crewneck T-Shirt", res.data)   # 499

    def test_13_maximum_price_filter(self):
        """Test Case 13: Filter by maximum price excludes items above threshold."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products?max_price=800")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Classic Cotton Crewneck T-Shirt", res.data)       # 499
        self.assertIn(b"UV-Protected Polarized Sunglasses", res.data)    # 699
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res.data) # 2999

    def test_14_combined_filters(self):
        """Test Case 14: Combine search keyword, category, min price, and max price."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products?search=Watch&category=Accessories&min_price=1000&max_price=2000")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Minimalist Stainless Steel Wristwatch", res.data)
        # Smart Fitness Tracker Watch is in Electronics, so it should not appear
        self.assertNotIn(b"Smart Fitness Tracker Watch", res.data)

    def test_15_no_search_results(self):
        """Test Case 15: Non-existent product query returns 'No products found'."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        res = self.client.get("/products?search=NonExistentGadgetXYZ")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No products found", res.data)

    def test_16_clear_filters(self):
        """Test Case 16: Clear filters route resets and displays all items."""
        self.register_user(name="Test Consumer", email="testcons@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcons@example.com", password="password123")
        # Visiting base /products shows full catalog
        res = self.client.get("/products")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertIn(b"Multi-Utility Canvas Duffel Bag", res.data)

    # ==========================================
    # CART MANAGEMENT TESTS (Test Cases 17-25)
    # ==========================================

    def test_17_add_product_to_cart(self):
        """Test Case 17: Add product to shopping cart."""
        self.register_user(name="Shopper One", email="testcart1@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart1@example.com", password="password123")

        res = self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Added 2 x &#39;Noise-Canceling Wireless Headphones&#39;", res.data)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)

    def test_18_add_same_product_again_increments_quantity(self):
        """Test Case 18: Adding same product again increments quantity without creating duplicate row."""
        self.register_user(name="Shopper Two", email="testcart2@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart2@example.com", password="password123")

        # Add 2 items
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
        # Add 3 more items of same product
        res = self.client.post("/cart/add", data={"product_id": 1, "quantity": 3}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check in DB that only 1 row exists with quantity = 5
        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'testcart2@example.com';").fetchone()
        items = conn.execute("SELECT * FROM cart_items WHERE customer_id = ? AND product_id = 1;", (customer["id"],)).fetchall()
        conn.close()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quantity"], 5)

    def test_19_update_cart_quantity(self):
        """Test Case 19: Update cart item quantity successfully."""
        self.register_user(name="Shopper Three", email="testcart3@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart3@example.com", password="password123")

        self.client.post("/cart/add", data={"product_id": 3, "quantity": 2}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'testcart3@example.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res = self.client.post(f"/cart/update/{item['id']}", data={"quantity": 6}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Updated quantity", res.data)

        # Verify updated quantity in DB
        conn = database.get_db_connection()
        updated_item = conn.execute("SELECT quantity FROM cart_items WHERE id = ?;", (item["id"],)).fetchone()
        conn.close()
        self.assertEqual(updated_item["quantity"], 6)

    def test_20_remove_product_from_cart(self):
        """Test Case 20: Remove item from cart."""
        self.register_user(name="Shopper Four", email="testcart4@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart4@example.com", password="password123")

        self.client.post("/cart/add", data={"product_id": 4, "quantity": 1}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'testcart4@example.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res = self.client.post(f"/cart/remove/{item['id']}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Removed", res.data)

        # Verify DB is now empty for this customer
        conn = database.get_db_connection()
        items = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchall()
        conn.close()
        self.assertEqual(len(items), 0)

    def test_21_clear_entire_cart(self):
        """Test Case 21: Clear all items in customer cart."""
        self.register_user(name="Shopper Five", email="testcart5@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart5@example.com", password="password123")

        # Add two different products
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)
        self.client.post("/cart/add", data={"product_id": 2, "quantity": 1}, follow_redirects=True)

        res = self.client.post("/cart/clear", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your shopping cart has been cleared", res.data)
        self.assertIn(b"Your Cart is Currently Empty", res.data)

    def test_22_quantity_greater_than_available_stock(self):
        """Test Case 22: Prevent adding or updating quantity exceeding available stock."""
        self.register_user(name="Shopper Six", email="testcart6@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart6@example.com", password="password123")

        # Product 8 has 12 items in stock
        conn = database.get_db_connection()
        prod = conn.execute("SELECT stock FROM products WHERE id = 8;").fetchone()
        conn.close()
        stock = prod["stock"]

        # Attempt to add stock + 10
        res = self.client.post("/cart/add", data={"product_id": 8, "quantity": stock + 10}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Only", res.data)
        self.assertIn(b"in stock", res.data)

    def test_23_correct_subtotal_calculation(self):
        """Test Case 23: Verify Item Subtotal = Unit Price * Quantity."""
        self.register_user(name="Shopper Seven", email="testcart7@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart7@example.com", password="password123")

        # Product 3: Classic Cotton Crewneck T-Shirt, Price = 499.00
        # Quantity = 3 -> Subtotal = 1497.00
        self.client.post("/cart/add", data={"product_id": 3, "quantity": 3}, follow_redirects=True)
        res = self.client.get("/cart")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"1497.00", res.data)

    def test_24_correct_cart_total_calculation(self):
        """Test Case 24: Verify Cart Grand Total = Sum of all Subtotals."""
        self.register_user(name="Shopper Eight", email="testcart8@example.com", password="password123", confirm_password="password123")
        self.login_user(email="testcart8@example.com", password="password123")

        # Product 3: 499.00 * 2 = 998.00
        # Product 9: 1199.00 * 1 = 1199.00
        # Grand Total = 2197.00
        self.client.post("/cart/add", data={"product_id": 3, "quantity": 2}, follow_redirects=True)
        self.client.post("/cart/add", data={"product_id": 9, "quantity": 1}, follow_redirects=True)

        res = self.client.get("/cart")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"2197.00", res.data)

    def test_25_cart_requires_login_and_isolation(self):
        """Test Case 25: Unauthenticated access redirects to login; Customer A cannot see Customer B's cart."""
        # Unauthenticated access
        res = self.client.get("/cart", follow_redirects=True)
        self.assertIn(b"Please login to access this page", res.data)

        # Customer A adds an item
        self.register_user(name="Customer A", email="test_cust_a@example.com", password="password123", confirm_password="password123")
        self.login_user(email="test_cust_a@example.com", password="password123")
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)
        self.client.get("/logout", follow_redirects=True)

        # Customer B logs in
        self.register_user(name="Customer B", email="test_cust_b@example.com", password="password123", confirm_password="password123")
        self.login_user(email="test_cust_b@example.com", password="password123")
        res_b = self.client.get("/cart")

        # Customer B's cart should be empty!
        self.assertIn(b"Your Cart is Currently Empty", res_b.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res_b.data)

    # ==============================================================================
    # GOOGLE AUTHENTICATION TESTS (Test Cases 26-37)
    # ==============================================================================

    def test_26_google_login_missing_config(self):
        """Test Case 26 (Requirement 7.6): Missing OAuth configuration redirects with error."""
        self.app.config["GOOGLE_CLIENT_ID"] = ""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": ""}):
            res = self.client.get("/auth/google/login", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Google OAuth is not configured", res.data)

    def test_27_google_login_redirect_with_config(self):
        """Test Case 27 (Requirement 7.1): Google login initiates flow and redirects to Google."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-12345"
        res = self.client.get("/auth/google/login")
        self.assertEqual(res.status_code, 302)
        location = res.headers.get("Location", "")
        self.assertIn("accounts.google.com/o/oauth2/v2/auth", location)
        self.assertIn("client_id=test-client-id-12345", location)
        self.assertIn("response_type=code", location)
        self.assertIn("scope=openid+email+profile", location)

        # Check session contains state
        with self.client.session_transaction() as sess:
            self.assertIn("oauth_state", sess)
            self.assertTrue(len(sess["oauth_state"]) > 16)

    def test_28_google_callback_user_cancelled(self):
        """Test Case 28 (Requirement 7.4): User cancels Google sign-in."""
        res = self.client.get("/auth/google/callback?error=access_denied", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Google sign-in was cancelled", res.data)

    def test_29_google_callback_csrf_state_mismatch(self):
        """Test Case 29 (Requirement 7.5a): State parameter mismatch / CSRF attack is rejected."""
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "legitimate-token-abc"

        res = self.client.get("/auth/google/callback?code=mock_code&state=forged-state-xyz", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"State parameter mismatch", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_30_google_callback_invalid_or_expired_token(self, mock_verify, mock_post):
        """Test Case 30 (Requirement 7.5b): Invalid or expired ID token fails gracefully."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-12345"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret-abc"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "expired.jwt.token"}
        mock_post.return_value = mock_post_resp

        mock_verify.side_effect = ValueError("Token has expired")

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid-state"

        res = self.client.get("/auth/google/callback?code=valid-code&state=valid-state", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Google ID token verification failed", res.data)
        self.assertIn(b"Token has expired", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_31_google_callback_unverified_email_rejected(self, mock_verify, mock_post):
        """Test Case 31 (Requirement 7.5c): Unverified Google email is rejected."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-12345"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret-abc"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "mock.jwt.token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "google-user-unverified",
            "email": "unverified@example.com",
            "name": "Unverified User",
            "email_verified": False,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid-state"

        res = self.client.get("/auth/google/callback?code=valid-code&state=valid-state", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Google email is not verified", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_32_google_callback_first_time_registration(self, mock_verify, mock_post):
        """Test Case 32 (Requirement 7.2): First-time Google user creates account and logs into dashboard."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-12345"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret-abc"

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "valid.id.token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "google-sub-first-time-987",
            "email": "testgooglefirst@example.com",
            "name": "First Time Google User",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-reg"

        res = self.client.get("/auth/google/callback?code=auth-code-123&state=state-reg", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your account has been created with Google", res.data)
        self.assertIn(b"First Time Google User", res.data)
        self.assertIn(b"Google Account Connected", res.data)

        # Check customer record in SQLite
        conn = database.get_db_connection()
        user_row = conn.execute("SELECT * FROM customers WHERE email = 'testgooglefirst@example.com';").fetchone()
        conn.close()
        self.assertIsNotNone(user_row)
        self.assertEqual(user_row["google_id"], "google-sub-first-time-987")
        self.assertIsNone(user_row["password_hash"])

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_33_google_callback_returning_user_login(self, mock_verify, mock_post):
        """Test Case 33 (Requirement 7.3): Returning Google user logs into their existing account."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-12345"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret-abc"

        # Pre-seed returning Google customer
        conn = database.get_db_connection()
        conn.execute(
            "INSERT INTO customers (name, email, password_hash, google_id) VALUES (?, ?, NULL, ?);",
            ("Returning User", "testreturning@example.com", "google-sub-returning-555")
        )
        conn.commit()
        conn.close()

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "valid.id.token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "google-sub-returning-555",
            "email": "testreturning@example.com",
            "name": "Returning User",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-ret"

        res = self.client.get("/auth/google/callback?code=code-555&state=state-ret", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome back, Returning User!", res.data)
        self.assertIn(b"Google Account Connected", res.data)

    @patch("app.requests.post")
    @patch("app.id_token.verify_oauth2_token")
    def test_34_safe_account_linking_flow(self, mock_verify, mock_post):
        """Test Case 34 (Requirement 7.9): Existing password account requires password verification before linking."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-12345"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret-abc"

        # 1. Customer already exists with a password
        self.register_user(name="Local User", email="testexistinglink@example.com", password="password123", confirm_password="password123")

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {"id_token": "valid.id.token"}
        mock_post.return_value = mock_post_resp

        mock_verify.return_value = {
            "sub": "google-link-sub-777",
            "email": "testexistinglink@example.com",
            "name": "Local User",
            "email_verified": True,
            "iss": "https://accounts.google.com"
        }

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "state-link"

        # 2. Google callback should NOT auto-merge; must redirect to /auth/google/link
        res = self.client.get("/auth/google/callback?code=code-777&state=state-link", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Link Google Account", res.data)
        self.assertIn(b"Existing Account Detected", res.data)

        # 3. Submit wrong password -> rejected
        res_wrong = self.client.post("/auth/google/link", data={"password": "wrong-password"}, follow_redirects=True)
        self.assertEqual(res_wrong.status_code, 200)
        self.assertIn(b"Incorrect password", res_wrong.data)

        # 4. Submit correct password -> verified and linked
        res_correct = self.client.post("/auth/google/link", data={"password": "password123"}, follow_redirects=True)
        self.assertEqual(res_correct.status_code, 200)
        self.assertIn(b"Google account successfully linked!", res_correct.data)
        self.assertIn(b"Google Account Connected", res_correct.data)

        # Verify database has google_id linked
        conn = database.get_db_connection()
        row = conn.execute("SELECT google_id FROM customers WHERE email = 'testexistinglink@example.com';").fetchone()
        conn.close()
        self.assertEqual(row["google_id"], "google-link-sub-777")

    def test_35_google_user_password_login_attempt(self):
        """Test Case 35 (Requirement 7.10): User registered via Google cannot login via password form."""
        conn = database.get_db_connection()
        conn.execute(
            "INSERT INTO customers (name, email, password_hash, google_id) VALUES (?, ?, NULL, ?);",
            ("OAuth Only User", "testoauthonly@example.com", "google-sub-only")
        )
        conn.commit()
        conn.close()

        res = self.login_user(email="testoauthonly@example.com", password="somepassword")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"This account was created with Google Sign-In", res.data)

    def test_36_google_user_logout(self):
        """Test Case 36 (Requirement 7.7): Logout successfully terminates Google authenticated session."""
        with self.client.session_transaction() as sess:
            sess["customer_id"] = 100
            sess["customer_name"] = "Google Authenticated"
            sess["customer_email"] = "testgoogleout@example.com"
            sess["auth_provider"] = "google"

        res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"You have been logged out successfully", res.data)

        # Confirm session is cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)

    def test_37_protected_routes_without_login(self):
        """Test Case 37 (Requirement 7.8): Unauthenticated requests to protected pages are blocked."""
        routes = ["/dashboard", "/products", "/cart"]
        for route in routes:
            res = self.client.get(route, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Please login to access this page", res.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
