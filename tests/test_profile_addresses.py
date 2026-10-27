"""
tests/test_profile_addresses.py - Phase 2A: Customer Profile and Delivery Address Test Suite.
Covers:
  - Customer Profile viewing and authentication
  - Profile update (name and email changes, session sync)
  - Profile validation (empty fields, regex email syntax, duplicate email detection across accounts)
  - Delivery address addition, editing, and deletion
  - Default address assignment, atomic switching, and auto-promotion on deletion
  - Address validation (required fields, postal code formatting)
  - Multi-tenant customer data isolation (preventing cross-customer address viewing, editing, deletion, or default toggling)
  - CSRF anti-forgery validation on state-changing forms
  - Database schema initialization safety and data preservation
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


class TestCustomerProfileAndAddresses(BaseTestCase, unittest.TestCase):
    """Test suite for Customer Profile and Delivery Address Management."""

    def setUp(self):
        super().setUp()
        # Register and log in baseline customer Alice
        self.register(name="Alice Customer", email="alice@test.com", password="password123", confirm="password123")
        self.login(email="alice@test.com", password="password123")

    # ==========================================================================
    # 1. PROFILE MANAGEMENT TESTS
    # ==========================================================================

    def test_01_profile_page_requires_authentication(self):
        """Unauthenticated visitors accessing /profile are redirected to login."""
        unauth_client = self.app.test_client()
        res = unauth_client.get("/profile")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

        res_followed = unauth_client.get("/profile", follow_redirects=True)
        self.assertEqual(res_followed.status_code, 200)
        self.assertIn(b"Please login to access this page", res_followed.data)

    def test_02_profile_page_displays_customer_data(self):
        """Authenticated customer can view their personal information and credentials."""
        res = self.client.get("/profile")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Alice Customer", res.data)
        self.assertIn(b"alice@test.com", res.data)
        self.assertIn(b"Saved Delivery Addresses", res.data)

    def test_03_profile_update_success(self):
        """Customer can update their name and email, updating both database and active session."""
        res = self.client.post("/profile", data={
            "name": "Alice Wonderland",
            "email": "alicenew@test.com"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Profile updated successfully", res.data)
        self.assertIn(b"Alice Wonderland", res.data)
        self.assertIn(b"alicenew@test.com", res.data)

        # Verify SQLite row
        conn = database.get_db_connection()
        customer = conn.execute("SELECT * FROM customers WHERE email = 'alicenew@test.com';").fetchone()
        conn.close()
        self.assertIsNotNone(customer)
        self.assertEqual(customer["name"], "Alice Wonderland")

        # Verify active session updated
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["customer_name"], "Alice Wonderland")
            self.assertEqual(sess["customer_email"], "alicenew@test.com")

    def test_04_profile_update_validation_empty_fields(self):
        """Empty name or email is rejected by server-side validation."""
        # Empty name
        res_name = self.client.post("/profile", data={
            "name": "",
            "email": "alice@test.com"
        }, follow_redirects=True)
        self.assertIn(b"Name and email are required", res_name.data)

        # Empty email
        res_email = self.client.post("/profile", data={
            "name": "Alice Customer",
            "email": ""
        }, follow_redirects=True)
        self.assertIn(b"Name and email are required", res_email.data)

    def test_05_profile_update_invalid_email_format(self):
        """Invalid email syntax is rejected with validation alert."""
        res = self.client.post("/profile", data={
            "name": "Alice Customer",
            "email": "not-an-email"
        }, follow_redirects=True)
        self.assertIn(b"Please enter a valid email address", res.data)

    def test_06_profile_update_duplicate_email_rejected(self):
        """Changing email to one already registered by another customer is blocked."""
        # Alice logs out so we can register Bob
        self.client.get("/logout", follow_redirects=True)

        # Create second customer Bob
        self.register(name="Bob Smith", email="bob@test.com", password="password123", confirm="password123")

        # Bob logs out and Alice logs back in
        self.client.get("/logout", follow_redirects=True)
        self.login(email="alice@test.com", password="password123")

        # Try to change Alice's email to Bob's email
        res = self.client.post("/profile", data={
            "name": "Alice Customer",
            "email": "bob@test.com"
        }, follow_redirects=True)
        self.assertIn(b"This email is already in use by another account", res.data)

        # Case-insensitive duplicate check
        res_case = self.client.post("/profile", data={
            "name": "Alice Customer",
            "email": "BOB@TEST.COM"
        }, follow_redirects=True)
        self.assertIn(b"This email is already in use by another account", res_case.data)

        # Verify Alice's email did not change
        conn = database.get_db_connection()
        alice_db = conn.execute("SELECT * FROM customers WHERE email = 'alice@test.com';").fetchone()
        conn.close()
        self.assertIsNotNone(alice_db)

    # ==========================================================================
    # 2. DELIVERY ADDRESS MANAGEMENT TESTS
    # ==========================================================================

    def test_07_add_first_address_automatically_becomes_default(self):
        """The first delivery address added by a customer automatically becomes default."""
        res = self.client.post("/addresses/add", data={
            "address_line": "123 Ocean Drive, Apt 4B",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Address added successfully", res.data)
        self.assertIn(b"123 Ocean Drive, Apt 4B", res.data)
        self.assertIn(b"Default Delivery Address", res.data)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        addr = conn.execute("SELECT * FROM customer_addresses WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        self.assertIsNotNone(addr)
        self.assertEqual(addr["is_default"], 1)

    def test_08_add_second_address_with_explicit_default_switches_atomically(self):
        """Adding a subsequent address marked as default unsets default on the previous address."""
        # Add Address 1 (default)
        self.client.post("/addresses/add", data={
            "address_line": "123 Ocean Drive",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001"
        }, follow_redirects=True)

        # Add Address 2 marked as default
        self.client.post("/addresses/add", data={
            "address_line": "456 Hill Road",
            "city": "Pune",
            "state": "Maharashtra",
            "postal_code": "411001",
            "is_default": "1"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        addresses = conn.execute(
            "SELECT * FROM customer_addresses WHERE customer_id = ? ORDER BY id ASC;",
            (customer["id"],)
        ).fetchall()
        conn.close()

        self.assertEqual(len(addresses), 2)
        # First address should now be non-default
        self.assertEqual(addresses[0]["is_default"], 0)
        # Second address should be default
        self.assertEqual(addresses[1]["is_default"], 1)

    def test_09_add_address_validation_failures(self):
        """Missing fields or invalid postal codes are rejected."""
        # Missing address_line
        res1 = self.client.post("/addresses/add", data={
            "address_line": "",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001"
        }, follow_redirects=True)
        self.assertIn(b"All address fields are required", res1.data)

        # Invalid postal code format
        res2 = self.client.post("/addresses/add", data={
            "address_line": "123 Ocean Drive",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "!@#$"
        }, follow_redirects=True)
        self.assertIn(b"Please enter a valid postal code", res2.data)

    def test_10_edit_address_success(self):
        """Customer can edit an existing address they own."""
        # Add address
        self.client.post("/addresses/add", data={
            "address_line": "100 Initial St",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "110001"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        addr = conn.execute("SELECT * FROM customer_addresses WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        # GET edit page
        res_get = self.client.get(f"/addresses/edit/{addr['id']}")
        self.assertEqual(res_get.status_code, 200)
        self.assertIn(b"100 Initial St", res_get.data)

        # POST updated address
        res_post = self.client.post(f"/addresses/edit/{addr['id']}", data={
            "address_line": "100 Updated Avenue",
            "city": "New Delhi",
            "state": "Delhi",
            "postal_code": "110002"
        }, follow_redirects=True)

        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b"Address updated successfully", res_post.data)
        self.assertIn(b"100 Updated Avenue", res_post.data)

        # Verify in database
        conn = database.get_db_connection()
        updated_addr = conn.execute("SELECT * FROM customer_addresses WHERE id = ?;", (addr["id"],)).fetchone()
        conn.close()
        self.assertEqual(updated_addr["address_line"], "100 Updated Avenue")
        self.assertEqual(updated_addr["postal_code"], "110002")

    def test_11_edit_address_validation_failures(self):
        """Empty fields or invalid postal codes during edit return errors."""
        self.client.post("/addresses/add", data={
            "address_line": "100 Street",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "110001"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        addr = conn.execute("SELECT * FROM customer_addresses WHERE customer_id = ?;", (customer["id"],)).fetchone()
        conn.close()

        res_empty = self.client.post(f"/addresses/edit/{addr['id']}", data={
            "address_line": "",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "110001"
        }, follow_redirects=True)
        self.assertIn(b"All address fields are required", res_empty.data)

        res_bad_zip = self.client.post(f"/addresses/edit/{addr['id']}", data={
            "address_line": "100 Street",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "$$%%"
        }, follow_redirects=True)
        self.assertIn(b"Please enter a valid postal code", res_bad_zip.data)

    def test_12_set_default_address(self):
        """Setting an address as default updates flags so only one address is default."""
        # Add Address 1 (default)
        self.client.post("/addresses/add", data={
            "address_line": "First Address",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001"
        }, follow_redirects=True)

        # Add Address 2 (non-default)
        self.client.post("/addresses/add", data={
            "address_line": "Second Address",
            "city": "Pune",
            "state": "Maharashtra",
            "postal_code": "411001"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        addr1 = conn.execute("SELECT id FROM customer_addresses WHERE customer_id = ? AND address_line = 'First Address';", (customer["id"],)).fetchone()
        addr2 = conn.execute("SELECT id FROM customer_addresses WHERE customer_id = ? AND address_line = 'Second Address';", (customer["id"],)).fetchone()
        conn.close()

        # Explicitly set Address 2 as default
        res = self.client.post(f"/addresses/default/{addr2['id']}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Default delivery address updated", res.data)

        conn = database.get_db_connection()
        chk1 = conn.execute("SELECT is_default FROM customer_addresses WHERE id = ?;", (addr1["id"],)).fetchone()
        chk2 = conn.execute("SELECT is_default FROM customer_addresses WHERE id = ?;", (addr2["id"],)).fetchone()
        conn.close()

        self.assertEqual(chk1["is_default"], 0)
        self.assertEqual(chk2["is_default"], 1)

    def test_13_delete_address_and_auto_promote_remaining(self):
        """Deleting the default address automatically promotes another remaining address to default."""
        self.client.post("/addresses/add", data={
            "address_line": "Address One",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001"
        }, follow_redirects=True)

        self.client.post("/addresses/add", data={
            "address_line": "Address Two",
            "city": "Pune",
            "state": "Maharashtra",
            "postal_code": "411001"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        addr1 = conn.execute("SELECT id, is_default FROM customer_addresses WHERE customer_id = ? AND address_line = 'Address One';", (customer["id"],)).fetchone()
        addr2 = conn.execute("SELECT id, is_default FROM customer_addresses WHERE customer_id = ? AND address_line = 'Address Two';", (customer["id"],)).fetchone()
        conn.close()

        # Address 1 was default. Delete Address 1.
        self.assertEqual(addr1["is_default"], 1)
        res = self.client.post(f"/addresses/delete/{addr1['id']}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Address deleted successfully", res.data)

        # Address 2 should now be promoted to default
        conn = database.get_db_connection()
        remaining_addr = conn.execute("SELECT * FROM customer_addresses WHERE id = ?;", (addr2["id"],)).fetchone()
        deleted_addr = conn.execute("SELECT * FROM customer_addresses WHERE id = ?;", (addr1["id"],)).fetchone()
        conn.close()

        self.assertIsNone(deleted_addr)
        self.assertEqual(remaining_addr["is_default"], 1)

    # ==========================================================================
    # 3. MULTI-TENANT ISOLATION TESTS (CROSS-CUSTOMER ACCESS PREVENTION)
    # ==========================================================================

    def test_14_cross_customer_address_isolation(self):
        """Customer B cannot view, edit, delete, or set default on Customer A's address."""
        # Alice creates an address
        self.client.post("/addresses/add", data={
            "address_line": "Alice Secret Mansion",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001"
        }, follow_redirects=True)

        conn = database.get_db_connection()
        alice = conn.execute("SELECT id FROM customers WHERE email = 'alice@test.com';").fetchone()
        alice_addr = conn.execute("SELECT id FROM customer_addresses WHERE customer_id = ?;", (alice["id"],)).fetchone()
        conn.close()

        # Alice logs out
        self.client.get("/logout", follow_redirects=True)

        # Register and log in as Bob
        self.register(name="Bob Attacker", email="bob@test.com", password="password123", confirm="password123")
        self.login(email="bob@test.com", password="password123")

        # Bob attempts to GET Alice's address edit page -> 404
        res_get = self.client.get(f"/addresses/edit/{alice_addr['id']}")
        self.assertEqual(res_get.status_code, 404)

        # Bob attempts to POST edit Alice's address -> 404
        res_edit = self.client.post(f"/addresses/edit/{alice_addr['id']}", data={
            "address_line": "Hacked Address",
            "city": "Hacked City",
            "state": "Hacked State",
            "postal_code": "999999"
        })
        self.assertEqual(res_edit.status_code, 404)

        # Bob attempts to POST delete Alice's address -> 404
        res_del = self.client.post(f"/addresses/delete/{alice_addr['id']}")
        self.assertEqual(res_del.status_code, 404)

        # Bob attempts to set default on Alice's address -> 404
        res_def = self.client.post(f"/addresses/default/{alice_addr['id']}")
        self.assertEqual(res_def.status_code, 404)

        # Verify Alice's address remains unmodified
        conn = database.get_db_connection()
        intact_addr = conn.execute("SELECT * FROM customer_addresses WHERE id = ?;", (alice_addr["id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(intact_addr)
        self.assertEqual(intact_addr["address_line"], "Alice Secret Mansion")

    # ==========================================================================
    # 4. CSRF PROTECTION TESTS
    # ==========================================================================

    def test_15_csrf_protection_validation(self):
        """When CSRF protection is active, requests with missing or invalid tokens are rejected."""
        self.app.config["TESTING"] = False
        self.app.config["WTF_CSRF_ENABLED"] = True

        try:
            # POST without CSRF token
            res = self.client.post("/profile", data={
                "name": "Attacker Name",
                "email": "attacker@test.com"
            }, follow_redirects=True)
            self.assertIn(b"Security verification failed", res.data)

            # POST address without CSRF token
            res_addr = self.client.post("/addresses/add", data={
                "address_line": "CSRF Street",
                "city": "City",
                "state": "State",
                "postal_code": "12345"
            }, follow_redirects=True)
            self.assertIn(b"Security verification failed", res_addr.data)

            # Fetch valid token from active session
            with self.client.session_transaction() as sess:
                valid_token = sess.get("csrf_token")

            # POST with valid token succeeds
            res_valid = self.client.post("/profile", data={
                "csrf_token": valid_token,
                "name": "Valid CSRF User",
                "email": "alice@test.com"
            }, follow_redirects=True)
            self.assertIn(b"Profile updated successfully", res_valid.data)

        finally:
            self.app.config["TESTING"] = True
            self.app.config["WTF_CSRF_ENABLED"] = False

    # ==========================================================================
    # 5. SCHEMA & MIGRATION SAFETY TESTS
    # ==========================================================================

    def test_16_database_migration_preserves_existing_data(self):
        """Running init_db() preserves all existing customer accounts, products, and addresses."""
        # Add an address for Alice
        self.client.post("/addresses/add", data={
            "address_line": "Migration Test St",
            "city": "Bangalore",
            "state": "Karnataka",
            "postal_code": "560001"
        }, follow_redirects=True)

        # Trigger database schema initialization again
        database.init_db()

        conn = database.get_db_connection()
        customers = conn.execute("SELECT COUNT(*) AS count FROM customers;").fetchone()["count"]
        products = conn.execute("SELECT COUNT(*) AS count FROM products;").fetchone()["count"]
        addresses = conn.execute("SELECT COUNT(*) AS count FROM customer_addresses;").fetchone()["count"]
        conn.close()

        self.assertGreater(customers, 0)
        self.assertEqual(products, 10)
        self.assertGreater(addresses, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
