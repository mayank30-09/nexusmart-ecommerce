"""
tests/test_checkout_discounts.py - Phase 2B: Checkout Review and Discount Validation Test Suite.
Covers:
  1. Unauthenticated checkout access (GET /checkout and POST actions redirect to /login)
  2. Empty-cart checkout handling (redirects with warning to /cart)
  3. Valid checkout preview with customer-owned address & products
  4. Rejection of foreign-customer address IDs and cross-customer address isolation
  5. Accurate server-side subtotal and final payable amount calculation
  6. Valid percentage discount coupon calculation
  7. Valid fixed-amount discount coupon calculation
  8. Rejection of invalid, empty, or nonexistent coupons
  9. Rejection of expired, inactive, or future-dated coupons
  10. Enforcement of minimum cart purchase requirements and automatic coupon drop on subtotal change
  11. Discount boundary enforcement (preventing negative totals or discount exceeding subtotal) and rounding precision
  12. Coupon usage limit enforcement and non-incrementation during preview
  13. CSRF anti-forgery protection on all checkout POST endpoints
  14. Coupon removal and restoration of full cart total
  15. Stock discrepancy warnings and database schema preservation across reinitializations
"""

import os
import sys
import unittest
import sqlite3

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app
from tests.conftest import BaseTestCase


