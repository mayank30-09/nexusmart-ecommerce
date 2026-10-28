"""
tests/test_playwright_logout_regression.py - Playwright E2E Browser Test for Logout and Session Invalidation
Verifies:
1. Logging in and viewing customer dashboard.
2. Logging out invalidates session cookie and redirects to login.
3. Hitting browser "Back" button does NOT restore authenticated state (pageshow forces re-evaluation / cache-control prevents cached page serving).
4. Direct navigation to protected routes (/dashboard, /orders, /profile, /checkout, /admin) is blocked and redirected to login.
"""

import os
import sys
import time
import subprocess
import requests
import pytest
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(WORKSPACE_DIR, "ecommerce_practical10")
BASE_URL = "http://127.0.0.1:5000"


def wait_for_server(url, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            res = requests.get(f"{url}/healthz", timeout=1)
            if res.status_code == 200:
                return True
        except Exception:
            time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def live_server():
    env = os.environ.copy()
    env["FLASK_ENV"] = "testing"
    env["FLASK_DEBUG"] = "0"
    env["FLASK_SECRET_KEY"] = "playwright-logout-test-key-2026"

    server_process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=APP_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not wait_for_server(BASE_URL):
        server_process.kill()
        pytest.fail("Flask server failed to start for Playwright logout test.")

    yield BASE_URL

    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()


def test_e2e_logout_and_browser_back_regression(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Register or Login with a test user
        test_email = f"logout_e2e_{int(time.time())}@nexusmart.com"
        test_pass = "TestPass123!"

        # Register
        page.goto(f"{BASE_URL}/register")
        page.fill("input[name='name']", "Logout Tester")
        page.fill("input[name='email']", test_email)
        page.fill("input[name='password']", test_pass)
        page.fill("input[name='confirm_password']", test_pass)
        page.click("button[type='submit']")

        # Login
        page.goto(f"{BASE_URL}/login")
        page.fill("input[name='email']", test_email)
        page.fill("input[name='password']", test_pass)
        page.click("button[type='submit']")

        # Verify on dashboard
        page.wait_for_url(f"{BASE_URL}/dashboard")
        assert "dashboard" in page.url.lower()
        assert "Logout Tester" in page.content() or "Logout" in page.content()

        # Step 2: Perform Logout
        page.click("a[href*='/logout']")
        page.wait_for_url(f"{BASE_URL}/login")
        assert "login" in page.url.lower()

        # Verify session cookies are cleared
        cookies = context.cookies(BASE_URL)
        session_cookie = [c for c in cookies if c["name"] == "session"]
        # In modern Flask with delete_cookie, cookie is either deleted or has empty/expired value
        if session_cookie:
            assert session_cookie[0]["value"] == "" or session_cookie[0]["expires"] <= time.time()

        # Step 3: Trigger Browser BACK navigation
        page.go_back()
        time.sleep(0.8)

        # After going back, due to pageshow reload and no-cache headers,
        # the page must NOT remain logged in. It must either reload to login or show unauthenticated state!
        assert "dashboard" not in page.url.lower() or "Please log in" in page.content() or "Sign In" in page.content()
        # Ensure we cannot access customer dashboard
        assert "Welcome back, Logout Tester" not in page.content()

        # Step 4: Direct URL access to protected routes
        protected_routes = ["/dashboard", "/profile", "/orders", "/checkout", "/admin"]
        for route in protected_routes:
            page.goto(f"{BASE_URL}{route}")
            time.sleep(0.3)
            # Must be redirected away from protected content to login
            assert route not in page.url or "login" in page.url.lower() or "Sign In" in page.content()
            assert "Welcome back, Logout Tester" not in page.content()

        browser.close()
