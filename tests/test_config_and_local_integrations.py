"""
tests/test_config_and_local_integrations.py - Comprehensive Unit & Integration Tests for:
  - Configuration loading, secret exclusion, and safe diagnostic endpoint
  - Google OAuth localhost flow, initiation parameters, CSRF state, and error handling
  - Razorpay Test Mode order creation, HMAC-SHA256 signature verification,
    order ID validation, cart preservation, idempotency, and webhook security
"""

import os
import sys
import hmac
import hashlib
import json
import secrets
import unittest
from unittest.mock import patch, MagicMock

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ecommerce_practical10")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import database
import app as flask_app
from tests.conftest import BaseTestCase


class TestConfigurationAndDiagnostics(BaseTestCase, unittest.TestCase):
    """Automated tests for environment configuration and non-sensitive diagnostics."""

    def test_01_config_diagnostics_endpoint_structure_and_no_secret_leaks(self):
        """Phase 6: Diagnostic endpoint returns 200, reports boolean flags, and never leaks secrets."""
        res = self.client.get("/healthz/config")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Check required fields
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("environment", data)
        self.assertIn("database_type", data)
        self.assertIn("app_base_url", data)
        self.assertIn("google_redirect_uri", data)
        self.assertIn("flask_secret_configured", data)
        self.assertIn("google_oauth_configured", data)
        self.assertIn("razorpay_configured", data)
        self.assertIn("razorpay_webhook_configured", data)

        # Ensure values are booleans or safe strings, never actual secret strings
        raw_text = res.get_data(as_text=True)
        # Test known secrets are absent
        secret_keys_to_verify_absent = [
            os.environ.get("FLASK_SECRET_KEY", ""),
            os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            os.environ.get("RAZORPAY_KEY_SECRET", ""),
            os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
        ]
        for secret_val in secret_keys_to_verify_absent:
            if secret_val and len(secret_val) > 5:
                self.assertNotIn(
                    secret_val,
                    raw_text,
                    "CRITICAL: Secret value was leaked in diagnostics endpoint!"
                )

    def test_02_missing_google_credentials_diagnosed_correctly(self):
        """Phase 6: Missing Google credentials correctly sets google_oauth_configured to False."""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
            self.app.config["GOOGLE_CLIENT_ID"] = ""
            self.app.config["GOOGLE_CLIENT_SECRET"] = ""
            diag = flask_app.get_config_diagnostics()
            self.assertFalse(diag["google_oauth_configured"])

    def test_03_missing_razorpay_credentials_diagnosed_correctly(self):
        """Phase 6: Missing Razorpay credentials correctly sets razorpay_configured to False."""
        with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": ""}):
            diag = flask_app.get_config_diagnostics()
            self.assertFalse(diag["razorpay_configured"])

    def test_04_sqlite_used_for_local_development(self):
        """Phase 6: Local development uses SQLite unless DATABASE_URL is set to postgres."""
        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            diag = flask_app.get_config_diagnostics()
            self.assertEqual(diag["database_type"], "SQLite (Local)")


