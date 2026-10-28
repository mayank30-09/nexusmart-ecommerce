# NexusMart — Enterprise E-Commerce Platform

NexusMart is a modern, full-stack, transactional e-commerce platform developed with Python, Flask, SQLite/PostgreSQL dual-dialect persistence, Vanilla CSS responsive design system, official Razorpay Standard Checkout, and Google OAuth 2.0 / OIDC authentication.

Originally conceived as a Software Engineering course practical project, NexusMart has been systematically refactored into a commercial-grade, production-deployable e-commerce web platform aligned with university Software Engineering syllabus requirements (BTCO13702), Pressman SQA principles, and enterprise security standards.

---

## 🚀 Key Features

### 1. Customer Authentication & Profile Management
- **Local Authentication:** Account registration with regex email validation, minimum 6-character passwords, parity checks, duplicate email prevention, and `PBKDF2/SHA-256` salted password hashing.
- **Google OAuth 2.0 / OpenID Connect:** Cryptographic anti-forgery `state` parameter validation, automatic redirect URI generation with `APP_BASE_URL` reverse-proxy support, official Google token signature validation (`google.oauth2.id_token.verify_oauth2_token`), and password-protected safe account linking.
- **Profile & Address Book:** Full CRUD for customer delivery destinations with active default address selection and automatic address switching during checkout.

### 2. Product Catalog, Search & Details
- **Dynamic Catalog:** Multi-criteria filtering by keyword, product category, and price range with parameterized SQL queries preventing SQL injection.
- **Product Details:** Item specifications, inventory counters, responsive breadcrumbs, category badges, dynamic stock level warnings, and quantity validation.
- **INR Currency Formatting:** All prices consistently displayed in Indian Rupees (₹).

### 3. Shopping Cart, Checkout & Discount Engine
- **Persistent Cart:** Customer-isolated cart persistence, warehouse stock boundary enforcement, in-cart quantity modifiers, line item deletion, and full cart clearing.
- **Coupon & Promo Engine:** Promo validation supporting percentage discounts (e.g., `WELCOME10` - 10% off on ₹500+) and fixed value coupons (e.g., `FLAT200` - ₹200 off on ₹1000+) with minimum cart thresholds and concurrency-safe usage caps.
- **Transactional Consistency:** Atomic stock validation, coupon evaluation, and idempotency protection against duplicate submissions.

### 4. Official Razorpay Payment Integration
- **Razorpay Standard Checkout:** Official Razorpay client order generation (`amount_in_paise`, currency INR), pending state creation, and client modal launch.
- **Cryptographic Verification:** Server-side HMAC-SHA256 signature verification matching `razorpay_order_id|razorpay_payment_id` against `RAZORPAY_KEY_SECRET`.
- **Payment Failure & Cancellation:** Customer cancellation and invalid signature handling with complete cart and inventory preservation.
- **Webhook Endpoint:** Dedicated `/webhooks/razorpay` endpoint with raw-body signature validation and replay deduplication via `processed_webhooks` table.

### 5. Multi-Database Architecture (SQLite + PostgreSQL)
- **Universal Database Engine (`database.py`):** Seamless automatic switching between SQLite (local testing and development) and PostgreSQL (production deployment on Render, Neon, Supabase, or AWS RDS).
- **PostgresCursorWrapper:** Automatic SQL parameter translation (`?` to `%s`), dictionary-like column access (`row["col"]`), and transactional safety.

### 6. Admin Operations Portal & Staff Controls
- **Privileged Access (`/admin/login`):** Role-based access control with `@admin_required` decorator enforcing administrative privileges (`is_admin=1`).
- **Live Operations Dashboard (`/admin/dashboard`):** Real-time monitoring of Gross Revenue, Lifetime Orders, Total Catalog Size, and Low-Stock Warehouse Alerts.
- **Product & Stock Management (`/admin/products`):** Full catalog CRUD and direct inventory stock adjustments.
- **Order Lifecycle Fulfillment (`/admin/orders`):** Order status transitions (`Confirmed` -> `Processing` -> `Shipped` -> `Delivered`) and strict cancellation lock enforcement (`BR-04`).
- **Coupon Management (`/admin/coupons`):** Promotional discount creation and instant status activation/deactivation.

### 7. AI-Powered Product Recommendations (FR-16)
- Multi-tier recommendation engine analyzing customer purchase history, browsing category affinity, and catalog popularity fallbacks on customer dashboards and product detail views.

---

## 📂 Project Architecture

