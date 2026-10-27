"""
tests/test_products.py - Module 2: Product Search & Filtering Test Suite.
Covers:
  - Catalog retrieval and category aggregation
  - Keyword search on product names
  - Category-based filtering
  - Price boundary constraints (min_price, max_price)
  - Combined multi-attribute filtering
  - Boundary and exception conditions (invalid price formats, inverted ranges, no matching items)
  - Filter reset / clear behavior
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


class TestProductSearchFilter(BaseTestCase, unittest.TestCase):
    """Test suite for Module 2: Product Search and Filtering."""

    def setUp(self):
        super().setUp()
        # Log in a baseline customer for all product browsing tests
        self.register(name="Catalog Viewer", email="viewer@test.com", password="password123", confirm="password123")
        self.login(email="viewer@test.com", password="password123")

    def test_01_display_all_products(self):
        """BB-PROD-01 / WB: Catalog displays all seed products when no filters applied."""
        res = self.client.get("/products")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Product Catalog", res.data)
        # Verify known seeded items across different categories appear
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertIn(b"Classic Cotton Crewneck T-Shirt", res.data)
        self.assertIn(b"Lightweight Running Sports Shoes", res.data)
        self.assertIn(b"UV-Protected Polarized Sunglasses", res.data)
        self.assertIn(b"Water-Resistant Laptop Backpack", res.data)

    def test_02_categories_dropdown_populated(self):
        """BB-PROD-02 / WB: Category filter dropdown contains all unique catalog categories."""
        res = self.client.get("/products")
        self.assertEqual(res.status_code, 200)
        expected_categories = [b"Electronics", b"Clothing", b"Footwear", b"Accessories", b"Bags"]
        for cat in expected_categories:
            self.assertIn(cat, res.data)

    def test_03_search_by_product_name(self):
        """BB-PROD-03 / WB: Search keyword filters catalog matching product name."""
        res = self.client.get("/products?search=Headphones")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertNotIn(b"Classic Cotton Crewneck T-Shirt", res.data)
        self.assertNotIn(b"Multi-Utility Canvas Duffel Bag", res.data)

    def test_04_search_case_insensitive_substring(self):
        """BB-PROD-04 / WB: Substring and case variations match product names properly."""
        res = self.client.get("/products?search=shoes")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Lightweight Running Sports Shoes", res.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res.data)

    def test_05_filter_by_category(self):
        """BB-PROD-05 / WB: Category filter returns only items belonging to selected category."""
        res = self.client.get("/products?category=Footwear")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Lightweight Running Sports Shoes", res.data)
        self.assertIn(b"Casual Canvas Low-Top Sneakers", res.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertNotIn(b"Water-Resistant Laptop Backpack", res.data)

    def test_06_search_category_via_parameter(self):
        """BB-PROD-06 / WB: Category search returns matching items for Electronics."""
        res = self.client.get("/products?category=Electronics")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertIn(b"Smart Fitness Tracker Watch", res.data)
        self.assertNotIn(b"Classic Cotton Crewneck T-Shirt", res.data)

    def test_07_search_category_name_in_keyword_field(self):
        """BB-PROD-07 / WB: Entering category into product name search searches name field strictly."""
        # The search bar specifies name LIKE ?; entering 'Footwear' yields 0 items because no name contains 'Footwear'
        res = self.client.get("/products?search=Footwear")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No products found", res.data)

    def test_08_minimum_price_filter(self):
        """BB-PROD-08 / WB: Minimum price filter excludes products priced below threshold."""
        # Min price = 2000 -> Should include Headphones (2999), exclude T-shirt (499) and Shoes (1799)
        res = self.client.get("/products?min_price=2000")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertNotIn(b"Lightweight Running Sports Shoes", res.data)
        self.assertNotIn(b"Classic Cotton Crewneck T-Shirt", res.data)

    def test_09_maximum_price_filter(self):
        """BB-PROD-09 / WB: Maximum price filter excludes products priced above threshold."""
        # Max price = 700 -> Should include T-Shirt (499), Sunglasses (699), exclude Jeans (1299)
        res = self.client.get("/products?max_price=700")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Classic Cotton Crewneck T-Shirt", res.data)
        self.assertIn(b"UV-Protected Polarized Sunglasses", res.data)
        self.assertNotIn(b"Slim Fit Stretch Denim Jeans", res.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res.data)

    def test_10_combined_multi_filters(self):
        """BB-PROD-10 / WB: Multi-criteria filtering combines keyword, category, min and max price."""
        # Keyword: 'Watch', Category: 'Accessories', Price between 1000 and 2000
        # Expected: 'Minimalist Stainless Steel Wristwatch' (1499, Accessories)
        # Excluded: 'Smart Fitness Tracker Watch' (1899, but category is Electronics)
        res = self.client.get("/products?search=Watch&category=Accessories&min_price=1000&max_price=2000")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Minimalist Stainless Steel Wristwatch", res.data)
        self.assertNotIn(b"Smart Fitness Tracker Watch", res.data)

    def test_11_no_matching_products(self):
        """BB-PROD-11 / WB: Queries with zero matches display clear user empty state."""
        res = self.client.get("/products?search=UnobtaniumDevice999")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No products found", res.data)

    def test_12_invalid_price_range_non_numeric(self):
        """BB-PROD-12 / WB: Non-numeric price values are safely caught without server 500 error."""
        # Non-numeric string caught by try-except ValueError
        res = self.client.get("/products?min_price=invalid_text&max_price=abc")
        self.assertEqual(res.status_code, 200)
        # Catalog displays normally without crashing
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)

    def test_13_invalid_price_range_inverted(self):
        """BB-PROD-13 / WB: Inverted price range (min_price > max_price) returns zero results."""
        # min_price 3000 > max_price 1000
        res = self.client.get("/products?min_price=3000&max_price=1000")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No products found", res.data)

    def test_14_clear_filters(self):
        """BB-PROD-14 / WB: Clearing filters resets search parameters and shows full catalog."""
        # Applying a restrictive filter first
        filtered_res = self.client.get("/products?category=Bags")
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", filtered_res.data)

        # Navigating to clean /products route
        cleared_res = self.client.get("/products")
        self.assertEqual(cleared_res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", cleared_res.data)
        self.assertIn(b"Multi-Utility Canvas Duffel Bag", cleared_res.data)

    # ==========================================================================
    # PRODUCT DETAILS TESTS (Task Requirements 1-8)
    # ==========================================================================

    def test_15_view_existing_product_details(self):
        """1. Authenticated customer can view an existing product."""
        res = self.client.get("/product/1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Noise-Canceling Wireless Headphones", res.data)
        self.assertIn(b"Electronics", res.data)
        self.assertIn(b"2999.00", res.data)
        self.assertIn(b"In Stock", res.data)

    def test_16_product_details_displays_all_fields(self):
        """2. The details page displays the correct product fields: name, category, price, stock, description."""
        res = self.client.get("/product/2")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Smart Fitness Tracker Watch", res.data)
        self.assertIn(b"Electronics", res.data)
        self.assertIn(b"1899.00", res.data)
        self.assertIn(b"20", res.data)
        self.assertIn(b"Waterproof smartwatch featuring continuous heart rate monitoring", res.data)
        self.assertIn(b"Add to Cart", res.data)

    def test_17_nonexistent_product_returns_404(self):
        """3. A nonexistent product returns 404."""
        res = self.client.get("/product/999999")
        self.assertEqual(res.status_code, 404)

    def test_18_unauthenticated_customer_redirected(self):
        """4. An unauthenticated customer is redirected according to existing authentication behavior."""
        # Unauthenticated client (no session)
        unauth_client = self.app.test_client()
        res = unauth_client.get("/product/1")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

        res_followed = unauth_client.get("/product/1", follow_redirects=True)
        self.assertEqual(res_followed.status_code, 200)
        self.assertIn(b"Please login to access this page", res_followed.data)

    def test_19_view_details_link_targets_correct_product(self):
        """5. The View Details link targets the correct product from the catalog."""
        res = self.client.get("/products")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'href="/product/1"', res.data)
        self.assertIn(b'id="btn-view-details-1"', res.data)
        self.assertIn(b"View Details", res.data)

    def test_20_add_product_from_details_page_to_cart(self):
        """6. Adding a product from its details page uses the existing cart logic."""
        res = self.client.post("/cart/add", data={"product_id": 1, "quantity": 2}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Added 2 x &#39;Noise-Canceling Wireless Headphones&#39;", res.data)
        self.assertIn(b"Shopping Cart", res.data)

        # Verify in DB
        conn = database.get_db_connection()
        customer = conn.execute("SELECT id FROM customers WHERE email = 'viewer@test.com';").fetchone()
        cart_row = conn.execute("SELECT * FROM cart_items WHERE customer_id = ? AND product_id = 1;", (customer["id"],)).fetchone()
        conn.close()
        self.assertIsNotNone(cart_row)
        self.assertEqual(cart_row["quantity"], 2)

    def test_21_cart_invalid_and_exceeding_quantities_rejected(self):
        """7. Invalid quantities and quantities exceeding stock are rejected."""
        # Zero or negative quantity
        res_zero = self.client.post("/cart/add", data={"product_id": 1, "quantity": 0}, follow_redirects=True)
        self.assertIn(b"Please select a quantity greater than zero", res_zero.data)

        # Non-numeric quantity
        res_text = self.client.post("/cart/add", data={"product_id": 1, "quantity": "invalid"}, follow_redirects=True)
        self.assertIn(b"Invalid product or quantity specified", res_text.data)

        # Exceeds available stock (Headphones has stock 15)
        res_exceed = self.client.post("/cart/add", data={"product_id": 1, "quantity": 999}, follow_redirects=True)
        self.assertIn(b"Cannot add 999 unit(s)", res_exceed.data)

    def test_22_existing_search_filter_behavior_unchanged(self):
        """8. Existing search and filter behavior remains unchanged with View Details links."""
        # Keyword search
        res_search = self.client.get("/products?search=T-Shirt")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"Classic Cotton Crewneck T-Shirt", res_search.data)
        self.assertIn(b'href="/product/3"', res_search.data)
        self.assertNotIn(b"Noise-Canceling Wireless Headphones", res_search.data)

        # Category filter
        res_cat = self.client.get("/products?category=Bags")
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b"Water-Resistant Laptop Backpack", res_cat.data)
        self.assertIn(b"Multi-Utility Canvas Duffel Bag", res_cat.data)
        self.assertNotIn(b"Classic Cotton Crewneck T-Shirt", res_cat.data)

        # Multi-filter
        res_multi = self.client.get("/products?category=Footwear&min_price=1000")
        self.assertEqual(res_multi.status_code, 200)
        self.assertIn(b"Lightweight Running Sports Shoes", res_multi.data)
        self.assertNotIn(b"Casual Canvas Low-Top Sneakers", res_multi.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)