class TestGoogleOAuthLocalFlow(BaseTestCase, unittest.TestCase):
    """Automated tests for Google OAuth local integration."""

    def test_01_oauth_initiation_uses_expected_callback_url(self):
        """Phase 6: Google OAuth initiation generates authorization URL targeting local redirect URI."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id-local-1234.apps.googleusercontent.com"
        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id-local-1234.apps.googleusercontent.com",
            "GOOGLE_REDIRECT_URI": "http://127.0.0.1:5000/auth/google/callback"
        }):
            res = self.client.get("/auth/google/login")
            self.assertEqual(res.status_code, 302)
            location = res.headers.get("Location", "")
            self.assertIn("accounts.google.com/o/oauth2/v2/auth", location)
            self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%3A5000%2Fauth%2Fgoogle%2Fcallback", location)
            self.assertIn("client_id=test-client-id-local-1234.apps.googleusercontent.com", location)
            self.assertIn("scope=openid+email+profile", location)
            self.assertIn("response_type=code", location)

            # Confirm state was saved in session
            with self.client.session_transaction() as sess:
                self.assertIn("oauth_state", sess)
                self.assertTrue(len(sess["oauth_state"]) > 20)

    def test_02_oauth_missing_credentials_handled_gracefully(self):
        """Phase 6: Missing Google client ID displays clear setup message rather than 500 stack trace."""
        self.app.config["GOOGLE_CLIENT_ID"] = ""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": ""}):
            res = self.client.get("/auth/google/login", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Google OAuth is not configured on this server", res.data)
            self.assertIn(b"Please configure GOOGLE_CLIENT_ID", res.data)

    def test_03_oauth_invalid_state_csrf_rejected(self):
        """Phase 6: Callback with forged or mismatched state is rejected with CSRF warning."""
        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "legitimate-crypto-state-token"

        res = self.client.get("/auth/google/callback?code=mock_code&state=tampered_state", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"State parameter mismatch", res.data)
        # Ensure user is not authenticated
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)

    @patch("app.requests.post")
    def test_04_oauth_callback_failure_does_not_authenticate(self, mock_post):
        """Phase 6: Google token endpoint non-200 failure fails gracefully without authenticating."""
        self.app.config["GOOGLE_CLIENT_ID"] = "test-client-id"
        self.app.config["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "invalid_client: Unauthorized client credentials"
        mock_post.return_value = mock_resp

        with self.client.session_transaction() as sess:
            sess["oauth_state"] = "valid-state"

        res = self.client.get("/auth/google/callback?code=bad_code&state=valid-state", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Failed to retrieve authentication tokens from Google", res.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)

    def test_05_oauth_user_cancelled_consent(self):
        """Phase 6: User cancelling consent on Google screen is handled cleanly."""
        res = self.client.get("/auth/google/callback?error=access_denied", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Google sign-in was cancelled by the user", res.data)
        with self.client.session_transaction() as sess:
            self.assertNotIn("customer_id", sess)


class TestRazorpayLocalPaymentFlow(BaseTestCase, unittest.TestCase):
    """Automated tests for Razorpay Test Mode checkout and verification."""

    def setUp(self):
        super().setUp()
        self.test_key_id = "rzp_test_mock_12345"
        self.test_key_secret = "secret_mock_test_key_67890"
        self.test_webhook_secret = "webhook_secret_mock_54321"

        os.environ["RAZORPAY_KEY_ID"] = self.test_key_id
        os.environ["RAZORPAY_KEY_SECRET"] = self.test_key_secret
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = self.test_webhook_secret

        # Register and login Bob
        self.register(name="Bob Tester", email="bob@test.com", password="password123", confirm="password123")
        self.login(email="bob@test.com", password="password123")

        conn = database.get_db_connection()
        bob = conn.execute("SELECT id FROM customers WHERE email = 'bob@test.com';").fetchone()
        self.bob_id = bob["id"]

        # Add delivery address for Bob
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer_addresses (customer_id, address_line, city, state, postal_code, is_default)
            VALUES (?, '45 MG Road', 'Mumbai', 'Maharashtra', '400001', 1);
        """, (self.bob_id,))
        self.address_id = cursor.lastrowid

        # Set stock for product 1 (₹2999) to 15
        cursor.execute("UPDATE products SET stock = 15 WHERE id = 1;")
        cursor.execute("DELETE FROM processed_webhooks;")
        conn.commit()
        conn.close()

    def add_item_to_cart(self, product_id=1, quantity=2):
        return self.client.post("/cart/add", data={
            "product_id": product_id,
            "quantity": quantity
        }, follow_redirects=True)

    def test_01_server_side_order_creation_parameters(self):
        """Phase 6: Server creates Razorpay order with correct amount in paise, currency INR, and receipt."""
        self.add_item_to_cart(product_id=1, quantity=2)  # 2 * 2999 = 5998.00 -> 599800 paise

        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            "id": "order_mock_test_778899",
            "amount": 599800,
            "currency": "INR",
            "status": "created"
        }

        with patch("app.get_razorpay_client", return_value=mock_client), \
             patch.dict(os.environ, {"MOCK_RAZORPAY": ""}):
            self.app.config["TESTING"] = False  # Exercise real client branch

            res = self.client.post("/checkout/place-order", data={
                "address_id": self.address_id,
                "payment_method": "razorpay"
            })
            self.app.config["TESTING"] = True  # Restore testing mode

            self.assertEqual(res.status_code, 200)
            mock_client.order.create.assert_called_once()
            call_args = mock_client.order.create.call_args[0][0]
            self.assertEqual(call_args["amount"], 599800)
            self.assertEqual(call_args["currency"], "INR")
            self.assertTrue(call_args["receipt"].startswith("ORD-"))
            self.assertEqual(call_args["notes"]["customer_id"], str(self.bob_id))

            # Verify order saved in DB
            conn = database.get_db_connection()
            order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.bob_id,)).fetchone()
            conn.close()
            self.assertEqual(order["razorpay_order_id"], "order_mock_test_778899")
            self.assertEqual(order["order_status"], "Pending Payment")
            self.assertEqual(order["payment_status"], "Pending")

    def test_02_unconfigured_razorpay_shows_setup_message(self):
        """Phase 6: Unconfigured Razorpay displays clear setup message and does not create order."""
        self.add_item_to_cart(product_id=1, quantity=1)

        with patch("app.get_razorpay_client", return_value=None), \
             patch.dict(os.environ, {"MOCK_RAZORPAY": ""}):
            self.app.config["TESTING"] = False  # Exercise non-testing branch

            res = self.client.post("/checkout/place-order", data={
                "address_id": self.address_id,
                "payment_method": "razorpay"
            }, follow_redirects=True)
            self.app.config["TESTING"] = True

            self.assertEqual(res.status_code, 200)
            self.assertIn(b"Razorpay payment gateway is not configured on this server", res.data)
            self.assertIn(b"Please configure valid RAZORPAY_KEY_ID", res.data)

    def test_03_valid_signature_acceptance_and_atomic_completion(self):
        """Phase 6: Valid HMAC signature confirms order, deducts stock, and clears cart."""
        self.add_item_to_cart(product_id=1, quantity=2)

        # Place order
        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.bob_id,)).fetchone()
        conn.close()

        rzp_order_id = order["razorpay_order_id"]
        rzp_payment_id = "pay_test_verified_123"
        secret = self.test_key_secret
        valid_signature = hmac.new(secret.encode("utf-8"), f"{rzp_order_id}|{rzp_payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()

        res = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": valid_signature
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Your Order is Confirmed", res.data)

        # Verify DB updates
        conn = database.get_db_connection()
        updated_order = conn.execute("SELECT * FROM orders WHERE id = ?;", (order["id"],)).fetchone()
        self.assertEqual(updated_order["order_status"], "Confirmed")
        self.assertEqual(updated_order["payment_status"], "Paid")
        self.assertEqual(updated_order["razorpay_payment_id"], rzp_payment_id)

        # Inventory deducted (15 - 2 = 13)
        prod = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod["stock"], 13)

        # Cart cleared
        cart = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.bob_id,)).fetchall()
        self.assertEqual(len(cart), 0)
        conn.close()

    def test_04_invalid_signature_rejection_preserves_cart_and_inventory(self):
        """Phase 6: Forged or invalid signature is rejected, marking order Failed and preserving cart & stock."""
        self.add_item_to_cart(product_id=1, quantity=3)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.bob_id,)).fetchone()
        conn.close()

        res = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": order["razorpay_order_id"],
            "razorpay_payment_id": "pay_test_tampered_999",
            "razorpay_signature": "forged_cryptographic_signature_value"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Payment verification failed: Invalid cryptographic signature", res.data)

        # Stock preserved (still 15)
        conn = database.get_db_connection()
        prod = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod["stock"], 15)

        # Cart preserved (items still there)
        cart = conn.execute("SELECT * FROM cart_items WHERE customer_id = ?;", (self.bob_id,)).fetchall()
        self.assertEqual(len(cart), 1)

        # Order status set to Failed
        failed_order = conn.execute("SELECT payment_status FROM orders WHERE id = ?;", (order["id"],)).fetchone()
        self.assertEqual(failed_order["payment_status"], "Failed")
        conn.close()

    def test_05_wrong_order_id_rejection(self):
        """Phase 6: Verification with mismatched Razorpay order ID is rejected."""
        self.add_item_to_cart(product_id=1, quantity=1)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.bob_id,)).fetchone()
        conn.close()

        # Submit a different order ID than what was registered for this order
        foreign_rzp_order_id = "order_foreign_mismatched_999"
        res = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": foreign_rzp_order_id,
            "razorpay_payment_id": "pay_test_any_111",
            "razorpay_signature": "some_sig"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Razorpay order ID mismatch", res.data)

        # Stock unchanged
        conn = database.get_db_connection()
        prod = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod["stock"], 15)
        conn.close()

    def test_06_duplicate_verification_cannot_process_order_twice(self):
        """Phase 6: Duplicate verification request is idempotent and does not double-deduct stock."""
        self.add_item_to_cart(product_id=1, quantity=2)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.bob_id,)).fetchone()
        conn.close()

        rzp_order_id = order["razorpay_order_id"]
        rzp_payment_id = "pay_test_idempotent_1"
        secret = self.test_key_secret
        valid_sig = hmac.new(secret.encode("utf-8"), f"{rzp_order_id}|{rzp_payment_id}".encode("utf-8"), hashlib.sha256).hexdigest()

        # First verification
        res1 = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": valid_sig
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # Stock is now 15 - 2 = 13
        conn = database.get_db_connection()
        prod1 = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod1["stock"], 13)
        conn.close()

        # Duplicate verification attempt
        res2 = self.client.post("/checkout/razorpay/verify", data={
            "order_reference": order["order_reference"],
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": rzp_payment_id,
            "razorpay_signature": valid_sig
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"Order is already paid and confirmed", res2.data)

        # Stock MUST STILL be 13, not 11
        conn = database.get_db_connection()
        prod2 = conn.execute("SELECT stock FROM products WHERE id = 1;").fetchone()
        self.assertEqual(prod2["stock"], 13)
        conn.close()

    def test_07_webhook_signatures_and_duplicate_events(self):
        """Phase 6: Webhook signature verification uses webhook secret and deduplicates events."""
        self.add_item_to_cart(product_id=1, quantity=1)

        self.client.post("/checkout/place-order", data={
            "address_id": self.address_id,
            "payment_method": "razorpay"
        })

        conn = database.get_db_connection()
        order = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC;", (self.bob_id,)).fetchone()
        conn.close()

        event_id = f"evt_mock_{secrets.token_hex(6)}"
        payload = {
            "event_id": event_id,
            "event": "order.paid",
            "payload": {
                "order": {
                    "entity": {
                        "id": order["razorpay_order_id"]
                    }
                },
                "payment": {
                    "entity": {
                        "id": "pay_webhook_live_999",
                        "status": "captured"
                    }
                }
            }
        }
        raw_body = json.dumps(payload).encode("utf-8")
        secret = self.test_webhook_secret
        valid_webhook_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        # 1. Invalid signature
        res_bad = self.client.post("/webhooks/razorpay", data=raw_body, headers={"X-Razorpay-Signature": "tampered_signature"})
        self.assertEqual(res_bad.status_code, 400)

        # 2. Valid signature
        res_ok = self.client.post("/webhooks/razorpay", data=raw_body, headers={"X-Razorpay-Signature": valid_webhook_sig})
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.get_json()["status"], "success")

        # 3. Duplicate event
        res_dup = self.client.post("/webhooks/razorpay", data=raw_body, headers={"X-Razorpay-Signature": valid_webhook_sig})
        self.assertEqual(res_dup.status_code, 200)
        self.assertEqual(res_dup.get_json()["status"], "already_processed")


if __name__ == "__main__":
    unittest.main()