```text
d:/AI-Workspace/projects/e-commerce-web/
├── ecommerce_practical10/        # Core Flask Application Root
│   ├── app.py                    # Main Application Controllers & Routes
│   ├── database.py               # Dual-Engine Database Abstraction (SQLite / PostgreSQL)
│   ├── wsgi.py                   # Production WSGI Application Entry Point
│   ├── requirements.txt          # Pinned Application Dependencies
│   ├── .env.example              # Environment Configuration Template
│   ├── templates/                # Jinja2 Customer & Admin Templates
│   │   ├── base.html             # Common Shell, Navbar with Live Cart Pill, Footer
│   │   ├── login.html            # Customer Login (Local & Google OAuth)
│   │   ├── register.html         # Customer Registration
│   │   ├── dashboard.html        # Customer Dashboard with AI Recommendations
│   │   ├── products.html         # Catalog with Search & Filter
│   │   ├── product_detail.html   # Product View with Specs & Add to Cart
│   │   ├── cart.html             # Shopping Cart Review
│   │   ├── checkout.html         # Checkout, Address & Promo Engine
│   │   ├── razorpay_checkout.html# Official Razorpay Standard Checkout Modal
│   │   ├── order_confirmation.html# Order Confirmation & Receipt Invoice
│   │   ├── orders.html           # Customer Order History Table
│   │   ├── order_detail.html     # Order Itemization & Cancellation
│   │   ├── profile.html          # Profile & Delivery Address CRUD
│   │   ├── admin_login.html      # Administrator Authentication Portal
│   │   ├── admin_dashboard.html  # Admin Operations & Live KPI Dashboard
│   │   ├── admin_products.html   # Admin Catalog CRUD & Stock Adjustments
│   │   ├── admin_orders.html     # Admin Customer Orders & Status Controls
│   │   ├── admin_coupons.html    # Admin Promo Coupon Management
│   │   ├── about.html            # Brand & Platform Architecture
│   │   ├── contact.html          # Customer Support & Help Desk
│   │   ├── privacy.html          # Privacy Policy
│   │   ├── terms.html            # Terms of Service
│   │   ├── 404.html              # Custom Not Found Error Page
│   │   └── 500.html              # Custom Server Error Page
│   └── static/                   # Static Styling & Design System
│       └── style.css             # Vanilla CSS Responsive Design System
├── docs/                         # Software Engineering Course Deliverables
│   ├── SRS_TRACEABILITY_MATRIX.md# Full Requirements Traceability (FR-01 to FR-21, BR-01 to BR-06)
│   ├── DEPLOYMENT_AND_CONFIGURATION.md # Production Deployment Guide (Render, GCP, Razorpay)
│   └── KNOWN_LIMITATIONS.md      # Operational Boundaries & Security Audit Notes
├── artifacts/deployment/         # QA & Automated Verification Evidence
│   ├── screenshots/              # 25 Verified Playwright Screenshots (Desktop & Mobile)
│   └── reports/                  # JSON Test Reports & Screenshot Inventory
├── tests/                        # Automated Pytest & Unittest Test Suites
│   ├── conftest.py               # Temporary DB Fixtures & Shared Test Base
│   ├── test_auth.py              # Authentication & Google OAuth Tests
│   ├── test_products.py          # Catalog, Search & Filtering Tests
│   ├── test_cart.py              # Cart Management & Boundary Tests
│   ├── test_profile_addresses.py # Profile & Address Book CRUD Tests
│   ├── test_checkout_discounts.py# Checkout Review & Coupon Engine Tests
│   ├── test_orders_payments.py   # Order Placement & Transaction Tests
├── manage_admin.py           # Standalone Administrator CLI Management Tool
│   ├── test_razorpay_checkout.py # Razorpay Signature, Failure & Webhook Tests
│   ├── test_admin_and_recommendations.py # Admin Portal & AI Recommendation Tests
│   ├── test_session_and_security.py # Session Persistence, Invalidation & Admin RBAC Tests
│   └── test_playwright_logout_regression.py # Playwright Browser Logout & Back-Button Test
├── run_playwright_verification.py# End-to-End Real Browser Automation Script
├── Procfile                      # Gunicorn Deployment Definition for Render/Heroku
└── requirements.txt              # Top-Level Dependency Manifest
```

---

## 🛠️ Local Startup & Execution

### 1. Start the Local Server
```bash
cd ecommerce_practical10
python app.py
```
The server will boot at `http://127.0.0.1:5000`.

