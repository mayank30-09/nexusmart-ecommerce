"""
tests/test_cart.py - Module 3: Cart Management Test Suite.
Covers:
  - Add to cart (new items, existing item increment, non-existent products)
  - Stock boundary enforcement (rejecting quantities exceeding inventory)
  - Quantity updates and input validation
  - Single item removal and complete cart clearing
  - Arithmetic precision for Item Subtotal (price * qty) and Cart Grand Total (sum of subtotals)
  - Empty cart state handling
  - Authentication enforcement on all cart mutation and viewing routes
  - Multi-tenant customer cart isolation (preventing cross-customer viewing, updating, or deletion)
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


class TestCartManagement(BaseTestCase, unittest.TestCase):
    """Test suite for Module 3: Cart Management."""

    def setUp(self):
        super().setUp()
        # Create and log in Primary Shopper
        self.register(name="Alice Shopper", email="alice@test.com", password="password123", confirm="password123")
        self.login(email="alice@test.com", password="password123")

    def test_01_add_product_to_cart(self):
        """BB-CART-01 / WB: Adding product creates row in cart and redirects with success flash."""
        # Product 1: Noise-Canceling Wireless Headphones (Price: 2999, Stock: 15)
        res = self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Added 2 x &#39;Noise-Canceling Wireless Headphones&#39;", res.data)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)

        # Verify in SQLite database
        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        row = conn.execute("SELECT * FROM cart_items WHERE customer_id = ? AND product_id = 1;", (customer["id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["quantity"], 2)

    def test_02_add_same_product_again_increments_quantity(self):
        """BB-CART-02 / WB: Adding same product increments quantity on existing record without duplicate row."""
        # Add 2 items first
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
        # Add 3 more of same product
        res = self.client.post("/cart/add", data={"product_id": 1, "quantity": 3}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        rows = conn.execute("SELECT * FROM cart_items WHERE customer_id = ? AND product_id = 1;", (customer["id"],)).fetchall()
        conn.close()

        # Exactly 1 row with quantity = 5
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 5)

    def test_03_update_quantity_valid(self):
        """BB-CART-03 / WB: Updating quantity modifies cart record accurately."""
        self.client.post("/cart/add", data={"product_id": 3, "quantity": 1}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res = self.client.post(f"/cart/update/{item['id']}", data={"quantity": 4}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Updated quantity", res.data)

        conn = database.get_db_connection()
        updated = conn.execute("SELECT quantity FROM cart_items WHERE id = ?;", (item["id"],)).fetchone()
        conn.close()
        self.assertEqual(updated["quantity"], 4)

    def test_04_remove_product(self):
        """BB-CART-04 / WB: Removing item deletes record from customer cart."""
        self.client.post("/cart/add", data={"product_id": 4, "quantity": 1}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res = self.client.post(f"/cart/remove/{item['id']}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Removed", res.data)

        # Verify DB is now empty for this customer
        conn = database.get_db_connection()
        count = conn.execute("SELECT COUNT(*) AS cnt FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()["cnt"]
        conn.close()
        self.assertEqual(count, 0)

    def test_05_clear_cart(self):
        """BB-CART-05 / WB: Clearing cart deletes all items belonging to current customer."""
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)
        self.client.post("/cart/add", data={"product_id": 2, "quantity": 1}, follow_redirects=True)

        res = self.client.post("/cart/clear", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your shopping cart has been cleared", res.data)
        self.assertIn(b"Your Cart is Currently Empty", res.data)

    def test_06_quantity_greater_than_available_stock_on_add(self):
        """BB-CART-06 / WB: Adding quantity exceeding inventory is rejected with boundary notice."""
        # Product 8: Minimalist Stainless Steel Wristwatch has stock = 12
        conn = database.get_db_connection()
        prod = conn.execute("SELECT stock FROM products WHERE id = 8;").fetchone()
        conn.close()
        available_stock = prod["stock"]

        # Attempt to add stock + 10 units
        res = self.client.post("/cart/add", data={"product_id": 8, "quantity": available_stock + 10}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"in stock", res.data)
        self.assertIn(b"Cannot add", res.data)

        # Verify nothing was added
        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        item = conn.execute("SELECT * FROM cart_items WHERE customer_id = ? AND product_id = 8;", (customer["id"],)).fetchone()
        conn.close()
        self.assertIsNone(item)

    def test_07_quantity_greater_than_available_stock_on_update(self):
        """BB-CART-07 / WB: Updating quantity beyond available stock is rejected."""
        self.client.post("/cart/add", data={"product_id": 8, "quantity": 2}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        # Update to 99 (stock is 12)
        res = self.client.post(f"/cart/update/{item['id']}", data={"quantity": 99}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cannot set quantity", res.data)
        self.assertIn(b"available in stock", res.data)

    def test_08_correct_item_subtotal(self):
        """BB-CART-08 / WB: Item Subtotal = Unit Price * Quantity is strictly verified."""
        # Product 3: Classic Cotton Crewneck T-Shirt (Price: 499.00)
        # 3 units -> Subtotal = 1497.00
        self.client.post("/cart/add", data={"product_id": 3, "quantity": 3}, follow_redirects=True)
        res = self.client.get("/cart")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"1497.00", res.data)

    def test_09_correct_cart_total(self):
        """BB-CART-09 / WB: Grand Cart Total = Sum of all item subtotals."""
        # Product 3: 499.00 * 2 = 998.00
        # Product 9: 1199.00 * 1 = 1199.00
        # Grand Total = 2197.00
        self.client.post("/cart/add", data={"product_id": 3, "quantity": 2}, follow_redirects=True)
        self.client.post("/cart/add", data={"product_id": 9, "quantity": 1}, follow_redirects=True)

        res = self.client.get("/cart")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"2197.00", res.data)

    def test_10_empty_cart_display(self):
        """BB-CART-10 / WB: Empty cart view displays friendly state and browse link."""
        res = self.client.get("/cart")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your Cart is Currently Empty", res.data)
        self.assertIn(b"Explore Products Now", res.data)

    def test_11_access_cart_without_login(self):
        """BB-CART-11 / WB: Unauthenticated requests to /cart and mutation routes are blocked."""
        # Log out
        self.client.get("/logout", follow_redirects=True)

        # GET /cart
        res_get = self.client.get("/cart", follow_redirects=True)
        self.assertIn(b"Please login to access this page", res_get.data)

        # POST /cart/add
        res_add = self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)
        self.assertIn(b"Please login to access this page", res_add.data)

        # POST /cart/update/1
        res_update = self.client.post("/cart/update/1", data={"quantity": 2}, follow_redirects=True)
        self.assertIn(b"Please login to access this page", res_update.data)

        # POST /cart/remove/1
        res_remove = self.client.post("/cart/remove/1", follow_redirects=True)
        self.assertIn(b"Please login to access this page", res_remove.data)

        # POST /cart/clear
        res_clear = self.client.post("/cart/clear", follow_redirects=True)
        self.assertIn(b"Please login to access this page", res_clear.data)

    def test_12_customer_isolation_and_cross_access_prevention(self):
        """BB-CART-12 / WB: Customers cannot view, modify, or delete another customer's cart items."""
        # 1. Alice adds Product 1
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)

        conn = database.get_db_connection()
        alice = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        alice_cart_item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (alice["id"],)).fetchone()
        conn.close()

        # Alice logs out
        self.client.get("/logout", follow_redirects=True)

        # 2. Bob registers and logs in
        self.register(name="Bob Shopper", email="bob@test.com", password="password123", confirm="password123")
        self.login(email="bob@test.com", password="password123")

        # Bob views cart -> Must be empty (Alice's items hidden)
        res_bob_cart = self.client.get("/cart")
        self.assertIn(b"Your Cart is Currently Empty", res_bob_cart.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res_bob_cart.data)

        # Bob attempts to update Alice's cart item -> Blocked
        res_hack_update = self.client.post(f"/cart/update/{alice_cart_item['id']}", data={"quantity": 10}, follow_redirects=True)
        self.assertIn(b"Cart item not found", res_hack_update.data)

        # Bob attempts to remove Alice's cart item -> Blocked
        res_hack_remove = self.client.post(f"/cart/remove/{alice_cart_item['id']}", follow_redirects=True)
        self.assertIn(b"Item could not be found in your cart", res_hack_remove.data)

        # Verify Alice's cart item remains unmodified in SQLite
        conn = database.get_db_connection()
        check_item = conn.execute("SELECT quantity FROM cart_items WHERE id = ?;", (alice_cart_item["id"],)).fetchone()
        conn.close()
        self.assertEqual(check_item["quantity"], 2)

    def test_13_invalid_cart_inputs(self):
        """BB-CART-13 / WB: Invalid quantity or missing product handles validation gracefully."""
        # Add non-existent product
        res1 = self.client.post("/cart/add", data={"product_id": 99999, "quantity": 1}, follow_redirects=True)
        self.assertIn(b"Product not found", res1.data)

        # Add negative quantity
        res2 = self.client.post("/cart/add", data={"product_id": 1, "quantity": -5}, follow_redirects=True)
        self.assertIn(b"Please select a quantity greater than zero", res2.data)

        # Add non-numeric quantity
        res3 = self.client.post("/cart/add", data={"product_id": 1, "quantity": "invalid_num"}, follow_redirects=True)
        self.assertIn(b"Invalid product or quantity specified", res3.data)

    def test_14_cart_count_context_processor(self):
        """BB-CART-14 / WB: inject_cart_count correctly tallies total items across header badge."""
        # Add 2 of product 1 and 3 of product 2 -> Total cart count = 5
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
        self.client.post("/cart/add", data={"product_id": 2, "quantity": 3}, follow_redirects=True)

        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        # Check badge rendering
        self.assertIn(b"cart-badge", res.data)
        self.assertIn(b"5", res.data)

    def test_15_update_quantity_zero_or_negative(self):
        """WB: Updating cart item quantity with 0 or negative number triggers warning."""
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res_zero = self.client.post(f"/cart/update/{item['id']}", data={"quantity": "0"}, follow_redirects=True)
        self.assertIn(b"Quantity must be at least 1", res_zero.data)

        res_neg = self.client.post(f"/cart/update/{item['id']}", data={"quantity": "-2"}, follow_redirects=True)
        self.assertIn(b"Quantity must be at least 1", res_neg.data)

    def test_16_update_quantity_non_numeric(self):
        """WB: Updating cart item quantity with non-numeric value triggers validation error."""
        self.client.post("/cart/add", data={"product_id": 1, "quantity": 1}, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        item = conn.execute("SELECT id FROM cart_items WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res = self.client.post(f"/cart/update/{item['id']}", data={"quantity": "abc"}, follow_redirects=True)
        self.assertIn(b"Invalid quantity value", res.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
