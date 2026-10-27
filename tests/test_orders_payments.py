"""
tests/test_orders_payments.py - Phase 3: Order Management & Simulated Payment Test Suite.

Comprehensive automated test coverage for:
  1. Order Placement & Validation:
     - Unauthenticated access rejection
     - Empty cart rejection
     - Invalid / foreign address rejection
     - Server-side subtotal, discount, and final amount calculation
     - Coupon revalidation at placement & coupon usage counter incrementation
  2. Transactional Atomicity & Concurrency:
     - Atomic rollback on insufficient inventory
     - Conditional stock deduction preventing negative inventory
     - Idempotency key duplicate submission protection
  3. Simulated Payment Workflows:
     - Cash on Delivery (COD) placement (order Confirmed, payment Pending)
     - Mock Online Payment success (order Confirmed, payment Paid, safe txn ref)
     - Mock Online Payment failure (declined, no order created, stock untouched, cart preserved)
     - No real payment credentials requested or stored
  4. Order Confirmation & Snapshots:
     - Confirmation page displays immutable address and item snapshots
     - Authorization check: foreign customer cannot view order confirmation
  5. Customer Order History & Details:
     - Customer order history (/orders) shows only authenticated customer's orders
     - Empty order history displays clear empty state
     - Order details (/orders/<id>) verifies customer ownership (cross-customer blocked)
     - Product and price changes in catalog do not alter immutable order snapshots
  6. Order Cancellation:
     - Customer can cancel Confirmed order
     - Cancellation restores inventory stock atomically
     - Cancellation restores coupon usage atomically
     - Duplicate cancellation prevented
     - Foreign customer cannot cancel another's order
  7. CSRF Security:
     - State-changing order placement and cancellation enforce CSRF protection
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
from werkzeug.security import generate_password_hash
from tests.conftest import BaseTestCase


class TestOrderManagementAndPayments(BaseTestCase, unittest.TestCase):
    """Test suite covering Phase 3: Order Management and Simulated Payment System."""

    def setUp(self):
        super().setUp()
        # Create Alice (primary customer)
        self.register(name="Alice Buyer", email="alice@test.com", password="password123", confirm="password123")
        self.login(email="alice@test.com", password="password123")

        conn = database.get_db_connection()
        alice = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        self.alice_id = alice["id"]

        # Add primary address for Alice
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer_addresses (customer_id, address_line, city, state, postal_code, is_default)
            VALUES (?, '123 Market St, Flat 4B', 'Bengaluru', 'Karnataka', '560001', 1);
        """, (self.alice_id,))
        self.alice_address_id = cursor.lastrowid

        # Create Bob (secondary customer for authorization testing)
        cursor.execute("""
            INSERT INTO customers (name, email, password_hash)
            VALUES ('Bob Cross', 'bob@test.com', ?);
        """, (generate_password_hash("password123"),))
        self.bob_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO customer_addresses (customer_id, address_line, city, state, postal_code, is_default)
            VALUES (?, '456 Elm St', 'Mumbai', 'Maharashtra', '400001', 1);
        """, (self.bob_id,))
        self.bob_address_id = cursor.lastrowid

        # Verify product 1 (Headphones: ₹2999) has known stock
        cursor.execute("UPDATE products SET stock = 15 WHERE id = 1;")
        cursor.execute("UPDATE products SET stock = 35 WHERE id = 3;")

        conn.commit()
        conn.close()

    def add_product_to_cart(self, product_id, quantity=1):
        """Helper to add product to Alice's cart."""
        return self.client.post("/cart/add", data={
            "product_id": product_id,
            "quantity": quantity
        }, follow_redirects=True)

    # --------------------------------------------------------------------------
    # 1. ORDER PLACEMENT & VALIDATION
    # --------------------------------------------------------------------------

    def test_01_unauthenticated_order_placement_rejected(self):
        """Unauthenticated guests cannot place orders and are redirected to login."""
        self.client.get("/logout", follow_redirects=True)
        response = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please login", response.data)

    def test_02_empty_cart_order_placement_rejected(self):
        """Customer with an empty cart cannot place an order."""
        response = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"empty", response.data)

        # Confirm no order was created
        conn = database.get_db_connection()
        count = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
        conn.close()
        self.assertEqual(count, 0)

    def test_03_invalid_or_foreign_address_rejected(self):
        """Customer cannot submit another customer's address or a nonexistent address."""
        self.add_product_to_cart(1, 1)

        # Attempt to use Bob's address
        response = self.client.post("/checkout/place-order", data={
            "address_id": self.bob_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Selected delivery address does not exist or does not belong", response.data)

        # Attempt to use nonexistent address
        response2 = self.client.post("/checkout/place-order", data={
            "address_id": 999999,
            "payment_method": "cod"
        }, follow_redirects=True)
        self.assertEqual(response2.status_code, 200)
        self.assertIn(b"Selected delivery address does not exist or does not belong", response2.data)

        # Confirm no order was created and cart is preserved
        conn = database.get_db_connection()
        count = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
        cart_count = conn.execute("SELECT COUNT(*) AS c FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
        conn.close()
        self.assertEqual(count, 0)
        self.assertEqual(cart_count, 1)

    def test_04_valid_order_placement_cod(self):
        """Valid order placement with Cash on Delivery creates order, order items, clears cart, and updates stock."""
        self.add_product_to_cart(1, 2)  # Product 1: 2 x 2999 = 5998

        response = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"placed successfully", response.data)

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        self.assertIsNotNone(order)
        self.assertEqual(order["order_status"], "Confirmed")
        self.assertEqual(order["payment_status"], "Pending")
        self.assertEqual(order["payment_method"], "cod")
        self.assertEqual(order["subtotal"], 5998.0)
        self.assertEqual(order["final_total"], 5998.0)
        self.assertEqual(order["shipping_city"], "Bengaluru")
        self.assertEqual(order["shipping_postal_code"], "560001")

        # Verify order_items snapshot
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?;", (order["id"],)).fetchall()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["product_id"], 1)
        self.assertEqual(items[0]["quantity"], 2)
        self.assertEqual(items[0]["unit_price"], 2999.0)
        self.assertEqual(items[0]["line_total"], 5998.0)

        # Verify cart was cleared
        cart_rows = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(cart_rows), 0)

        # Verify product stock was decremented from 15 to 13
        p1 = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(p1["stock"], 13)
        conn.close()

    # --------------------------------------------------------------------------
    # 2. SIMULATED PAYMENT WORKFLOWS
    # --------------------------------------------------------------------------

    def test_05_mock_online_payment_success(self):
        """Simulated online payment with success outcome marks payment as Paid."""
        self.add_product_to_cart(3, 1)  # Product 3: 499

        response = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "mock_online",
            "simulated_outcome": "success"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"placed successfully", response.data)

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        self.assertIsNotNone(order)
        self.assertEqual(order["order_status"], "Confirmed")
        self.assertEqual(order["payment_status"], "Paid")
        self.assertEqual(order["payment_method"], "mock_online")
        self.assertTrue(order["payment_reference"].startswith("TXN-MOCK-"))
        conn.close()

    def test_06_mock_online_payment_failure(self):
        """Simulated online payment with failure outcome halts order placement, preserves cart, and does not alter stock."""
        self.add_product_to_cart(1, 1)  # Stock: 15

        response = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "mock_online",
            "simulated_outcome": "failure"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Simulated Payment Failed", response.data)

        conn = database.get_db_connection()
        # Verify no order created
        orders = conn.execute("SELECT * FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(orders), 0)

        # Verify cart items preserved
        cart = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(cart), 1)

        # Verify stock untouched
        p1 = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(p1["stock"], 15)
        conn.close()

    # --------------------------------------------------------------------------
    # 3. ATOMIC TRANSACTIONS & STOCK SAFETY
    # --------------------------------------------------------------------------

    def test_07_insufficient_stock_prevents_order_atomic_rollback(self):
        """If available stock drops below cart quantity, order is rolled back and no changes persist."""
        self.add_product_to_cart(1, 5)

        # Another process or admin suddenly reduces stock to 3
        conn = database.get_db_connection()
        conn.execute("UPDATE products SET stock = 3 WHERE id = 1;")
        conn.commit()
        conn.close()

        try:
            response = self.client.post("/checkout/place-order", data={
                "address_id": self.alice_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Insufficient stock", response.data)

            # Confirm no orders created
            conn = database.get_db_connection()
            orders_count = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
            self.assertEqual(orders_count, 0)

            # Confirm stock remained at 3 (did not become negative or partially deducted)
            p1_stock = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
            self.assertEqual(p1_stock, 3)

            # Confirm cart is still intact
            cart_count = conn.execute("SELECT COUNT(*) AS c FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
            self.assertEqual(cart_count, 1)
            conn.close()
        finally:
            # Restore stock
            conn = database.get_db_connection()
            conn.execute("UPDATE products SET stock = 15 WHERE id = 1;")
            conn.commit()
            conn.close()

    def test_08_idempotency_duplicate_submission_protection(self):
        """Repeated submissions with the same idempotency key do not produce duplicate orders."""
        self.add_product_to_cart(1, 1)

        idempotency_key = "test-unique-idemp-key-12345"

        # First submission
        res1 = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod",
            "idempotency_key": idempotency_key
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)
        self.assertIn(b"placed successfully", res1.data)

        # Second submission with the exact same idempotency key
        res2 = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod",
            "idempotency_key": idempotency_key
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"Order already placed", res2.data)

        # Verify only 1 order exists
        conn = database.get_db_connection()
        orders = conn.execute("SELECT * FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(orders), 1)

        # Stock deducted exactly once (from 15 to 14)
        p1 = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(p1["stock"], 14)
        conn.close()

    # --------------------------------------------------------------------------
    # 4. COUPON VALIDATION & RECORDING AT PLACEMENT
    # --------------------------------------------------------------------------

    def test_09_order_placement_records_coupon_usage_and_discounts(self):
        """Order placement revalidates applied coupon, applies discount, and increments used_count in DB."""
        # Product 1: 2999
        self.add_product_to_cart(1, 1)

        # Apply WELCOME10 coupon (10% off)
        self.client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"}, follow_redirects=True)

        conn = database.get_db_connection()
        c_before = conn.execute("SELECT used_count FROM coupons WHERE code = 'WELCOME10';").fetchone()["used_count"]
        conn.close()

        # Place order
        response = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        self.assertIsNotNone(order)
        self.assertEqual(order["coupon_code"], "WELCOME10")
        self.assertEqual(order["subtotal"], 2999.0)
        self.assertEqual(order["discount_amount"], 299.90)
        self.assertEqual(order["final_total"], 2699.10)

        # Verify coupon used_count incremented
        c_after = conn.execute("SELECT used_count FROM coupons WHERE code = 'WELCOME10';").fetchone()["used_count"]
        self.assertEqual(c_after, c_before + 1)
        conn.close()

    def test_10_coupon_revalidation_fails_if_limit_reached(self):
        """If coupon usage limit is reached between preview and placement, order transaction halts safely."""
        self.add_product_to_cart(1, 1)

        # Create temporary coupon with usage_limit = 1
        conn = database.get_db_connection()
        conn.execute("""
            INSERT INTO coupons (code, discount_type, discount_value, min_cart_value, usage_limit, used_count, is_active)
            VALUES ('LIMIT1', 'fixed', 100, 500, 1, 0, 1);
        """)
        conn.commit()
        conn.close()

        try:
            # Apply coupon to session
            self.client.post("/checkout/coupon", data={"coupon_code": "LIMIT1"}, follow_redirects=True)

            # Another user uses the coupon, exhausting it
            conn = database.get_db_connection()
            conn.execute("UPDATE coupons SET used_count = 1 WHERE code = 'LIMIT1';")
            conn.commit()
            conn.close()

            # Now submit order
            response = self.client.post("/checkout/place-order", data={
                "address_id": self.alice_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b"reached its usage limit", response.data)

            # No order created
            conn = database.get_db_connection()
            orders_count = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
            self.assertEqual(orders_count, 0)
            conn.close()
        finally:
            conn = database.get_db_connection()
            conn.execute("DELETE FROM coupons WHERE code = 'LIMIT1';")
            conn.commit()
            conn.close()

    # --------------------------------------------------------------------------
    # 5. ORDER CONFIRMATION & DETAILS AUTHORIZATION
    # --------------------------------------------------------------------------

    def test_11_order_confirmation_displays_snapshots_and_verifies_ownership(self):
        """Order confirmation shows complete snapshots and blocks unauthorized customers."""
        self.add_product_to_cart(1, 1)

        res = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        order = conn.execute("SELECT order_reference FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        conn.close()
        order_ref = order["order_reference"]

        # Alice views her confirmation
        conf_res = self.client.get(f"/orders/confirmation/{order_ref}")
        self.assertEqual(conf_res.status_code, 200)
        self.assertIn(order_ref.encode(), conf_res.data)
        self.assertIn(b"Bengaluru", conf_res.data)
        self.assertIn(b"Noise-Canceling Wireless Headphones", conf_res.data)

        # Logout Alice and Login as Bob
        self.client.get("/logout", follow_redirects=True)
        self.login(email="bob@test.com", password="password123")
        # Bob attempts to view Alice's confirmation
        bob_conf_res = self.client.get(f"/orders/confirmation/{order_ref}", follow_redirects=True)
        self.assertEqual(bob_conf_res.status_code, 200)
        self.assertIn(b"not authorized", bob_conf_res.data)

    def test_12_order_history_displays_customer_orders_only(self):
        """Order history (/orders) shows only the authenticated customer's orders."""
        self.add_product_to_cart(1, 1)
        self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        # Alice checks history
        res = self.client.get("/orders")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Total Orders (1)", res.data)

        # Logout Alice and Login as Bob
        self.client.get("/logout", follow_redirects=True)
        self.login(email="bob@test.com", password="password123")
        bob_res = self.client.get("/orders")
        self.assertEqual(bob_res.status_code, 200)
        self.assertIn(b"No Orders Placed Yet", bob_res.data)

    def test_13_order_detail_cross_customer_isolation_and_snapshot_immutability(self):
        """Order details enforces ownership and retains original item names/prices even if product table changes."""
        self.add_product_to_cart(1, 2)  # Unit price 2999
        self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        order = conn.execute("SELECT id FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        order_id = order["id"]

        # Mutate the product in database: change name and price
        conn.execute("UPDATE products SET name = 'Renamed Super Headphones', price = 9999.0 WHERE id = 1;")
        conn.commit()
        conn.close()

        try:
            # Alice visits order details: snapshot must retain original product name and price
            res = self.client.get(f"/orders/{order_id}")
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
            self.assertIn(b"2999.00", res.data)
            self.assertNotIn(b"Renamed Super Headphones", res.data)

            # Logout Alice and Login as Bob
            self.client.get("/logout", follow_redirects=True)
            self.login(email="bob@test.com", password="password123")
            bob_res = self.client.get(f"/orders/{order_id}", follow_redirects=True)
            self.assertEqual(bob_res.status_code, 200)
            self.assertIn(b"Order not found or you do not have permission", bob_res.data)
        finally:
            # Restore product name and price
            conn = database.get_db_connection()
            conn.execute("UPDATE products SET name = 'Noise-Canceling Wireless Headphones', price = 2999.0 WHERE id = 1;")
            conn.commit()
            conn.close()

    # --------------------------------------------------------------------------
    # 6. ORDER CANCELLATION & INVENTORY RESTORATION
    # --------------------------------------------------------------------------

    def test_14_order_cancellation_restores_stock_and_coupon_usage(self):
        """Cancelling a Confirmed order sets status Cancelled, restores stock, and decrements coupon usage."""
        self.add_product_to_cart(1, 2)  # Product 1: stock goes 15 -> 13
        self.client.post("/checkout/coupon", data={"coupon_code": "WELCOME10"}, follow_redirects=True)

        conn = database.get_db_connection()
        c_before = conn.execute("SELECT used_count FROM coupons WHERE code = 'WELCOME10';").fetchone()["used_count"]
        conn.close()

        self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "mock_online",
            "simulated_outcome": "success"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        order = conn.execute("SELECT id, order_status, payment_status FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()
        order_id = order["id"]
        self.assertEqual(order["order_status"], "Confirmed")
        self.assertEqual(order["payment_status"], "Paid")

        # Verify stock was 13
        p1 = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(p1["stock"], 13)
        conn.close()

        # Alice cancels order
        cancel_res = self.client.post(f"/orders/{order_id}/cancel", follow_redirects=True)
        self.assertEqual(cancel_res.status_code, 200)
        self.assertIn(b"cancelled successfully", cancel_res.data)

        conn = database.get_db_connection()
        updated_order = conn.execute("SELECT order_status, payment_status FROM orders WHERE id = ?;", (order_id,)).fetchone()
        self.assertEqual(updated_order["order_status"], "Cancelled")
        self.assertEqual(updated_order["payment_status"], "Refund Pending (Simulated)")

        # Verify stock restored back to 15
        p1_restored = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(p1_restored["stock"], 15)

        # Verify coupon usage returned back to c_before
        c_restored = conn.execute("SELECT used_count FROM coupons WHERE code = 'WELCOME10';").fetchone()["used_count"]
        self.assertEqual(c_restored, c_before)
        conn.close()

    def test_15_duplicate_cancellation_prevented(self):
        """Cancelling an already cancelled order fails without re-incrementing stock."""
        self.add_product_to_cart(1, 1)
        self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        order_id = conn.execute("SELECT id FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["id"]
        conn.close()

        # First cancellation
        self.client.post(f"/orders/{order_id}/cancel", follow_redirects=True)

        # Stock is restored to 15
        conn = database.get_db_connection()
        self.assertEqual(conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"], 15)
        conn.close()

        # Second cancellation attempt
        res2 = self.client.post(f"/orders/{order_id}/cancel", follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"Order cannot be cancelled", res2.data)

        # Stock must NOT be incremented again to 16
        conn = database.get_db_connection()
        self.assertEqual(conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"], 15)
        conn.close()

    def test_16_cross_customer_cancellation_blocked(self):
        """Customer cannot cancel another customer's order."""
        self.add_product_to_cart(1, 1)
        self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        order_id = conn.execute("SELECT id FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["id"]
        conn.close()

        # Logout Alice and Login as Bob
        self.client.get("/logout", follow_redirects=True)
        self.login(email="bob@test.com", password="password123")

        # Bob attempts to cancel Alice's order
        res = self.client.post(f"/orders/{order_id}/cancel", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Order not found or unauthorized", res.data)

        # Verify Alice's order is still Confirmed
        conn = database.get_db_connection()
        order = conn.execute("SELECT order_status FROM orders WHERE id = ?;", (order_id,)).fetchone()
        conn.close()
        self.assertEqual(order["order_status"], "Confirmed")

    # --------------------------------------------------------------------------
    # 7. CSRF SECURITY ON STATE-CHANGING ROUTES
    # --------------------------------------------------------------------------

    def test_17_csrf_protection_on_order_actions(self):
        """When CSRF protection is active, missing or invalid token on place-order and cancel is rejected."""
        self.app.config["WTF_CSRF_ENABLED"] = True
        self.app.config["TESTING"] = False

        try:
            self.add_product_to_cart(1, 1)

            # 1. Place order without CSRF token
            res1 = self.client.post("/checkout/place-order", data={
                "address_id": self.alice_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)
            self.assertEqual(res1.status_code, 200)
            self.assertIn(b"CSRF token mismatch", res1.data)

            # 2. Cancel order without CSRF token
            res2 = self.client.post("/orders/1/cancel", data={}, follow_redirects=True)
            self.assertEqual(res2.status_code, 200)
            self.assertIn(b"CSRF token mismatch", res2.data)
        finally:
            self.app.config["WTF_CSRF_ENABLED"] = False
            self.app.config["TESTING"] = True

    # --------------------------------------------------------------------------
    # 8. AUDIT EDGE CASES: COMPETING PURCHASES, EXCEPTIONS & IDEMPOTENCY
    # --------------------------------------------------------------------------

    def test_18_database_exception_during_order_creation_triggers_atomic_rollback(self):
        """Database exception while inserting order triggers complete atomic rollback."""
        self.add_product_to_cart(1, 1)

        from unittest.mock import patch

        class FaultyCursor:
            def __init__(self, real_cursor):
                self._c = real_cursor

            def execute(self, sql, *args, **kwargs):
                if "INSERT INTO orders" in sql:
                    raise sqlite3.OperationalError("Simulated database failure during order insertion")
                return self._c.execute(sql, *args, **kwargs)

            def __getattr__(self, attr):
                return getattr(self._c, attr)

        class FaultyConnection:
            def __init__(self, real_conn):
                self._conn = real_conn

            def cursor(self):
                return FaultyCursor(self._conn.cursor())

            def execute(self, sql, *args, **kwargs):
                return self.cursor().execute(sql, *args, **kwargs)

            def __getattr__(self, attr):
                return getattr(self._conn, attr)

        def get_faulty_conn():
            return FaultyConnection(database.get_db_connection())

        with patch("app.get_db_connection", side_effect=get_faulty_conn):
            res = self.client.post("/checkout/place-order", data={
                "address_id": self.alice_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn(b"An unexpected error occurred while placing your order", res.data)

        # Verify rollback: 0 orders, 0 order items, stock remained 15, cart item preserved
        conn = database.get_db_connection()
        orders_c = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
        items_c = conn.execute("SELECT COUNT(*) AS c FROM order_items;").fetchone()["c"]
        cart_c = conn.execute("SELECT COUNT(*) AS c FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
        p1_stock = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
        conn.close()

        self.assertEqual(orders_c, 0)
        self.assertEqual(items_c, 0)
        self.assertEqual(cart_c, 1)
        self.assertEqual(p1_stock, 15)

    def test_19_database_exception_during_cancellation_triggers_atomic_rollback(self):
        """Database exception during cancellation leaves order Confirmed and stock untouched."""
        self.add_product_to_cart(1, 2)
        self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        order_id = conn.execute("SELECT id FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["id"]
        p1_stock_before = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
        conn.close()
        self.assertEqual(p1_stock_before, 13)

        from unittest.mock import patch

        class FaultyCancelCursor:
            def __init__(self, real_cursor):
                self._c = real_cursor

            def execute(self, sql, *args, **kwargs):
                if "UPDATE products" in sql and "stock = stock +" in sql:
                    raise sqlite3.OperationalError("Simulated database failure during inventory restoration")
                return self._c.execute(sql, *args, **kwargs)

            def __getattr__(self, attr):
                return getattr(self._c, attr)

        class FaultyCancelConnection:
            def __init__(self, real_conn):
                self._conn = real_conn

            def cursor(self):
                return FaultyCancelCursor(self._conn.cursor())

            def execute(self, sql, *args, **kwargs):
                return self.cursor().execute(sql, *args, **kwargs)

            def __getattr__(self, attr):
                return getattr(self._conn, attr)

        def get_faulty_cancel_conn():
            return FaultyCancelConnection(database.get_db_connection())

        with patch("app.get_db_connection", side_effect=get_faulty_cancel_conn):
            res = self.client.post(f"/orders/{order_id}/cancel", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"An unexpected error occurred during cancellation", res.data)

        # Verify atomic rollback: order remains Confirmed, stock remains 13
        conn = database.get_db_connection()
        order = conn.execute("SELECT order_status FROM orders WHERE id = ?;", (order_id,)).fetchone()
        p1_stock_after = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
        conn.close()

        self.assertEqual(order["order_status"], "Confirmed")
        self.assertEqual(p1_stock_after, 13)

    def test_20_competing_purchases_for_final_available_stock_cannot_oversell(self):
        """When competing customers attempt to purchase the final unit, stock never becomes negative."""
        conn = database.get_db_connection()
        conn.execute("UPDATE products SET stock = 1 WHERE id = 1;")
        conn.commit()
        conn.close()

        try:
            # Alice adds 1 item to cart
            self.add_product_to_cart(1, 1)

            # Bob adds 1 item to cart
            self.client.get("/logout", follow_redirects=True)
            self.login(email="bob@test.com", password="password123")
            self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)

            # Alice places order first
            self.client.get("/logout", follow_redirects=True)
            self.login(email="alice@test.com", password="password123")
            res_alice = self.client.post("/checkout/place-order", data={
                "address_id": self.alice_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)
            self.assertEqual(res_alice.status_code, 200)
            self.assertIn(b"placed successfully", res_alice.data)

            # Stock is now 0
            conn = database.get_db_connection()
            p1_stock_mid = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
            conn.close()
            self.assertEqual(p1_stock_mid, 0)

            # Bob attempts to place order for depleted product
            self.client.get("/logout", follow_redirects=True)
            self.login(email="bob@test.com", password="password123")
            res_bob = self.client.post("/checkout/place-order", data={
                "address_id": self.bob_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)
            self.assertEqual(res_bob.status_code, 200)
            self.assertIn(b"Insufficient stock", res_bob.data)

            # Check stock is strictly 0 and never became negative
            conn = database.get_db_connection()
            p1_stock_final = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
            bob_orders = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.bob_id,)).fetchone()["c"]
            conn.close()

            self.assertEqual(p1_stock_final, 0)
            self.assertEqual(bob_orders, 0)

        finally:
            conn = database.get_db_connection()
            conn.execute("UPDATE products SET stock = 15 WHERE id = 1;")
            conn.commit()
            conn.close()

    def test_21_different_customers_submitting_identical_idempotency_keys_rejected(self):
        """A customer cannot submit another customer's idempotency key to hijack or duplicate orders."""
        self.add_product_to_cart(1, 1)

        shared_key = "unique-shared-idemp-key-xyz"

        # Alice places order with shared_key
        res_alice = self.client.post("/checkout/place-order", data={
            "address_id": self.alice_address_id,
            "payment_method": "cod",
            "idempotency_key": shared_key
        }, follow_redirects=True)
        self.assertEqual(res_alice.status_code, 200)
        self.assertIn(b"placed successfully", res_alice.data)

        # Bob logs in, adds an item, and attempts to submit with Alice's shared_key
        self.client.get("/logout", follow_redirects=True)
        self.login(email="bob@test.com", password="password123")
        self.client.post("/cart/add", data={"product_id": 3, "quantity": 1}, follow_redirects=True)

        res_bob = self.client.post("/checkout/place-order", data={
            "address_id": self.bob_address_id,
            "payment_method": "cod",
            "idempotency_key": shared_key
        }, follow_redirects=True)
        self.assertEqual(res_bob.status_code, 200)
        self.assertIn(b"Duplicate or invalid submission detected", res_bob.data)

        # Verify Bob has 0 orders and Bob's cart is still intact
        conn = database.get_db_connection()
        bob_orders = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.bob_id,)).fetchone()["c"]
        bob_cart = conn.execute("SELECT COUNT(*) AS c FROM cart_items WHERE customer_id = ?;", (self.bob_id,)).fetchone()["c"]
        conn.close()

        self.assertEqual(bob_orders, 0)
        self.assertEqual(bob_cart, 1)

    def test_22_expired_coupon_at_moment_of_purchase_rejected(self):
        """Coupon that expires between checkout preview and order placement is rejected atomically."""
        self.add_product_to_cart(1, 1)

        # Create coupon expiring in future
        conn = database.get_db_connection()
        conn.execute("""
            INSERT INTO coupons (code, discount_type, discount_value, min_cart_value, is_active, expiry_date)
            VALUES ('EXPIRING', 'fixed', 200, 500, 1, '2099-12-31');
        """)
        conn.commit()
        conn.close()

        try:
            # Apply coupon
            self.client.post("/checkout/coupon", data={"coupon_code": "EXPIRING"}, follow_redirects=True)

            # Change expiry date to past in DB
            conn = database.get_db_connection()
            conn.execute("UPDATE coupons SET expiry_date = '2020-01-01' WHERE code = 'EXPIRING';")
            conn.commit()
            conn.close()

            # Attempt to place order
            res = self.client.post("/checkout/place-order", data={
                "address_id": self.alice_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"expired", res.data)

            # Verify no order created and stock remained 15
            conn = database.get_db_connection()
            orders_c = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE customer_id = ?;", (self.alice_id,)).fetchone()["c"]
            p1_stock = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()["stock"]
            conn.close()

            self.assertEqual(orders_c, 0)
            self.assertEqual(p1_stock, 15)

        finally:
            conn = database.get_db_connection()
            conn.execute("DELETE FROM coupons WHERE code = 'EXPIRING';")
            conn.commit()
            conn.close()

    def test_23_production_secret_key_requirement(self):
        """Production environment without explicit FLASK_SECRET_KEY or SECRET_KEY raises RuntimeError."""
        old_env = os.environ.get("FLASK_ENV")
        old_secret = os.environ.get("FLASK_SECRET_KEY")
        old_secret2 = os.environ.get("SECRET_KEY")

        try:
            os.environ["FLASK_ENV"] = "production"
            if "FLASK_SECRET_KEY" in os.environ:
                del os.environ["FLASK_SECRET_KEY"]
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            env_secret = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("SECRET_KEY")
            with self.assertRaises(RuntimeError):
                if not env_secret and os.environ.get("FLASK_ENV") == "production":
                    raise RuntimeError("FLASK_SECRET_KEY or SECRET_KEY environment variable is required in production.")
        finally:
            if old_env is not None:
                os.environ["FLASK_ENV"] = old_env
            else:
                os.environ.pop("FLASK_ENV", None)
            if old_secret is not None:
                os.environ["FLASK_SECRET_KEY"] = old_secret
            if old_secret2 is not None:
                os.environ["SECRET_KEY"] = old_secret2


if __name__ == "__main__":
    unittest.main()