### 2. Verify Server Health
```bash
curl http://127.0.0.1:5000/healthz
# Returns: {"database": "connected", "service": "NexusMart Web", "status": "healthy"}
```

### 3. Administrator CLI Management (`manage_admin.py`)
Administrator accounts are managed securely via command line:
```bash
# List existing administrators (emails masked for privacy)
python manage_admin.py list

# Reset an administrator password securely (interactive prompt):
python manage_admin.py reset-password admin@nexusmart.com

# Promote an existing customer to Administrator
python manage_admin.py promote user@example.com

# Demote an Administrator (with protection against demoting the sole remaining admin)
python manage_admin.py demote user@example.com

# Create a new Administrator directly
python manage_admin.py create --name "Demo Admin" --email "demo@nexusmart.com"
```

Dedicated Admin Login Portal: `http://127.0.0.1:5000/admin/login`

---

## ⚙️ Environment Variables Reference

NexusMart requires the following configuration variables:

| Variable | Sensitivity | Environment | Description |
|---|---|---|---|
| `FLASK_SECRET_KEY` | **High** (Secret) | All | Cryptographic secret for signing session cookies and CSRF tokens. |
| `DATABASE_URL` | **High** (Secret) | Production | PostgreSQL connection URI. If omitted, defaults to local SQLite `ecommerce.db`. |
| `APP_BASE_URL` | Low (Public) | Production | Canonical public URL (e.g., `http://127.0.0.1:5000` or `https://nexusmart.onrender.com`). |
| `GOOGLE_CLIENT_ID` | Low (Public) | Production | Google Cloud OAuth 2.0 Web Client ID. |
| `GOOGLE_CLIENT_SECRET` | **High** (Secret) | Production | Google Cloud OAuth 2.0 Client Secret. |
| `RAZORPAY_KEY_ID` | Low (Public) | All | Razorpay API Key ID (`rzp_test_...` for test mode). |
| `RAZORPAY_KEY_SECRET` | **High** (Secret) | All | Razorpay API Secret Key used strictly server-side for signature verification. |
| `ENABLE_MOCK_PAYMENT` | Low | Development | Enables built-in Razorpay Test simulation (`true` for local demo). |

---

## 🧪 Testing & Verification

NexusMart includes **213 automated tests** (176 Pytest + 37 Unittest) with a **100% pass rate**, plus **25 live browser Playwright scenarios**.

### 1. Run Complete Pytest Suite (176 Tests)
```bash
pytest -v tests/
```
*Executes all unit, boundary, authentication, session invalidation, address, discount, order, Razorpay, Admin portal, and AI recommendation tests against an isolated temporary database.*

### 2. Run Browser Logout Regression Test
```bash
pytest -v tests/test_playwright_logout_regression.py
```
*Launches real Chromium browser, verifies session destruction on logout, Back-button cache re-evaluation, and direct URL rejection.*

### 3. Run Legacy Practical Suite (37 Tests)
```bash
python ecommerce_practical10/test_app.py
```
*Validates backward-compatibility with original Practical 10 requirements.*

### 4. Run Real Playwright Browser Verification (25 Screenshots)
```bash
python run_playwright_verification.py
```
*Launches Chromium, exercises all customer journeys and admin operations across Desktop (1440×900) and Mobile (390×844) viewports, tests payment signature verification and rejection, and saves 25 verified screenshot artifacts to `artifacts/deployment/screenshots/`.*

---

## 📚 Course Documentation & Demonstration Manuals
- **[Faculty Demonstration Guide](docs/FACULTY_DEMO_GUIDE.md)**: Step-by-step walkthrough for faculty evaluation and viva defense.
- **[Final QA & Security Audit Report](docs/FINAL_QA_REPORT.md)**: Full verification metrics, root causes, defect classifications, and fixes.
- **[Demo Test Checklist](docs/DEMO_TEST_CHECKLIST.md)**: Concise quick-reference checklist for the live presentation.
- **[SRS Traceability Matrix](docs/SRS_TRACEABILITY_MATRIX.md)**: Full requirements traceability (FR-01 to FR-21, BR-01 to BR-06).
- **[Production Deployment & Configuration Guide](docs/DEPLOYMENT_AND_CONFIGURATION.md)**: Production deployment guide (Render, GCP, Razorpay).
- **[Known Limitations & Security Audit](docs/KNOWN_LIMITATIONS.md)**: Operational boundaries and security audit notes.
- **[Playwright Screenshot Inventory](artifacts/deployment/reports/screenshot_inventory.md)**: Visual catalog of 25 captured screenshots.

