"""
verify_live_e2e.py - Live HTTP End-to-End Customer Journey & Security Audit Script.

Validates the running Flask server against all requirements from Phase 3:
1. Register & Login with isolated test data
2. Browse products & view product details
3. Add product to cart & change/update quantity
4. Add & select delivery address
5. Apply valid coupon & verify discount
6. Simulate payment failure (verify cart & inventory preserved)
7. Place Cash on Delivery order & verify confirmation
8. Verify cart is cleared & inventory is deducted
9. View order history and order details
10. Cancel order & verify stock restoration
11. Place order via Mock Online Payment (Approved)
12. Verify customer isolation & CSRF security constraints
"""

import sys
import time
import re
import sqlite3
import requests

# Ensure console supports utf-8 safely
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = "ecommerce.db"


def extract_csrf_token(html_text):
    """Helper to extract CSRF token from HTML form."""
    match = re.search(r'name="csrf_token"\s+value="([a-f0-9]{64})"', html_text)
    if not match:
        match = re.search(r'value="([a-f0-9]{64})"\s+name="csrf_token"', html_text)
    return match.group(1) if match else None


def get_product_stock(product_id):
    """Fetch current product stock directly from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT stock FROM products WHERE id = ?;", (product_id,)).fetchone()
    conn.close()
    return row["stock"] if row else None


def main():
    print("=" * 75)
    print("PHASE 3 LIVE END-TO-END HTTP VERIFICATION & SECURITY AUDIT")
    print(f"Target Server: {BASE_URL}")
    print("=" * 75)

    session = requests.Session()
    ts = int(time.time())
    test_email = f"college_tester_{ts}@example.com"
    test_password = "Password@123"
    test_name = f"College Demo Tester {ts}"

    # --------------------------------------------------------------------------
    # 1. Unauthenticated Home Redirect & Health
    # --------------------------------------------------------------------------
    print("\n[Step 1] Visiting Home Page (GET /)...")
    resp = session.get(f"{BASE_URL}/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "/login" in resp.url, f"Expected redirect to /login, got {resp.url}"
    print(f"  [OK] Server responded with 200; redirected to: {resp.url}")

    # --------------------------------------------------------------------------
    # 2. Register New Customer
    # --------------------------------------------------------------------------
    print(f"\n[Step 2] Registering customer '{test_email}'...")
    resp = session.get(f"{BASE_URL}/register")
    assert resp.status_code == 200
    csrf = extract_csrf_token(resp.text)
    reg_data = {
        "csrf_token": csrf,
        "name": test_name,
        "email": test_email,
        "password": test_password,
        "confirm_password": test_password
    }
    resp = session.post(f"{BASE_URL}/register", data=reg_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "Registration successful" in resp.text
    print("  [OK] Customer registered successfully.")

    # --------------------------------------------------------------------------
    # 3. Login as New Customer
    # --------------------------------------------------------------------------
    print(f"\n[Step 3] Logging in as '{test_email}'...")
    resp = session.get(f"{BASE_URL}/login")
    login_data = {
        "email": test_email,
        "password": test_password
    }
    resp = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "/dashboard" in resp.url
    assert test_name in resp.text
    assert "Available Products" in resp.text
    assert "My Orders" in resp.text
    print("  [OK] Logged in successfully. Dashboard stat cards verified.")

    # --------------------------------------------------------------------------
    # 4. Add Delivery Address
    # --------------------------------------------------------------------------
    print("\n[Step 4] Adding delivery address in Profile (/profile)...")
    resp = session.get(f"{BASE_URL}/profile")
    assert resp.status_code == 200
    csrf = extract_csrf_token(resp.text)
    addr_data = {
        "csrf_token": csrf,
        "full_name": "Demo Recipient",
        "phone": "9876543210",
        "address_line": "742 Evergreen Terrace, Apt 2B",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560001",
        "is_default": "1"
    }
    resp = session.post(f"{BASE_URL}/addresses/add", data=addr_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "742 Evergreen Terrace" in resp.text
    assert "Bengaluru" in resp.text
    print("  [OK] Delivery address added and marked as default.")

    # --------------------------------------------------------------------------
    # 5. Browse Products & Product Details
    # --------------------------------------------------------------------------
    print("\n[Step 5] Browsing catalog (/products) and viewing Product 1 details...")
    resp = session.get(f"{BASE_URL}/products")
    assert resp.status_code == 200
    assert "Noise-Canceling Wireless Headphones" in resp.text

    resp = session.get(f"{BASE_URL}/product/1")
    assert resp.status_code == 200
    assert "Noise-Canceling Wireless Headphones" in resp.text
    assert "Electronics" in resp.text
    assert "2999" in resp.text
    print("  [OK] Product details page loaded with correct specifications.")

    # --------------------------------------------------------------------------
    # 6. Add Product to Cart & Update Quantity
    # --------------------------------------------------------------------------
    print("\n[Step 6] Adding 1 unit of Product 1 to cart, then changing quantity to 2...")
    csrf = extract_csrf_token(resp.text)
    cart_data = {
        "csrf_token": csrf,
        "product_id": "1",
        "quantity": "1"
    }
    resp = session.post(f"{BASE_URL}/cart/add", data=cart_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "cart" in resp.url
    assert "Noise-Canceling Wireless Headphones" in resp.text
    assert "2999.00" in resp.text or "2999" in resp.text

    # Extract cart item ID from update form
    item_match = re.search(r'/cart/update/(\d+)', resp.text)
    assert item_match, "Cart item update form not found"
    cart_item_id = item_match.group(1)
    csrf = extract_csrf_token(resp.text)

    # Change quantity to 2
    update_data = {
        "csrf_token": csrf,
        "quantity": "2"
    }
    resp = session.post(f"{BASE_URL}/cart/update/{cart_item_id}", data=update_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "Updated quantity" in resp.text
    assert "5998.00" in resp.text
    print("  [OK] Quantity successfully changed to 2 units. Verified Subtotal: INR 5998.00.")

    # Record initial stock of Product 1 before orders
    stock_p1_initial = get_product_stock(1)
    print(f"  [INFO] Product 1 current inventory in database: {stock_p1_initial} units.")

    # --------------------------------------------------------------------------
    # 7. Proceed to Checkout & Verify Review
    # --------------------------------------------------------------------------
    print("\n[Step 7] Opening Checkout Review (/checkout)...")
    resp = session.get(f"{BASE_URL}/checkout")
    assert resp.status_code == 200
    assert "Order Checkout Review" in resp.text
    assert "742 Evergreen Terrace" in resp.text
    csrf = extract_csrf_token(resp.text)
    print("  [OK] Checkout page loaded with delivery address and order items.")

    # --------------------------------------------------------------------------
    # 8. Apply Promo Coupon 'WELCOME10'
    # --------------------------------------------------------------------------
    print("\n[Step 8] Applying promo coupon 'WELCOME10' (10% off)...")
    coupon_data = {
        "csrf_token": csrf,
        "coupon_code": "WELCOME10"
    }
    resp = session.post(f"{BASE_URL}/checkout/coupon", data=coupon_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "WELCOME10" in resp.text
    assert "599.80" in resp.text  # 10% of 5998.00
    assert "5398.20" in resp.text  # Final Payable
    print("  [OK] Coupon 'WELCOME10' applied. Discount: -INR 599.80. Final Payable: INR 5398.20.")

    # --------------------------------------------------------------------------
    # 9. Simulate Payment Failure & Verify Preservation
    # --------------------------------------------------------------------------
    print("\n[Step 9] Simulating Online Payment Failure (Declined)...")
    csrf = extract_csrf_token(resp.text)
    fail_data = {
        "csrf_token": csrf,
        "payment_method": "mock_online",
        "simulated_outcome": "failure"
    }
    resp = session.post(f"{BASE_URL}/checkout/place-order", data=fail_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "Simulated Payment Failed" in resp.text
    assert "cart items have been preserved" in resp.text

    # Verify inventory was NOT deducted
    stock_p1_after_fail = get_product_stock(1)
    assert stock_p1_after_fail == stock_p1_initial, "Stock should remain unchanged on failed payment"

    # Verify cart still has the 2 units
    resp = session.get(f"{BASE_URL}/cart")
    assert "5998.00" in resp.text
    print("  [OK] Payment failure handled gracefully: alert displayed, cart & inventory preserved.")

    # --------------------------------------------------------------------------
    # 10. Place Valid Order via Cash on Delivery (COD)
    # --------------------------------------------------------------------------
    print("\n[Step 10] Placing order via Cash on Delivery (COD)...")
    resp = session.get(f"{BASE_URL}/checkout")
    csrf = extract_csrf_token(resp.text)
    order_data = {
        "csrf_token": csrf,
        "payment_method": "cod"
    }
    resp = session.post(f"{BASE_URL}/checkout/place-order", data=order_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "/orders/confirmation/ORD-" in resp.url
    assert "Thank You! Your Order is Confirmed" in resp.text
    assert "Cash on Delivery" in resp.text
    assert "Pending" in resp.text
    assert "5398.20" in resp.text

    order_ref_match = re.search(r"ORD-\d{8}-[A-F0-9]+", resp.text)
    assert order_ref_match, "Order reference not found in confirmation HTML"
    order_ref = order_ref_match.group(0)
    print(f"  [OK] Order placed successfully! Order Reference: {order_ref}")

    # Verify stock deduction in database
    stock_p1_after_order = get_product_stock(1)
    assert stock_p1_after_order == stock_p1_initial - 2, f"Expected stock {stock_p1_initial - 2}, got {stock_p1_after_order}"
    print(f"  [OK] Product 1 inventory deducted by 2 units in DB ({stock_p1_initial} -> {stock_p1_after_order}).")

    # --------------------------------------------------------------------------
    # 11. Verify Cart is Cleared
    # --------------------------------------------------------------------------
    print("\n[Step 11] Verifying Shopping Cart is cleared after order...")
    resp = session.get(f"{BASE_URL}/cart")
    assert resp.status_code == 200
    assert "Your Cart is Currently Empty" in resp.text
    print("  [OK] Shopping cart is completely cleared.")

    # --------------------------------------------------------------------------
    # 12. Verify Orders History & Details
    # --------------------------------------------------------------------------
    print("\n[Step 12] Checking Customer Order History (/orders)...")
    resp = session.get(f"{BASE_URL}/orders")
    assert resp.status_code == 200
    assert order_ref in resp.text
    assert "Confirmed" in resp.text
    assert "5398.20" in resp.text
    print("  [OK] Order appears in Order History with Confirmed status.")

    # Extract order ID
    detail_match = re.search(r'/orders/(\d+)', resp.text)
    assert detail_match, "Order detail link not found in /orders"
    order_id = detail_match.group(1)

    print(f"\n[Step 13] Viewing Order Details for Order ID #{order_id}...")
    resp = session.get(f"{BASE_URL}/orders/{order_id}")
    assert resp.status_code == 200
    assert order_ref in resp.text
    assert "742 Evergreen Terrace" in resp.text
    assert "Noise-Canceling Wireless Headphones" in resp.text
    assert "Cancel Order" in resp.text
    print("  [OK] Order Details loaded with immutable snapshots and Cancel button.")

    # --------------------------------------------------------------------------
    # 14. Cancel Order and Verify Inventory Restoration
    # --------------------------------------------------------------------------
    print(f"\n[Step 14] Cancelling Order #{order_ref}...")
    csrf = extract_csrf_token(resp.text)
    cancel_data = {"csrf_token": csrf}
    resp = session.post(f"{BASE_URL}/orders/{order_id}/cancel", data=cancel_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "cancelled successfully" in resp.text
    assert "Cancelled" in resp.text

    # Verify inventory restoration in database
    stock_p1_restored = get_product_stock(1)
    assert stock_p1_restored == stock_p1_initial, f"Expected stock {stock_p1_initial}, got {stock_p1_restored}"
    print(f"  [OK] Order #{order_ref} cancelled. Stock restored to {stock_p1_restored} units.")

    # --------------------------------------------------------------------------
    # 15. Place Order with Mock Online Payment (Approved)
    # --------------------------------------------------------------------------
    print("\n[Step 15] Placing second order via Mock Online Payment (Approved)...")
    stock_p2_initial = get_product_stock(2)

    resp = session.get(f"{BASE_URL}/product/2")
    csrf = extract_csrf_token(resp.text)
    session.post(f"{BASE_URL}/cart/add", data={"csrf_token": csrf, "product_id": "2", "quantity": "1"}, allow_redirects=True)

    resp = session.get(f"{BASE_URL}/checkout")
    csrf = extract_csrf_token(resp.text)
    online_order_data = {
        "csrf_token": csrf,
        "payment_method": "mock_online",
        "simulated_outcome": "success"
    }
    resp = session.post(f"{BASE_URL}/checkout/place-order", data=online_order_data, allow_redirects=True)
    assert resp.status_code == 200
    assert "/orders/confirmation/ORD-" in resp.url
    assert "Confirmed" in resp.text
    assert "Paid" in resp.text
    assert "TXN-MOCK-" in resp.text

    stock_p2_after = get_product_stock(2)
    assert stock_p2_after == stock_p2_initial - 1
    print("  [OK] Mock Online Payment approved! Order confirmed with status 'Paid' and TXN reference.")

    # --------------------------------------------------------------------------
    # 16. Verify Order History Shows Both Orders
    # --------------------------------------------------------------------------
    print("\n[Step 16] Checking Order History for both orders...")
    resp = session.get(f"{BASE_URL}/orders")
    assert resp.status_code == 200
    assert "Total Orders (2)" in resp.text
    assert "Cancelled" in resp.text
    assert "Paid" in resp.text
    print("  [OK] Both orders listed correctly with distinct statuses (Cancelled and Paid).")

    # --------------------------------------------------------------------------
    # 17. Security Verification: Customer Isolation & CSRF
    # --------------------------------------------------------------------------
    print("\n[Step 17] Verifying Security Constraints (Cross-Customer Isolation & CSRF)...")
    # Register attacker customer
    session_attacker = requests.Session()
    attacker_email = f"attacker_{ts}@example.com"
    resp = session_attacker.get(f"{BASE_URL}/register")
    csrf_atk = extract_csrf_token(resp.text)
    session_attacker.post(f"{BASE_URL}/register", data={
        "csrf_token": csrf_atk,
        "name": "Attacker Bob",
        "email": attacker_email,
        "password": test_password,
        "confirm_password": test_password
    }, allow_redirects=True)

    session_attacker.post(f"{BASE_URL}/login", data={
        "email": attacker_email,
        "password": test_password
    }, allow_redirects=True)

    # Attacker tries to view Customer A's order details
    resp_atk = session_attacker.get(f"{BASE_URL}/orders/{order_id}", allow_redirects=True)
    assert resp_atk.status_code == 200
    assert "/orders" in resp_atk.url
    assert "not have permission" in resp_atk.text or "not found" in resp_atk.text
    # Attacker does NOT see Customer A's items or address
    assert "742 Evergreen Terrace" not in resp_atk.text
    assert "Noise-Canceling Wireless Headphones" not in resp_atk.text

    # Attacker tries to cancel Customer A's order using their own valid CSRF token
    csrf_atk_orders = extract_csrf_token(resp_atk.text)
    resp_atk_cancel = session_attacker.post(
        f"{BASE_URL}/orders/{order_id}/cancel", 
        data={"csrf_token": csrf_atk_orders}, 
        allow_redirects=True
    )
    assert "not have permission" in resp_atk_cancel.text or "not found" in resp_atk_cancel.text

    # Check that Customer A's order in DB is still untouched
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    order_row = conn.execute("SELECT order_status FROM orders WHERE id = ?;", (order_id,)).fetchone()
    conn.close()
    assert order_row["order_status"] == "Cancelled"  # Still has original status, attacker could not affect it
    print("  [OK] Customer isolation verified: Attacker cannot access or modify another customer's orders.")

    # Test CSRF Protection on original session
    resp_csrf_fail = session.post(f"{BASE_URL}/orders/{order_id}/cancel", data={"csrf_token": "invalid_fake_token"}, allow_redirects=True)
    assert "CSRF token mismatch" in resp_csrf_fail.text
    print("  [OK] CSRF protection verified: Invalid tokens rejected with security flash warning.")

    print("\n" + "=" * 75)
    print("ALL 17 LIVE END-TO-END HTTP VERIFICATION & SECURITY AUDIT CHECKS PASSED!")
    print("=" * 75)


if __name__ == "__main__":
    main()
