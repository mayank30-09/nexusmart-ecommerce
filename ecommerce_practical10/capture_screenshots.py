"""
capture_screenshots.py - Automated browser session to capture actual, authentic
screenshots of all 11 required application states for Practical-10 documentation.
"""

import os
import time
import threading
from playwright.sync_api import sync_playwright
import app as flask_app
import database

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

PORT = 5002
BASE_URL = f"http://127.0.0.1:{PORT}"


def run_server():
    """Run Flask server on test port."""
    database.init_db()
    flask_app.app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)


def main():
    # 1. Reset database customer & cart for clean run
    conn = database.get_db_connection()
    conn.execute("DELETE FROM cart_items;")
    conn.execute("DELETE FROM customers WHERE email LIKE '%mayank%' OR email LIKE '%amit%';")
    conn.commit()
    conn.close()

    # 2. Start Flask in daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Give server time to bind

    print(f"Server started at {BASE_URL}. Launching Playwright Chromium...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 850})
        page = context.new_page()

        # -------------------------------------------------------------
        # 1. Registration Page
        # -------------------------------------------------------------
        page.goto(f"{BASE_URL}/register")
        page.wait_for_selector("#register-form")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_registration_page.png"))
        print("[1/11] Captured 01_registration_page.png")

        # -------------------------------------------------------------
        # 2. Successful Registration
        # -------------------------------------------------------------
        page.fill("#name", "Mayank Viradiya")
        page.fill("#email", "mayank.viradiya@example.com")
        page.fill("#password", "password123")
        page.fill("#confirm_password", "password123")
        page.click("#btn-register-submit")
        page.wait_for_url(f"{BASE_URL}/login")
        page.wait_for_selector(".alert-success")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_successful_registration.png"))
        print("[2/11] Captured 02_successful_registration.png")

        # -------------------------------------------------------------
        # 3. Login Page
        # -------------------------------------------------------------
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector("#login-form")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_login_page.png"))
        print("[3/11] Captured 03_login_page.png")

        # -------------------------------------------------------------
        # 4. Successful Login / Dashboard
        # -------------------------------------------------------------
        page.fill("#email", "mayank.viradiya@example.com")
        page.fill("#password", "password123")
        page.click("#btn-login-submit")
        page.wait_for_url(f"{BASE_URL}/dashboard")
        page.wait_for_selector(".dashboard-header")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_dashboard.png"))
        print("[4/11] Captured 04_dashboard.png")

        # -------------------------------------------------------------
        # 5. Product List
        # -------------------------------------------------------------
        page.goto(f"{BASE_URL}/products")
        page.wait_for_selector("#product-grid-list")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_product_list.png"))
        print("[5/11] Captured 05_product_list.png")

        # -------------------------------------------------------------
        # 6. Product Search
        # -------------------------------------------------------------
        page.fill("#search", "Headphones")
        page.click("#btn-apply-filters")
        page.wait_for_selector("#product-grid-list")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_product_search.png"))
        print("[6/11] Captured 06_product_search.png")

        # -------------------------------------------------------------
        # 7. Product Filtering
        # -------------------------------------------------------------
        page.click("#btn-clear-filters")
        page.wait_for_url(f"{BASE_URL}/products")
        page.select_option("#category", "Footwear")
        page.fill("#min_price", "500")
        page.fill("#max_price", "2000")
        page.click("#btn-apply-filters")
        page.wait_for_selector("#product-grid-list")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_product_filtering.png"))
        print("[7/11] Captured 07_product_filtering.png")

        # -------------------------------------------------------------
        # 8. Product Added to Cart
        # -------------------------------------------------------------
        page.click("#btn-clear-filters")
        page.wait_for_url(f"{BASE_URL}/products")
        # Add 2 units of product 1 (Headphones)
        page.fill("#qty-input-1", "2")
        page.click("#btn-add-cart-1")
        page.wait_for_url(f"{BASE_URL}/cart")
        page.wait_for_selector(".alert-success")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_product_added_to_cart.png"))
        print("[8/11] Captured 08_product_added_to_cart.png")

        # -------------------------------------------------------------
        # 9. Cart Page with Multiple Items & Totals
        # -------------------------------------------------------------
        page.goto(f"{BASE_URL}/products")
        # Add 1 unit of product 3 (Cotton T-Shirt)
        page.fill("#qty-input-3", "2")
        page.click("#btn-add-cart-3")
        page.wait_for_url(f"{BASE_URL}/cart")
        page.wait_for_selector("#cart-items-table")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_cart_page.png"))
        print("[9/11] Captured 09_cart_page.png")

        # -------------------------------------------------------------
        # 10. Updated Cart
        # -------------------------------------------------------------
        # Locate input for item 3 and change quantity to 4
        qty_inputs = page.locator("input[name='quantity']").all()
        # Update the second item's quantity
        if len(qty_inputs) > 0:
            qty_inputs[-1].fill("4")
            update_btns = page.locator("button:has-text('Update')").all()
            update_btns[-1].click()
            page.wait_for_selector(".alert-success")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_updated_cart.png"))
        print("[10/11] Captured 10_updated_cart.png")

        # -------------------------------------------------------------
        # 11. Removed Product / Final Cart
        # -------------------------------------------------------------
        remove_btns = page.locator("button:has-text('Remove')").all()
        if len(remove_btns) > 0:
            remove_btns[0].click()
            page.wait_for_selector(".alert-info")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "11_removed_product_final_cart.png"))
        print("[11/11] Captured 11_removed_product_final_cart.png")

        browser.close()

    print("All 11 authentic screenshots captured successfully in:", SCREENSHOTS_DIR)


if __name__ == "__main__":
    main()
