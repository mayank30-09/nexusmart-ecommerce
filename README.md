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

### 6. Production Security & Quality Assurance
- Anti-CSRF protection across all state-changing `POST` routes with session-scoped cryptographically strong tokens.
- Secure HTTP headers, `SameSite=Lax`, `HttpOnly` cookie settings, and custom 404/500 error pages without revealing stack traces.
- Zero committed secrets: complete isolation through environment variables (`.env.example`).
- Health check monitoring endpoint (`/healthz`).

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
│   ├── templates/                # Jinja2 Customer-Facing Templates
│   │   ├── base.html             # Common Shell, Navbar with Live Cart Pill, Footer
│   │   ├── login.html            # Customer Login (Local & Google OAuth)
│   │   ├── register.html         # Customer Registration
│   │   ├── dashboard.html        # Customer Portal Dashboard
│   │   ├── products.html         # Catalog with Search & Filter
│   │   ├── product_detail.html   # Product View with Specs & Add to Cart
│   │   ├── cart.html             # Shopping Cart Review
│   │   ├── checkout.html         # Checkout, Address & Promo Engine
│   │   ├── razorpay_checkout.html# Official Razorpay Standard Checkout Modal
│   │   ├── order_confirmation.html# Order Confirmation & Receipt Invoice
│   │   ├── orders.html           # Customer Order History Table
│   │   ├── order_detail.html     # Order Itemization & Cancellation
│   │   ├── profile.html          # Profile & Delivery Address CRUD
│   │   ├── about.html            # Brand & Platform Architecture
│   │   ├── contact.html          # Customer Support & Help Desk
│   │   ├── privacy.html          # Privacy Policy
│   │   ├── terms.html            # Terms of Service
│   │   ├── 404.html              # Custom Not Found Error Page
│   │   └── 500.html              # Custom Server Error Page
│   └── static/                   # Static Styling & Design System
│       └── style.css             # Vanilla CSS Responsive Design System
├── docs/                         # Software Engineering Course Deliverables
│   ├── SRS_TRACEABILITY_MATRIX.md# Full Requirements Traceability (FR-01 to FR-21, NFRs)
│   ├── DEPLOYMENT_AND_CONFIGURATION.md # Production Deployment Guide (Render, GCP, Razorpay)
│   └── KNOWN_LIMITATIONS.md      # Operational Boundaries & Security Audit Notes
├── artifacts/deployment/         # QA & Automated Verification Evidence
│   ├── screenshots/              # 19 Verified Playwright Screenshots (Desktop & Mobile)
│   └── reports/                  # JSON Test Reports & Screenshot Inventory
├── tests/                        # Automated Pytest & Unittest Test Suites
│   ├── conftest.py               # Temporary DB Fixtures & Shared Test Base
│   ├── test_auth.py              # Authentication & Google OAuth Tests
│   ├── test_products.py          # Catalog, Search & Filtering Tests
│   ├── test_cart.py              # Cart Management & Boundary Tests
│   ├── test_profile_addresses.py # Profile & Address Book CRUD Tests
│   ├── test_checkout_discounts.py# Checkout Review & Coupon Engine Tests
│   ├── test_orders_payments.py   # Order Placement & Transaction Tests
│   └── test_razorpay_checkout.py # Razorpay Signature, Failure & Webhook Tests
├── run_playwright_verification.py# End-to-End Real Browser Automation Script
├── Procfile                      # Gunicorn Deployment Definition for Render/Heroku
└── requirements.txt              # Top-Level Dependency Manifest
```

---

## ⚙️ Environment Variables Reference

NexusMart requires the following configuration variables in production:

| Variable | Sensitivity | Environment | Description |
|---|---|---|---|
| `FLASK_SECRET_KEY` | **High** (Secret) | All | Cryptographic secret for signing session cookies and CSRF tokens. Generate using `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `DATABASE_URL` | **High** (Secret) | Production | PostgreSQL connection URI (e.g., `postgresql://user:pass@host:5432/dbname`). If omitted, defaults to SQLite `ecommerce.db`. |
| `APP_BASE_URL` | Low (Public) | Production | Canonical public HTTPS URL (e.g., `https://nexusmart.onrender.com`). Used for exact OAuth callback URI and return links. |
| `GOOGLE_CLIENT_ID` | Low (Public) | Production | Google Cloud OAuth 2.0 Web Client ID (ending in `.apps.googleusercontent.com`). |
| `GOOGLE_CLIENT_SECRET` | **High** (Secret) | Production | Google Cloud OAuth 2.0 Client Secret from GCP Console. |
| `RAZORPAY_KEY_ID` | Low (Public) | Production | Razorpay API Key ID (e.g., `rzp_test_...` for test mode). Shared with frontend checkout modal. |
| `RAZORPAY_KEY_SECRET` | **High** (Secret) | Production | Razorpay API Secret Key used strictly server-side for HMAC signature verification. |
| `RAZORPAY_WEBHOOK_SECRET` | **High** (Secret) | Production | Secret configured in Razorpay Dashboard for webhook payload signature validation. |

---

## 🧪 Testing & Verification

NexusMart includes 172 automated unit, integration, and regression tests, plus 19 live browser Playwright scenarios.

### 1. Run Complete Pytest Suite (135 Tests)
```bash
pytest -v tests/
```
*Executes all unit, boundary, authentication, address, discount, order, and Razorpay tests against an isolated temporary database.*

### 2. Run Legacy Practical Suite (37 Tests)
```bash
python test_app.py
```
*Validates backward-compatibility with original Practical 10 requirements.*

### 3. Run Real Playwright Browser Verification
```bash
python run_playwright_verification.py
```
*Launches headless Chromium, navigates all 8 customer journeys across Desktop (1440×900) and Mobile (390×844) viewports, tests payment signature verification and rejection, and saves 19 screenshot artifacts to `artifacts/deployment/screenshots/`.*

---

## 🚢 Production Deployment (Render)

1. **Push repository to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "feat: complete NexusMart production release"
   git remote add origin https://github.com/your-username/nexusmart.git
   git push -u origin main
   ```
2. **Create Managed PostgreSQL Database on Render:**
   - Go to [dashboard.render.com](https://dashboard.render.com) &rarr; **New +** &rarr; **PostgreSQL**.
   - Copy the **Internal Database URL**.
3. **Create Web Service on Render:**
   - Select your GitHub repository.
   - Runtime: `Python 3`.
   - Build Command: `pip install -r ecommerce_practical10/requirements.txt`.
   - Start Command: `gunicorn --chdir ecommerce_practical10 wsgi:app`.
   - Add Environment Variables: `DATABASE_URL`, `FLASK_SECRET_KEY`, `APP_BASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`.
4. **Configure Google Cloud Console OAuth:**
   - Add Authorized Redirect URI: `https://<your-render-subdomain>.onrender.com/auth/google/callback`.
5. **Configure Razorpay Webhook:**
   - Add Webhook URL: `https://<your-render-subdomain>.onrender.com/webhooks/razorpay`.
   - Active Event: `order.paid`.

---

## 📚 Course Documentation & Practical Files
- [SRS Traceability Matrix](file:///docs/SRS_TRACEABILITY_MATRIX.md)
- [Production Deployment & Configuration Guide](file:///docs/DEPLOYMENT_AND_CONFIGURATION.md)
- [Known Limitations & Security Audit](file:///docs/KNOWN_LIMITATIONS.md)
- [Playwright Screenshot Inventory](file:///artifacts/deployment/reports/screenshot_inventory.md)
- [Black-Box & White-Box Test Cases](file:///test_results/black_box_test_cases.md)
