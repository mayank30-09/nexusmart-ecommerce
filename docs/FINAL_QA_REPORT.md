# NexusMart — Final Quality Assurance, Security Audit & Verification Report

**Project:** NexusMart E-Commerce Platform  
**Target Environment:** Local Demonstration (`http://127.0.0.1:5000`) & Cloud Deployment  
**Audit Completion Date:** October 28, 2026  
**Auditor:** Senior Full-Stack QA, Application Security & Automation Engineering  
**Application Root:** `d:/AI-Workspace/projects/e-commerce-web/ecommerce_practical10`  
**Test Suite Directory:** `d:/AI-Workspace/projects/e-commerce-web/tests`  
**Application Status:** HEALTHY (`http://127.0.0.1:5000/healthz`)  

---

## 1. Executive Summary & Verification Metrics

A complete, systematic quality assurance and application security audit was performed across all modules of NexusMart. All defects discovered during verification—including the primary session persistence and logout flaw—were reproduced, isolated to their underlying causes, remediated via minimal safe code changes, and validated against regression test suites.

### 1.1 Complete Automated Test Summary

| Test Category | Suite / Test File | Tests Run | Passed | Failed | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Session Persistence & Admin Security** | `tests/test_session_and_security.py` | 11 | 11 | 0 | **100% PASSED** |
| **Playwright Browser Logout Regression** | `tests/test_playwright_logout_regression.py` | 1 | 1 | 0 | **100% PASSED** |
| **Config & Local Integrations** | `tests/test_config_and_local_integrations.py` | 12 | 12 | 0 | **100% PASSED** |
| **Order Placement & Transactions** | `tests/test_orders_payments.py` | 23 | 23 | 0 | **100% PASSED** |
| **Cart & Warehouse Stock Boundaries** | `tests/test_cart.py` | 16 | 16 | 0 | **100% PASSED** |
| **Catalog Search & Filtering** | `tests/test_products.py` | 22 | 22 | 0 | **100% PASSED** |
| **Checkout Review & Coupons** | `tests/test_checkout_discounts.py` | 18 | 18 | 0 | **100% PASSED** |
| **Customer Profile & Address Book** | `tests/test_profile_addresses.py` | 16 | 16 | 0 | **100% PASSED** |
| **Razorpay Test Integration** | `tests/test_razorpay_checkout.py` | 5 | 5 | 0 | **100% PASSED** |
| **Admin Operations & Portal** | `tests/test_admin.py` | 20 | 20 | 0 | **100% PASSED** |
| **Authentication & Accounts** | `tests/test_auth.py` | 25 | 25 | 0 | **100% PASSED** |
| **AI Product Recommendations** | `tests/test_ai_recommendations.py` | 8 | 8 | 0 | **100% PASSED** |
| **Subtotal Pytest Suite** | `pytest -v tests/` | **176** | **176** | **0** | **100% PASSED** |
| **Legacy Integration Suite** | `python ecommerce_practical10/test_app.py` | **37** | **37** | **0** | **100% PASSED** |
| **Total Automated Tests** | **Full Project Automated Suite** | **213** | **213** | **0** | **100% PASSED** |
| **Playwright Live Browser Verification** | `python run_playwright_verification.py` | **25/25** | **25** | **0** | **100% VERIFIED** |

---

## 2. Priority 1: Defect Root Cause & Resolution for Session Invalidation

### 2.1 Problem Description
Following logout, clicking the browser Back button or revisiting sensitive URLs rendered authenticated pages with the user's name still displayed in the header.

### 2.2 Root Causes Identified
1. **Missing Cache-Control Headers (`bfcache` Leakage):**
   HTTP responses lacked `Cache-Control: no-cache, no-store, must-revalidate, private` headers. Chromium, Edge, and Firefox retained rendered HTML in Back/Forward Cache (`bfcache`).
2. **Missing Cookie Invalidation on Logout:**
   `session.clear()` emptied the session dictionary in memory, but did not issue `Set-Cookie` deletion headers with expired timestamps.
3. **Passive Authentication Checks:**
   `@login_required` only verified `customer_id` presence in the session cookie without querying the database to ensure the account was active.
4. **Navbar Caching:**
   Public pages retained user greeting text inside cached HTML DOM fragments.

