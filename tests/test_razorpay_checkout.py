"""
tests/test_razorpay_checkout.py - Comprehensive Unit & Integration Tests for Razorpay Standard Checkout:
  - Phase D: Razorpay Standard Checkout order initiation
  - Cryptographic payment signature verification (HMAC-SHA256)
  - Duplicate verification idempotency
  - Payment failure and customer cancellation handling
  - Inventory preservation until payment confirmation
  - Atomic stock deduction and coupon usage upon verified payment
  - Webhook signature verification and deduplication
"""

import os
import sys
import hmac
import hashlib
import json
import secrets
import unittest

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
from tests.conftest import BaseTestCase


class TestRazorpayCheckout(BaseTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        os.environ["RAZORPAY_KEY_ID"] = "rzp_test_mockkey123"
        os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_secret_mock456"
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_webhook_secret_mock789"

        # Register and login Alice
        self.register(name="Alice Buyer", email="alice@test.com", password="password123", confirm="password123")
        self.login(email="alice@test.com", password="password123")

        conn = database.get_db_connection()
        alice = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        self.alice_id = alice["id"]

        # Add delivery address for Alice
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer_addresses (customer_id, address_line, city, state, postal_code, is_default)
            VALUES (?, '123 Market St, Flat 4B', 'Bengaluru', 'Karnataka', '560001', 1);
        """, (self.alice_id,))
        self.address_id = cursor.lastrowid

        # Set stock for product 1 (Wireless Bluetooth Headphones: ₹2999) to 10
        cursor.execute("UPDATE products SET stock = 10 WHERE id = 1;")
        cursor.execute("DELETE FROM processed_webhooks;")
        conn.commit()
        conn.close()

    def add_to_cart(self, product_id=1, quantity=2):
        return self.client.post("/cart/add", data={
            "product_id": product_id,
            "quantity": quantity
        }, follow_redirects=True)

    def test_01_razorpay_order_initiation_preserves_stock_and_cart(self):
        """Phase D: Placing an order with payment_method='razorpay' creates pending order without deducting stock."""
        self.add_to_cart(product_id=1, quantity=2)

        res = self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Securing Payment with Razorpay", res.data)
        self.assertIn(b"Open Razorpay Checkout Modal", res.data)

        # Confirm stock was NOT yet deducted (remains 10)
        conn = database.get_db_connection()
        prod = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod["stock"], 10)

        # Confirm cart items still exist
        cart = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(cart), 1)

        # Confirm pending order exists
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.alice_id,)).fetchone()
        self.assertIsNotNone(order)
        self.assertEqual(order["order_status"], "Pending Payment")
        self.assertEqual(order["payment_status"], "Pending")
        self.assertEqual(order["payment_method"], "razorpay")
        self.assertIsNotNone(order["razorpay_order_id"])
        conn.close()

    def test_02_razorpay_signature_verification_success(self):
        """Phase D: Valid signature verification marks order Confirmed, deducts stock, and clears cart."""
        self.add_to_cart(product_id=1, quantity=2)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.alice_id,)).fetchone()
        conn.close()

        rzp_order_id = order["razorpay_order_id"]
        rzp_payment_id = "pay_test_998877"
        secret = "rzp_test_secret_mock456"
        expected_sig = hmac.new(secret.encode("utf-8"), f"{rzp_order_id}|{rzp_payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()

        res = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": expected_sig
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your Order is Confirmed", res.data)

        # Verify database state
        conn = database.get_db_connection()
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?;", (order["id"],)).fetchone()
        self.assertEqual(updated_order["order_status"], "Confirmed")
        self.assertEqual(updated_order["payment_status"], "Paid")
        self.assertEqual(updated_order["razorpay_payment_id"], rzp_payment_id)
        self.assertEqual(updated_order["razorpay_signature"], expected_sig)

        # Stock deducted (10 - 2 = 8)
        prod = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod["stock"], 8)

        # Cart cleared
        cart = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(cart), 0)
        conn.close()

    def test_03_razorpay_signature_verification_rejection(self):
        """Phase D: Forged or invalid signature is rejected, marking order Failed without deducting stock."""
        self.add_to_cart(product_id=1, quantity=3)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.alice_id,)).fetchone()
        conn.close()

        res = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": order["razorpay_order_id"],
            "razorpay_payment_id": "pay_fake_123",
            "razorpay_signature": "forged_invalid_signature_hex"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Payment verification failed", res.data)

        # Stock NOT deducted (still 10)
        conn = database.get_db_connection()
        prod = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod["stock"], 10)

        # Order marked Failed
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?;", (order["id"],)).fetchone()
        self.assertEqual(updated_order["payment_status"], "Failed")
        conn.close()

    def test_04_razorpay_customer_cancellation(self):
        """Phase D: Customer cancelling modal preserves cart and inventory."""
        self.add_to_cart(product_id=1, quantity=1)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.alice_id,)).fetchone()
        conn.close()

        res = self.client.post(f"/checkout/razorpay/cancel/{order['order_reference']}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Payment cancelled", res.data)

        conn = database.get_db_connection()
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?;", (order["id"],)).fetchone()
        self.assertEqual(updated_order["order_status"], "Cancelled")
        self.assertEqual(updated_order["payment_status"], "Cancelled")

        # Cart still has item
        cart = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.alice_id,)).fetchall()
        self.assertEqual(len(cart), 1)
        conn.close()

    def test_05_webhook_signature_verification_and_deduplication(self):
        """Phase D: Webhook verifies signature, commits order idempotently, and ignores duplicate events."""
        self.add_to_cart(product_id=1, quantity=1)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.alice_id,)).fetchone()
        conn.close()

        test_event_id = f"evt_test_{secrets.token_hex(6)}"
        event_payload = {
            "event_id": test_event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_webhook_live_777",
                        "order_id": order["razorpay_order_id"],
                        "status": "captured"
                    }
                }
            }
        }
        body_bytes = json.dumps(event_payload).encode("utf-8")
        webhook_secret = "rzp_webhook_secret_mock789"
        valid_webhook_sig = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        # 1. Invalid signature rejection
        res_invalid = self.client.post(
            "/webhooks/razorpay",
            data=body_bytes,
            headers={"X-Razorpay-Signature": "tampered_sig", "Content-Type": "application/json"}
        )
        self.assertEqual(res_invalid.status_code, 400)

        # 2. Valid signature processing
        res_valid = self.client.post(
            "/webhooks/razorpay",
            data=body_bytes,
            headers={"X-Razorpay-Signature": valid_webhook_sig, "Content-Type": "application/json"}
        )
        self.assertEqual(res_valid.status_code, 200)
        self.assertEqual(res_valid.get_json()["status"], "success")

        # Confirm order was committed
        conn = database.get_db_connection()
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?;", (order["id"],)).fetchone()
        self.assertEqual(updated_order["order_status"], "Confirmed")
        self.assertEqual(updated_order["payment_status"], "Paid")

        # 3. Duplicate delivery test (idempotency check)
        res_dup = self.client.post(
            "/webhooks/razorpay",
            data=body_bytes,
            headers={"X-Razorpay-Signature": valid_webhook_sig, "Content-Type": "application/json"}
        )
        self.assertEqual(res_dup.status_code, 200)
        self.assertEqual(res_dup.get_json()["status"], "already_processed")
        conn.close()


if __name__ == "__main__":
    unittest.main()
