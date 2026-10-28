"""
tests/test_admin_and_recommendations.py - Automated Unit & Integration Tests for:
  - FR-16: AI-Based Product Recommendations (Activity-based, Context-based, Cold-start)
  - FR-17: Administrator Product Management (Add, Edit, Delete products)
  - FR-18: Inventory / Stock Control (Stock adjustment, Low stock alerts)
  - FR-19: Discount & Coupon Management (Create promo code, Toggle availability)
  - FR-20: Administrator Order Management (View all orders, Update fulfillment status)
  - BR-04: Strict enforcement preventing order cancellation after shipping
"""

import os
import sys
import unittest

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app
from tests.conftest import BaseTestCase


class TestAdminAndRecommendations(BaseTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        conn = database.get_db_connection()
        cursor = conn.cursor()

        # Seed or ensure admin account exists
        admin_row = conn.execute("SELECT id FROM customers WHERE email = 'admin@nexusmart.com';").fetchone()
        if not admin_row:
            from werkzeug.security import generate_password_hash
            cursor.execute("""
                INSERT INTO customers (name, email, password_hash, is_admin)
                VALUES ('Nexus Administrator', 'admin@nexusmart.com', ?, 1);
            """, (generate_password_hash("AdminPass123!"),))

        # Register regular test user Bob
        self.register(name="Bob Regular", email="bob@test.com", password="password123", confirm="password123")
        bob_row = conn.execute("SELECT id FROM customers WHERE email = 'bob@test.com';").fetchone()
        self.bob_id = bob_row["id"]

        # Ensure Bob has an address
        cursor.execute("""
            INSERT INTO customer_addresses (customer_id, address_line, city, state, postal_code, is_default)
            VALUES (?, '456 Tech Park', 'Pune', 'Maharashtra', '411001', 1);
        """, (self.bob_id,))
        self.bob_address_id = cursor.lastrowid

        conn.commit()
        conn.close()

    def login_admin(self):
        """Helper to log in as administrator."""
        return self.client.post("/admin/login", data={
            "email": "admin@nexusmart.com",
            "password": "AdminPass123!"
        }, follow_redirects=True)

    # --------------------------------------------------------------------------
    # ADMIN AUTHENTICATION & ACCESS CONTROL
    # --------------------------------------------------------------------------

    def test_01_admin_login_success(self):
        """Test Case 1: Authorized administrator login succeeds and grants access."""
        res = self.login_admin()
        self.assertEqual(res.status_code, 200)
        self.assertIn("Welcome to the NexusMart Admin Portal", res.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get("is_admin"))
            self.assertEqual(sess.get("customer_email"), "admin@nexusmart.com")

    def test_02_admin_login_wrong_password(self):
        """Test Case 2: Administrator login with incorrect password is rejected."""
        res = self.client.post("/admin/login", data={
            "email": "admin@nexusmart.com",
            "password": "WrongPassword!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Invalid administrator credentials", res.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("is_admin", False))

    def test_03_admin_login_non_admin_forbidden(self):
        """Test Case 3: Regular customer credentials on /admin/login are denied with 403."""
        res = self.client.post("/admin/login", data={
            "email": "bob@test.com",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 403)
        self.assertIn("does not possess administrator credentials", res.get_data(as_text=True))

    def test_04_admin_route_protection_unauthenticated(self):
        """Test Case 4: Unauthenticated access to admin routes redirects to admin login."""
        self.client.get("/logout", follow_redirects=True)
        with self.client.session_transaction() as sess:
            sess.clear()
        for endpoint in ["/admin/dashboard", "/admin/products", "/admin/orders", "/admin/coupons"]:
            res = self.client.get(endpoint)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/admin/login", res.headers.get("Location", ""))

    def test_05_admin_route_protection_regular_customer(self):
        """Test Case 5: Authenticated regular customer accessing admin routes is denied with 403."""
        self.login("bob@test.com", "password123")
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 403)

    # --------------------------------------------------------------------------
    # FR-17: ADMIN PRODUCT MANAGEMENT
    # --------------------------------------------------------------------------

    def test_06_admin_product_add(self):
        """Test Case 6 (FR-17): Admin adds a new product to catalog."""
        self.login_admin()
        res = self.client.post("/admin/products/add", data={
            "name": "Noise Cancelling Earbuds Pro",
            "category": "Electronics",
            "price": "3499.00",
            "stock": "30",
            "description": "Premium wireless ANC earbuds with spatial audio."
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("added successfully to catalog", res.get_data(as_text=True))

        conn = database.get_db_connection()
        prod = conn.execute("SELECT * FROM products WHERE name = 'Noise Cancelling Earbuds Pro';").fetchone()
        self.assertIsNotNone(prod)
        self.assertEqual(prod["category"], "Electronics")
        self.assertEqual(float(prod["price"]), 3499.00)
        self.assertEqual(prod["stock"], 30)
        # Clean up so catalog seed data remains pristine for subsequent test suites
        conn.execute("DELETE FROM products WHERE id = ?;", (prod["id"],))
        conn.commit()
        conn.close()

    def test_07_admin_product_edit_and_delete(self):
        """Test Case 7 (FR-17): Admin updates product details and deletes item."""
        self.login_admin()
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, category, price, stock, description) VALUES ('Temporary Item To Delete', 'Accessories', 500.0, 10, 'Temp');")
        prod_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Update product
        res_edit = self.client.post(f"/admin/products/{prod_id}/edit", data={
            "name": "Updated Test Product",
            "category": "Accessories",
            "price": "899.00",
            "stock": "18",
            "description": "Updated description for test product."
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn("updated successfully", res_edit.get_data(as_text=True))

        # Delete product
        res_del = self.client.post(f"/admin/products/{prod_id}/delete", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertIn("removed from catalog", res_del.get_data(as_text=True))

        conn = database.get_db_connection()
        deleted = conn.execute("SELECT * FROM products WHERE id = ?;", (prod_id,)).fetchone()
        conn.close()
        self.assertIsNone(deleted)

    # --------------------------------------------------------------------------
    # FR-18: INVENTORY / STOCK CONTROL
    # --------------------------------------------------------------------------

    def test_08_admin_stock_update(self):
        """Test Case 8 (FR-18): Admin updates product inventory stock directly."""
        self.login_admin()
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, category, price, stock, description) VALUES ('Temporary Stock Item', 'Accessories', 250.0, 5, 'Temp');")
        prod_id = cursor.lastrowid
        conn.commit()
        conn.close()

        res = self.client.post(f"/admin/products/{prod_id}/stock", data={
            "stock": "45"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("updated to 45 units", res.get_data(as_text=True))

        conn = database.get_db_connection()
        updated_prod = conn.execute("SELECT stock FROM products WHERE id = ?;", (prod_id,)).fetchone()
        conn.execute("DELETE FROM products WHERE id = ?;", (prod_id,))
        conn.commit()
        conn.close()
        self.assertEqual(updated_prod["stock"], 45)

    # --------------------------------------------------------------------------
    # FR-20: ADMIN ORDER MANAGEMENT & BR-04 ENFORCEMENT
    # --------------------------------------------------------------------------

    def test_09_admin_order_status_and_br04_cancellation_lock(self):
        """Test Case 9 (FR-20, BR-04): Admin marks order as Shipped, and customer cancellation is blocked."""
        # 1. Create a dedicated temporary product so seed stock is never mutated
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, category, price, stock, description) VALUES ('Temporary BR04 Item', 'Accessories', 100.0, 10, 'Temp');")
        prod_id = cursor.lastrowid
        conn.commit()
        conn.close()

        try:
            # Bob places an order
            self.login("bob@test.com", "password123")
            self.client.post("/cart/add", data={"product_id": prod_id, "quantity": 1})
            res_place = self.client.post("/checkout/place-order", data={
                "address_id": self.bob_address_id,
                "payment_method": "cod"
            }, follow_redirects=True)
            self.assertEqual(res_place.status_code, 200)

            conn = database.get_db_connection()
            bob_order = conn.execute("SELECT id, order_status FROM orders WHERE customer_id = ? ORDER BY id DESC LIMIT 1;", (self.bob_id,)).fetchone()
            conn.close()
            self.assertIsNotNone(bob_order, f"Order placement failed: {res_place.get_data(as_text=True)}")
            order_id = bob_order["id"]
            self.assertEqual(bob_order["order_status"], "Confirmed")

            # 2. Admin logs in and updates status to 'Shipped' (FR-20)
            self.login_admin()
            res_status = self.client.post(f"/admin/orders/{order_id}/status", data={
                "order_status": "Shipped"
            }, follow_redirects=True)
            self.assertEqual(res_status.status_code, 200)
            self.assertIn("status updated to", res_status.get_data(as_text=True))
            self.assertIn("Shipped", res_status.get_data(as_text=True))

            # 3. Bob logs in and attempts to cancel the shipped order -> Blocked by BR-04
            self.client.get("/logout", follow_redirects=True)
            self.login("bob@test.com", "password123")
            res_cancel = self.client.post(f"/orders/{order_id}/cancel", follow_redirects=True)
            self.assertEqual(res_cancel.status_code, 200)
            self.assertIn("Order cancellation is not allowed. The order has already been shipped or delivered (BR-04)", res_cancel.get_data(as_text=True))

            # Confirm status remains Shipped
            conn = database.get_db_connection()
            final_order = conn.execute("SELECT order_status FROM orders WHERE id = ?;", (order_id,)).fetchone()
            conn.close()
            self.assertEqual(final_order["order_status"], "Shipped")
        finally:
            conn = database.get_db_connection()
            conn.execute("DELETE FROM order_items WHERE product_id = ?;", (prod_id,))
            conn.execute("DELETE FROM products WHERE id = ?;", (prod_id,))
            conn.commit()
            conn.close()

    # --------------------------------------------------------------------------
    # FR-19: DISCOUNT / COUPON MANAGEMENT
    # --------------------------------------------------------------------------

    def test_10_admin_coupon_creation_and_toggle(self):
        """Test Case 10 (FR-19): Admin creates and deactivates a promotional coupon code."""
        import secrets
        code = f"DISC_{secrets.token_hex(3).upper()}"
        self.login_admin()
        res_create = self.client.post("/admin/coupons/add", data={
            "code": code,
            "discount_type": "percentage",
            "discount_value": "40.0",
            "min_cart_value": "1500.0",
            "usage_limit": "50"
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn("created successfully", res_create.get_data(as_text=True))

        conn = database.get_db_connection()
        cpn = conn.execute("SELECT * FROM coupons WHERE code = ?;", (code,)).fetchone()
        self.assertIsNotNone(cpn)
        self.assertEqual(cpn["is_active"], 1)
        cpn_id = cpn["id"]
        conn.close()

        # Deactivate coupon
        res_toggle = self.client.post(f"/admin/coupons/{cpn_id}/toggle", follow_redirects=True)
        self.assertEqual(res_toggle.status_code, 200)
        self.assertIn("deactivated", res_toggle.get_data(as_text=True))

        conn = database.get_db_connection()
        toggled = conn.execute("SELECT is_active FROM coupons WHERE id = ?;", (cpn_id,)).fetchone()
        conn.close()
        self.assertEqual(toggled["is_active"], 0)

    # --------------------------------------------------------------------------
    # FR-16: AI PRODUCT RECOMMENDATIONS
    # --------------------------------------------------------------------------

    def test_11_ai_recommendations_cold_start(self):
        """Test Case 11 (FR-16): Cold start recommendations return available catalog products."""
        recs = flask_app.get_recommended_products(customer_id=None, limit=4)
        self.assertGreater(len(recs), 0)
        self.assertLessEqual(len(recs), 4)
        for r in recs:
            self.assertIn("name", r)
            self.assertIn("price", r)
            self.assertGreater(r["stock"], 0)

    def test_12_ai_recommendations_context_based(self):
        """Test Case 12 (FR-16): Context-based recommendations match category and exclude current product."""
        conn = database.get_db_connection()
        prod = conn.execute("SELECT id, category FROM products WHERE category = 'Electronics' LIMIT 1;").fetchone()
        conn.close()
        prod_id = prod["id"]

        recs = flask_app.get_recommended_products(current_product_id=prod_id, limit=4)
        self.assertGreater(len(recs), 0)
        rec_ids = [r["id"] for r in recs]
        self.assertNotIn(prod_id, rec_ids)

    def test_13_ai_recommendations_activity_based(self):
        """Test Case 13 (FR-16): Recommendations prioritize categories customer previously purchased."""
        # Alice buys an item in Bags category
        conn = database.get_db_connection()
        bag = conn.execute("SELECT id FROM products WHERE category = 'Bags' LIMIT 1;").fetchone()
        if bag:
            bag_id = bag["id"]
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (order_reference, customer_id, shipping_address_line, shipping_city, shipping_state, shipping_postal_code, subtotal, discount_amount, final_total, order_status, payment_status, payment_method)
                VALUES ('TEST-BAG-ORDER', ?, '123 St', 'City', 'State', '123456', 999.0, 0.0, 999.0, 'Confirmed', 'Paid', 'Razorpay');
            """, (self.bob_id,))
            order_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity, line_total)
                VALUES (?, ?, 'Test Duffel Bag', 999.0, 1, 999.0);
            """, (order_id, bag_id))
            conn.commit()
        conn.close()

        recs = flask_app.get_recommended_products(customer_id=self.bob_id, limit=3)
        self.assertGreater(len(recs), 0)
        # Should contain at least one item from Bags category
        categories = [r["category"] for r in recs]
        self.assertIn("Bags", categories)


if __name__ == "__main__":
    unittest.main()