class TestCheckoutAndDiscounts(BaseTestCase, unittest.TestCase):
    """Automated test suite for Phase 2B: Checkout Review & Discount Validation."""

    def setUp(self):
        super().setUp()
        # Register and log in Alice as default customer
        self.register(name="Alice Buyer", email="alice@test.com", password="password123", confirm="password123")
        self.login(email="alice@test.com", password="password123")

        # Add default address for Alice
        conn = database.get_db_connection()
        alice_id = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()["id"]
        conn.execute("""
            INSERT INTO customer_addresses (customer_id, address_line, city, state, postal_code, is_default)
            VALUES (?, '123 Market St', 'Bangalore', 'Karnataka', '560001', 1);
        """, (alice_id,))

        # Fetch product 1 (Headphones: ₹2999, stock 15) and product 3 (T-Shirt: ₹499, stock 35)
        self.alice_id = alice_id
        conn.commit()
        conn.close()

    def add_product_to_cart(self, product_id, quantity=1):
        """Helper to add an item to the active customer's cart."""
        return self.client.post("/cart/add", data={
            "product_id": product_id,
            "quantity": quantity
        }, follow_redirects=True)

    # ==========================================================================
    # 1. AUTHENTICATION & ACCESS CONTROL
    # ==========================================================================

    def test_01_unauthenticated_checkout_access(self):
        """Unauthenticated requests to /checkout or checkout POST endpoints redirect to /login."""
        unauth_client = self.app.test_client()

        # GET /checkout without session
        res = unauth_client.get("/checkout")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

        followed = unauth_client.get("/checkout", follow_redirects=True)
        self.assertEqual(followed.status_code, 200)
        self.assertIn(b"Please login to access this page", followed.data)

        # POST /checkout/coupon without session
        res_coupon = unauth_client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"})
        self.assertEqual(res_coupon.status_code, 302)
        self.assertIn("/login", res_coupon.headers.get("Location", ""))

        # POST /checkout/select-address without session
        res_addr = unauth_client.post("/checkout/select-address", data={"address_id": 1})
        self.assertEqual(res_addr.status_code, 302)
        self.assertIn("/login", res_addr.headers.get("Location", ""))

    # ==========================================================================
    # 2. EMPTY CART BEHAVIOR
    # ==========================================================================

    def test_02_empty_cart_checkout(self):
        """Accessing /checkout with an empty cart redirects to /cart with a clear warning."""
        res = self.client.get("/checkout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your shopping cart is empty", res.data)
        self.assertIn(b"Shopping Cart", res.data)

    # ==========================================================================
    # 3. VALID CHECKOUT WITH OWNED ADDRESS
    # ==========================================================================

    def test_03_valid_checkout_with_owned_address(self):
        """Customer with items and saved address sees itemized review and destination address."""
        self.add_product_to_cart(1, quantity=1)  # Headphones ₹2999

        res = self.client.get("/checkout")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Order Checkout Review", res.data)
        self.assertIn(b"123 Market St", res.data)
        self.assertIn(b"Bangalore", res.data)
        self.assertIn(b"560001", res.data)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertIn(b"2999.00", res.data)
        self.assertIn(b"Proceed to Payment", res.data)

    # ==========================================================================
    # 4. CROSS-CUSTOMER ADDRESS ISOLATION & REJECTION
    # ==========================================================================

    def test_04_rejection_of_foreign_customer_address(self):
        """A customer cannot select another customer's address during checkout."""
        # Alice has address ID belonging to self.alice_id
        conn = database.get_db_connection()
        alice_addr = conn.execute("SELECT id FROM customer_addresses WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        alice_addr_id = alice_addr["id"]
        conn.close()

        # Log out Alice and register/login Bob
        self.client.get("/logout", follow_redirects=True)
        self.register(name="Bob Buyer", email="bob@test.com", password="password123", confirm="password123")
        self.login(email="bob@test.com", password="password123")

        # Bob adds an item and his own address
        self.add_product_to_cart(1, quantity=1)
        self.client.post("/addresses/add", data={
            "address_line": "456 Oak Avenue",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001",
            "is_default": "1"
        }, follow_redirects=True)

        # Bob attempts to select Alice's address ID
        res = self.client.post("/checkout/select-address", data={
            "address_id": alice_addr_id
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Selected delivery address does not exist or does not belong to your account", res.data)
        # Verify Bob's checkout renders his own address, not Alice's
        self.assertIn(b"456 Oak Avenue", res.data)
        self.assertNotIn(b"123 Market St", res.data)

    # ==========================================================================
    # 5. SERVER-CALCULATED FINANCIAL AMOUNTS
    # ==========================================================================

    def test_05_correct_subtotal_and_final_amount(self):
        """Financial calculations are performed on server using database product prices."""
        # Add Product 2 (₹1899 x 2 = ₹3798.00) and Product 3 (₹499 x 3 = ₹1497.00)
        # Expected subtotal: ₹5295.00
        self.add_product_to_cart(2, quantity=2)
        self.add_product_to_cart(3, quantity=3)

        res = self.client.get("/checkout")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"5295.00", res.data)

    # ==========================================================================
    # 6. PERCENTAGE COUPON VALIDATION
    # ==========================================================================

    def test_06_valid_percentage_coupon(self):
        """WELCOME10 (10% off, min ₹500) applies 10% discount on cart subtotal."""
        self.add_product_to_cart(1, quantity=1)  # ₹2999.00

        res_apply = self.client.post("/checkout/coupon", data={
            "coupon_code": "WELCOME10"
        }, follow_redirects=True)

        self.assertEqual(res_apply.status_code, 200)
        self.assertIn(b"WELCOME10", res_apply.data)
        self.assertIn(b"applied successfully", res_apply.data)

        # 10% of 2999.00 is 299.90. Final total = 2999.00 - 299.90 = 2699.10
        self.assertIn(b"299.90", res_apply.data)
        self.assertIn(b"2699.10", res_apply.data)

    # ==========================================================================
    # 7. FIXED AMOUNT COUPON VALIDATION
    # ==========================================================================

    def test_07_valid_fixed_amount_coupon(self):
        """FLAT200 (₹200 off, min ₹1000) applies flat ₹200 discount."""
        self.add_product_to_cart(1, quantity=1)  # ₹2999.00

        res_apply = self.client.post("/checkout/coupon", data={
            "coupon_code": "FLAT200"
        }, follow_redirects=True)

        self.assertEqual(res_apply.status_code, 200)
        self.assertIn(b"FLAT200", res_apply.data)
        self.assertIn(b"applied successfully", res_apply.data)

        # Discount = 200.00, Final = 2999.00 - 200.00 = 2799.00
        self.assertIn(b"200.00", res_apply.data)
        self.assertIn(b"2799.00", res_apply.data)

    # ==========================================================================
    # 8. INVALID AND NONEXISTENT COUPONS
    # ==========================================================================

    def test_08_invalid_and_nonexistent_coupons(self):
        """Empty, whitespace-only, or bogus coupon codes are rejected without applying discount."""
        self.add_product_to_cart(1, quantity=1)

        # Empty coupon
        res_empty = self.client.post("/checkout/coupon", data={"coupon_code": ""}, follow_redirects=True)
        self.assertIn(b"Please enter a coupon code", res_empty.data)

        # Bogus coupon
        res_bogus = self.client.post("/checkout/coupon", data={"coupon_code": "NONEXISTENT99"}, follow_redirects=True)
        self.assertIn(b"NONEXISTENT99", res_bogus.data)
        self.assertIn(b"is invalid or does not exist", res_bogus.data)

        # Confirm subtotal remains unchanged at ₹2999.00
        self.assertIn(b"2999.00", res_bogus.data)

    # ==========================================================================
    # 9. EXPIRED AND INACTIVE COUPONS
    # ==========================================================================

    def test_09_expired_and_inactive_coupons(self):
        """Expired, inactive, or future-dated coupons are rejected with descriptive messages."""
        self.add_product_to_cart(1, quantity=1)

        # Expired coupon
        res_exp = self.client.post("/checkout/coupon", data={"coupon_code": "EXPIRED50"}, follow_redirects=True)
        self.assertIn(b"EXPIRED50", res_exp.data)
        self.assertIn(b"has expired", res_exp.data)

        # Inactive coupon
        res_inact = self.client.post("/checkout/coupon", data={"coupon_code": "INACTIVE20"}, follow_redirects=True)
        self.assertIn(b"INACTIVE20", res_inact.data)
        self.assertIn(b"is inactive", res_inact.data)

        # Future-dated coupon
        res_future = self.client.post("/checkout/coupon", data={"coupon_code": "FUTURE25"}, follow_redirects=True)
        self.assertIn(b"FUTURE25", res_future.data)
        self.assertIn(b"not yet active", res_future.data)

    # ==========================================================================
    # 10. MINIMUM PURCHASE REQUIREMENT
    # ==========================================================================

    def test_10_minimum_purchase_requirements(self):
        """Coupons requiring a minimum cart subtotal reject ineligible carts and drop if subtotal drops."""
        # Add 1 T-Shirt = ₹499.00
        self.add_product_to_cart(3, quantity=1)

        # WELCOME10 requires min ₹500.00
        res = self.client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"}, follow_redirects=True)
        self.assertIn(b"requires a minimum cart subtotal of", res.data)
        self.assertIn(b"499.00", res.data)

        # Now increase cart subtotal above ₹500 by adding another item
        self.add_product_to_cart(3, quantity=1)  # Subtotal now ₹998.00
        res_valid = self.client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"}, follow_redirects=True)
        self.assertIn(b"WELCOME10", res_valid.data)
        self.assertIn(b"applied successfully", res_valid.data)

        # Now simulate cart modification reducing subtotal back to ₹499
        conn = database.get_db_connection()
        conn.execute("UPDATE cart_items SET quantity = 1 WHERE customer_id = ?;", (self.alice_id,))
        conn.commit()
        conn.close()

        # Viewing /checkout should automatically detect the shortfall, remove coupon, and notify customer
        res_recheck = self.client.get("/checkout")
        self.assertIn(b"Coupon has been removed", res_recheck.data)

    # ==========================================================================
    # 11. DISCOUNT BOUNDARIES AND SAFE ARITHMETIC
    # ==========================================================================

    def test_11_discount_boundary_and_rounding(self):
        """Discount cannot exceed subtotal and final payable total can never be negative."""
        # Add T-shirt (₹499)
        self.add_product_to_cart(3, quantity=1)

        # Insert a high-value fixed coupon (₹1000 off)
        conn = database.get_db_connection()
        conn.execute("""
            INSERT INTO coupons (code, discount_type, discount_value, min_cart_value, is_active)
            VALUES ('MEGADEAL', 'fixed', 1000.0, 0.0, 1);
        """)
        conn.commit()
        conn.close()

        try:
            res = self.client.post("/checkout/coupon", data={"coupon_code": "MEGADEAL"}, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # Discount should be capped at ₹499.00, and final total must be ₹0.00 (not -₹501)
            self.assertIn("-₹499.00".encode("utf-8"), res.data)
            self.assertIn("₹0.00".encode("utf-8"), res.data)
            self.assertNotIn(b"-501", res.data)
        finally:
            conn = database.get_db_connection()
            conn.execute("DELETE FROM coupons WHERE code = 'MEGADEAL';")
            conn.commit()
            conn.close()

    # ==========================================================================
    # 12. USAGE LIMITS & NON-INCREMENTATION ON PREVIEW
    # ==========================================================================

    def test_12_usage_limits_and_preview_safety(self):
        """Coupons at usage limit are rejected, and previewing checkout never increments used_count."""
        self.add_product_to_cart(1, quantity=1)

        # MAXEDOUT has used_count = 5 and usage_limit = 5
        res = self.client.post("/checkout/coupon", data={"coupon_code": "MAXEDOUT"}, follow_redirects=True)
        self.assertIn(b"has reached its usage limit", res.data)

        # Apply a valid coupon FLAT200 and check that previewing checkout does not increment used_count
        conn = database.get_db_connection()
        count_before = conn.execute("SELECT used_count FROM coupons WHERE code = 'FLAT200';").fetchone()["used_count"]
        conn.close()

        self.client.post("/checkout/coupon", data={"coupon_code": "FLAT200"}, follow_redirects=True)
        self.client.get("/checkout")  # Multiple previews
        self.client.get("/checkout")

        conn = database.get_db_connection()
        count_after = conn.execute("SELECT used_count FROM coupons WHERE code = 'FLAT200';").fetchone()["used_count"]
        conn.close()

        self.assertEqual(count_before, count_after, "Checkout preview must never increment coupon used_count")

    # ==========================================================================
    # 13. CSRF PROTECTION ON STATE-CHANGING ENDPOINTS
    # ==========================================================================

    def test_13_csrf_protection_on_checkout_post_requests(self):
        """POST /checkout/coupon, select-address, and coupon/remove reject forged requests without CSRF token."""
        self.add_product_to_cart(1, quantity=1)

        self.app.config["TESTING"] = False
        self.app.config["WTF_CSRF_ENABLED"] = True

        try:
            # 1. Apply coupon without token
            res_coupon = self.client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"}, follow_redirects=True)
            self.assertIn(b"Security verification failed", res_coupon.data)

            # 2. Select address without token
            res_addr = self.client.post("/checkout/select-address", data={"address_id": 1}, follow_redirects=True)
            self.assertIn(b"Security verification failed", res_addr.data)

            # 3. Remove coupon without token
            res_rem = self.client.post("/checkout/coupon/remove", data={}, follow_redirects=True)
            self.assertIn(b"Security verification failed", res_rem.data)

            # 4. Valid CSRF token succeeds
            with self.client.session_transaction() as sess:
                valid_token = sess.get("csrf_token")

            res_valid = self.client.post("/checkout/coupon", data={
                "csrf_token": valid_token,
                "coupon_code": "WELCOME10"
            }, follow_redirects=True)
            self.assertIn(b"applied successfully", res_valid.data)

        finally:
            self.app.config["TESTING"] = True
            self.app.config["WTF_CSRF_ENABLED"] = False

    # ==========================================================================
    # 14. COUPON REMOVAL RESTORES ORIGINAL TOTAL
    # ==========================================================================

    def test_14_coupon_removal_restores_original_total(self):
        """Removing an applied coupon restores the original full subtotal."""
        self.add_product_to_cart(1, quantity=1)  # ₹2999.00

        # Apply coupon
        self.client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"}, follow_redirects=True)

        # Remove coupon
        res_remove = self.client.post("/checkout/coupon/remove", follow_redirects=True)
        self.assertEqual(res_remove.status_code, 200)
        self.assertIn(b"Coupon removed from checkout", res_remove.data)
        self.assertIn(b"2999.00", res_remove.data)
        self.assertNotIn(b"2699.10", res_remove.data)

    # ==========================================================================
    # 15. STOCK WARNING & DATABASE SCHEMA PRESERVATION
    # ==========================================================================

    def test_15_stock_warning_and_schema_preservation(self):
        """Cart quantity exceeding stock displays an inventory alert, and init_db preserves data."""
        self.add_product_to_cart(1, quantity=2)

        # Reduce warehouse stock to 1 to simulate concurrent depletion
        conn = database.get_db_connection()
        orig_stock = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
        conn.execute("UPDATE products SET stock = 1 WHERE id = 1;")
        conn.commit()
        conn.close()

        try:
            res = self.client.get("/checkout")
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Inventory Alert", res.data)
            self.assertIn(b"exceeds available stock", res.data)

            # Re-run init_db() to test non-destructive idempotency
            database.init_db()

            # Verify Alice's customer account, address, and cart records persist unharmed
            conn = database.get_db_connection()
            alice_check = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
            self.assertIsNotNone(alice_check)
            cart_check = conn.execute("SELECT COUNT(*) AS count FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchone()
            self.assertGreater(cart_check["count"], 0)
            conn.close()
        finally:
            # Restore product 1 stock to prevent side-effects in subsequent test suites
            conn = database.get_db_connection()
            conn.execute("UPDATE products SET stock = ? WHERE id = 1;", (orig_stock,))
            conn.commit()
            conn.close()