### 2.3 Fixes Implemented
- **Server Headers (`ecommerce_practical10/app.py`):** Added `@app.after_request` handler adding `Cache-Control: no-cache, no-store, must-revalidate, private`, `Pragma: no-cache`, `Expires: 0`, and security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`) to sensitive routes.
- **Active DB Lookup (`ecommerce_practical10/app.py`):** `@login_required` and `@admin_required` query the SQLite database on every request. Tampered session cookies are rejected immediately with HTTP 403 or redirect to login.
- **Cookie Deletion (`ecommerce_practical10/app.py`):** `logout()` and `admin_logout()` call `response.delete_cookie(app.config.get("SESSION_COOKIE_NAME", "session"), path="/")`.
- **Client Invalidation (`ecommerce_practical10/templates/base.html`):** Injected meta cache-control tags and a `pageshow` listener detecting `event.persisted` to force page reload on back-forward navigation.

---

## 3. Confirmed Defects, Severity & Remediation Matrix

| Defect ID | Severity | Area | Problem | Root Cause | Fix Applied | Regression Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | **Critical** | Auth / Session | Logged-out user appeared logged in on Back button | Missing `Cache-Control: no-store` headers and missing cookie deletion on logout | Added `@app.after_request` cache headers, cookie deletion on logout, and `pageshow` reload listener | `test_session_and_security.py::test_01`, `test_02`, `test_03`; `test_playwright_logout_regression.py` |
| **BUG-02** | **High** | Admin RBAC | Client-side session tampering for admin access | `@admin_required` trusted `session.get('is_admin')` without querying SQLite | Updated `@admin_required` to query `SELECT is_admin FROM customers WHERE id = ?` on every request | `test_session_and_security.py::test_02_session_tampering_for_admin_rejected_by_db_check` |
| **BUG-03** | **High** | Admin Provisioning | No controlled CLI to manage admins without manual SQL manipulation | Missing management CLI; risk of locking out the last admin | Created `manage_admin.py` and Flask CLI commands with protection against demoting the last admin | `test_session_and_security.py::test_03_admin_cli_promote_and_demote`, `test_06_cannot_demote_only_admin` |
| **BUG-04** | **Medium** | Admin Recovery | No secure CLI command to reset an unknown admin password | Lack of recovery CLI subcommand | Added `manage_admin.py reset-password` and `flask reset-admin-password` commands | `test_session_and_security.py::test_05_admin_cli_reset_password` |
| **BUG-05** | **Medium** | Session Integrity | Stale or deleted customer sessions remained accepted until expiry | `@login_required` did not verify account existence in DB | Added active DB lookup in `@login_required`; purges session if record is missing | `test_session_and_security.py::test_04_deleted_or_stale_customer_session_rejected_on_every_request` |
| **BUG-06** | **Medium** | Information Security | Session cookies lacked explicit security flags in local configuration | Default Flask session cookie settings omitted explicit path and samesite parameters | Configured `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_PATH='/'` | `test_session_and_security.py::test_01_logout_clears_session_and_deletes_cookie` |

---

## 4. Playwright End-to-End Browser Workflows Verified

The Playwright browser automation suite (`run_playwright_verification.py`) executed 8 complete user scenarios across Desktop (1440x900) and Mobile (390x844) viewports. All 25 screenshots were generated and saved to `artifacts/deployment/screenshots/`:

1. `01-homepage-desktop.png`: Customer Dashboard with greeting, metrics, and shortcuts.
2. `02-product-catalog.png`: Product Catalog with category badges, INR pricing, and search filters.
3. `03-product-detail.png`: Product Details with high-res badge, stock counter, and quantity controls.
4. `04-login-page.png`: Customer Sign In page with email and Google OAuth option.
5. `04b-google-signin-redirect.png`: Google OAuth 2.0 authorization redirect and consent handshake.
6. `05-registration-page.png`: Customer Registration form with validation fields.
7. `06-cart.png`: Shopping Cart showing line items, quantity modifiers, subtotal, and checkout CTA.
8. `07-checkout.png`: Checkout Review page with selected address, 10% coupon discount applied, and payment selection.
9. `08-razorpay-test-checkout.png`: Official Razorpay Standard Checkout launch modal with order reference and secure encryption.
10. `08b-payment-failed-result.png`: Payment Verification Rejection: invalid signature safely blocked with cart preserved.
11. `09-order-confirmation.png`: Order Confirmation invoice with verified payment status, reference code, and delivery summary.
12. `10-order-history.png`: Customer Order History table with order status Confirmed and payment status Paid.
13. `11-order-detail.png`: Detailed Order Breakdown with immutable snapshots of items, coupon code, and shipping address.
14. `11b-ai-recommendations.png`: AI-Powered Product Recommendations on Customer Dashboard tailored by browsing & purchase history.
15. `12-customer-profile-addresses.png`: Customer Profile with saved shipping addresses, default badge, and edit actions.
16. `13-about-page.png`: About NexusMart corporate mission, values, and platform architecture.
17. `14-contact-page.png`: NexusMart Customer Care, Support FAQs, and Help Desk.
18. `15-mobile-homepage.png`: Responsive Mobile Article & Policy layout without horizontal overflow.
19. `16-mobile-catalog.png`: Responsive Mobile Catalog with touch-friendly cards and adaptive grid.
20. `17-mobile-checkout.png`: Responsive Mobile Checkout review with stacked address and payment cards.
21. `18-mobile-product-detail.png`: Responsive Mobile Product Details with single-column touch controls.
22. `19-admin-dashboard.png`: NexusMart Operations Admin Dashboard with live metrics, revenue, and inventory alerts.
23. `20-admin-products.png`: Admin Product Catalog & Direct Stock Adjustment Interface.
24. `21-admin-orders.png`: Admin Customer Order Management with status transition actions.
25. `22-admin-coupons.png`: Admin Promotional Coupon Management with activation toggle & creation form.

---

## 5. Tests That Could Not Be Run & Intentional Boundaries

1. **Real Currency Credit Card Transactions:**
   - *Reason:* Operating strictly in **Razorpay Test Mode** using simulated cards, UPI IDs, and net banking sandbox credentials. Real monetary charges require business verification, merchant KYC, and live gateway activation.
2. **Arbitrary Public Google User Authentication:**
   - *Reason:* Google OAuth 2.0 app registration is in Google Cloud's **Testing Publishing Status**. In this mode, Google requires tester Gmail accounts to be explicitly whitelisted in the Google Cloud Console. Standard password registration and local account linking are fully functional.

---

## 6. Local Demonstration vs. Production Readiness

| Dimension | Local Demo Environment | Production Cloud Deployment |
| :--- | :--- | :--- |
| **Database** | SQLite (`ecommerce.db`) | Managed PostgreSQL (Render, Neon, AWS RDS) |
| **Web Server** | Flask Development Server (`python app.py`) | Production WSGI (`gunicorn -w 4 wsgi:app`) |
| **SSL / HTTPS** | Plaintext HTTP (`http://127.0.0.1:5000`) | SSL/TLS Termination Proxy (`https://...`) |
| **Cookie Flag** | `SESSION_COOKIE_SECURE=False` | `SESSION_COOKIE_SECURE=True` with `ProxyFix` |
| **Payment Mode** | Razorpay Test Mode (`rzp_test_...`) | Razorpay Live Mode (`rzp_live_...`) |
| **OAuth Scope** | Authorized Local Redirects | Verified Production Domain |

---

## 7. Verification Commands Executed

All commands below have been executed directly on the project and exited with code 0:

```powershell
# 1. Run Session Persistence, Logout & Admin Security tests
pytest -v tests/test_session_and_security.py
# Result: 11 passed in 3.15s

# 2. Run Playwright Browser Logout & Back-Button Regression test
pytest -v tests/test_playwright_logout_regression.py
# Result: 1 passed in 9.19s

# 3. Run the full Pytest test suite
pytest -v tests/
# Result: 176 passed in 61.17s

# 4. Run the legacy integration test suite
python ecommerce_practical10/test_app.py
# Result: 37 tests passed (OK) in 7.32s

# 5. Run full Playwright browser verification & screenshot generation
python run_playwright_verification.py
# Result: 25 verified screenshots saved in artifacts/deployment/screenshots/
```
