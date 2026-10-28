# NexusMart — Faculty Demonstration Guide & Oral Defense Manual

**Course / Subject:** Software Engineering Practicals (BTCO13702)  
**Project Name:** NexusMart E-Commerce Platform  
**Architecture:** Python 3.10+ / Flask, SQLite (Local Dev) / PostgreSQL (Prod), Vanilla CSS, Razorpay Test Mode, Google OAuth 2.0 / OIDC  
**Verified Local Server:** `http://127.0.0.1:5000`  
**Health Check URL:** `http://127.0.0.1:5000/healthz`  
**Dedicated Admin Login:** `http://127.0.0.1:5000/admin/login`  

---

## 1. Project Overview & Major Architecture Features

NexusMart is a production-grade, transactional e-commerce platform built to demonstrate core Software Engineering principles:
- **Customer Journey:** User registration, credential authentication, profile management with multi-address book, dynamic product catalog with multi-filter search, shopping cart with stock-boundary protection, promotional discount engine, and digital order invoicing.
- **Payment Gateway Integration:** Official Razorpay Standard Checkout in Test Mode with server-side HMAC-SHA256 signature verification, simulated test payments, invalid signature rejection, and order status tracking.
- **Enterprise Security:** Cryptographic password hashing (scrypt/PBKDF2), CSRF token validation on all state-changing POST requests, session-based role verification (`@login_required`, `@admin_required`) with active database lookups on every request, explicit cookie deletion on logout, and strict HTTP `no-cache, no-store` headers to prevent back-forward cache (`bfcache`) leakage.
- **Administrator Operations Portal:** Dedicated dashboard with live KPIs (gross revenue, lifetime orders, catalog count, low-stock warnings), product inventory CRUD, direct warehouse stock adjustments, order fulfillment status transitions, and promo coupon management.
- **Automated Verification:** 213 automated tests (176 Pytest + 37 legacy unittest) with 100% pass rate, plus Playwright Chromium browser automation capturing 25 verified screenshots across desktop and mobile viewports.

---

## 2. Prerequisites & Local Environment Setup

### 2.1 System Requirements
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Operating System: Windows, macOS, or Linux
- Web Browser: Google Chrome, Microsoft Edge, Mozilla Firefox, or Safari
- Git installed on PATH

### 2.2 Installation Commands
Open a terminal in the project root directory (`d:/AI-Workspace/projects/e-commerce-web`):

```bash
# 1. (Optional but recommended) Create and activate a Python virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# 2. Install application dependencies
pip install -r ecommerce_practical10/requirements.txt

# 3. Install test suite dependencies (pytest, playwright)
pip install pytest playwright
playwright install chromium
```

### 2.3 Environment Configuration (`.env`)
The project comes with a safe `.env.example` template. For local demonstration:
```bash
# Windows PowerShell:
Copy-Item .env.example .env
# Linux/macOS:
cp .env.example .env
```

Generate a secure, random secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Configure your `.env` with local development settings:
```ini
FLASK_ENV=development
FLASK_DEBUG=0
FLASK_SECRET_KEY=<paste_your_generated_secret_here>
APP_BASE_URL=http://127.0.0.1:5000

# Razorpay Test Mode Configuration
RAZORPAY_KEY_ID=rzp_test_mockkey123
RAZORPAY_KEY_SECRET=rzp_test_secret_mock456
ENABLE_MOCK_PAYMENT=true
MOCK_RAZORPAY=true

# Google OAuth 2.0 (Optional for Local Demo - password login works out of the box)
# GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
# GOOGLE_CLIENT_SECRET=your-client-secret
```

---

## 3. Database Initialization & Safety

The SQLite database file is located at `ecommerce_practical10/ecommerce.db`.
- **Preservation:** The database is already pre-seeded with 10 demonstration products, active discount coupons (`WELCOME10`, `FLAT200`), and sample customer records.
- **Safe Initialization:** The schema initializes automatically when `app.py` boots. It does **not** overwrite or erase existing orders or accounts.
- **Verification Command:**
  ```bash
  python -c "import sqlite3; c=sqlite3.connect('ecommerce_practical10/ecommerce.db'); print('Products:', c.execute('SELECT COUNT(*) FROM products').fetchone()[0]); c.close()"
  ```

---

## 4. How to Start, Stop & Health-Check the Application

### 4.1 Starting the Server
Run from the application folder:
```bash
cd ecommerce_practical10
python app.py
```
Output will confirm:
```text
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

### 4.2 Verifying Server Health
Open another terminal or browser tab:
```bash
curl http://127.0.0.1:5000/healthz
```
Expected response:
```json
{"database": "connected", "service": "NexusMart Web", "status": "healthy"}
```

### 4.3 Stopping & Restarting
- To stop: Press `Ctrl + C` in the running terminal.
- To restart: Re-run `python app.py`.

---

## 5. Step-by-Step Customer Demonstration Sequence

Follow this exact path during your faculty oral presentation:

### Step 1: Open the Homepage & Catalog
1. Open your browser to `http://127.0.0.1:5000`.
2. Point out:
   - Modern, responsive dark-mode navbar with brand identity and live cart counter pill.
   - Hero banner highlighting curated electronics, audio gear, and accessories.
   - Featured products grid with high-resolution imagery and Indian Rupee (₹) pricing.
3. Click **Products** in the top navigation:
   - Demonstrate category filtering (e.g., select "Audio").
   - Demonstrate keyword search (e.g., search "Noise").
   - Demonstrate price filtering (e.g., Min: ₹1000, Max: ₹5000).
   - Click "Clear Filters" to reset.

### Step 2: Product Details & Cart Boundary Validation
1. Click on the **Sony WH-1000XM5 Wireless Headphones** card.
2. Note the stock indicator badge (`In Stock (25 available)`).
3. Try entering an invalid quantity (e.g., `999` or `-5`) and show how client and server-side validation safely restrict additions.
4. Select quantity `1` and click **Add to Cart**.
5. The shopping cart opens automatically, displaying the item, subtotal, and updated navbar cart pill.
6. Increase the quantity to `2` and click **Update Cart**; observe instant subtotal recalculation.

### Step 3: Customer Registration & Login
1. Click **Sign In** in the navigation bar.
2. Click **Create an account** to show the registration form:
   - Note the password validation indicators and duplicate email prevention.
3. Register a demonstration account (e.g., `faculty_demo@nexusmart.com` / `DemoPass123!`).
4. Log in with the new credentials.
5. The **Customer Dashboard** opens:
   - Point out personal welcome greeting (`Welcome back, Faculty Demo`).
   - Highlight **AI-Powered Product Recommendations** tailored to the customer.

### Step 4: Address Management & Checkout Review
1. Go to **Profile** from the navigation menu:
   - Add a delivery address (e.g., `Flat 402, Tech Park Avenue, Pune, Maharashtra - 411001`).
   - Note the automatic "Default Address" badge assignment.
2. Return to **Cart** and click **Proceed to Checkout**:
   - The Checkout Review screen displays the selected delivery address.
   - Apply promotional discount coupon `WELCOME10`:
     - Show the instant 10% discount calculation and updated payable total.

### Step 5: Razorpay Test Mode Payment
1. Select **Online Payment (Credit / Debit Card / UPI via Razorpay)**.
2. Click **Proceed to Payment**:
   - The official Razorpay Standard Checkout launch modal opens.
   - Point out the order reference, amount in INR, and secure test encryption badge.
3. Enter Razorpay Test credentials:
   - Phone: `9876543210`
   - Test Card: `4111 1111 1111 1111`, Expiry: `12/28`, CVV: `123`
   - Click **Pay Now** -> Complete simulated OTP (`123456`).
4. The application processes the server-side HMAC-SHA256 signature and renders the **Order Confirmation Invoice**:
   - Displays unique Order Reference (e.g., `ORD-20261028-XXXX`), delivery destination, itemized breakdown, and status **Paid**.
5. Navigate to **Order History** and click **View Details** to display the permanent, immutable order snapshot.

---

## 6. Verifying Logout & Session Defenses (Priority 1 Demonstration)

Demonstrate the resolved session persistence flaw to the faculty:

1. With the customer logged in on `http://127.0.0.1:5000/dashboard`, click **Logout** in the navigation bar.
2. Observe immediate redirection to `/login` with flash message: `You have been logged out successfully.`
3. **Press the Browser "Back" Button:**
   - Observe that the browser does **not** keep the user logged in.
   - The `pageshow` listener detects back-forward navigation and triggers a re-evaluation against the server.
   - The server inspects the request, finds no active session cookie, and maintains the unauthenticated state.
4. **Direct URL Navigation Test:**
   - Type `http://127.0.0.1:5000/dashboard` directly into the URL bar and press Enter.
   - Type `http://127.0.0.1:5000/orders` directly into the URL bar and press Enter.
   - In both cases, the server immediately redirects to `/login` with: `Please log in to access this page.`

---

## 7. Administrator Demonstration & Account Setup

### 7.1 Dedicated Admin Login
- **Admin Login URL:** `http://127.0.0.1:5000/admin/login`
- The portal has dedicated operator branding and enforces `@admin_required` server-side check (`is_admin == 1`).

### 7.2 Administrator Credentials & Reset Procedure
If you need to set or reset the password for the administrator account before your demonstration, use the interactive CLI prompt (which uses Python's secure `getpass` to prevent passwords from being stored in your shell history):

```bash
# Interactive password reset (recommended):
python manage_admin.py reset-password admin@nexusmart.com
```

Alternatively, if running non-interactively:
```bash
python manage_admin.py reset-password admin@nexusmart.com --password "<YourSecureAdminPassword>"
```

### 7.3 Admin Demonstration Steps
1. Navigate to `http://127.0.0.1:5000/admin/login`.
2. Log in with `admin@nexusmart.com` and the password you set above.
3. You are redirected to the **NexusMart Operations Dashboard** (`/admin/dashboard`):
   - Review live KPIs: **Gross Revenue (₹)**, **Total Orders**, **Catalog Count**, and **Inventory Alerts**.
4. Click **Product Management** (`/admin/products`):
   - Demonstrate direct stock adjustments (e.g., increase or decrease warehouse inventory by 5 units).
   - Show how stock updates immediately reflect in the public catalog.
5. Click **Order Fulfillment** (`/admin/orders`):
   - Locate the order placed during the customer demo.
   - Update its fulfillment status from `Confirmed` -> `Processing` -> `Shipped`.
6. Click **Coupons & Promos** (`/admin/coupons`):
   - Show active coupons (`WELCOME10`, `FLAT200`).
   - Create a new demonstration promo coupon (e.g., `FACULTY25` for 25% off).
7. Click **Admin Logout**:
   - Session is destroyed, cookie expired, and user returned to admin login.

---

## 8. Command-Line Administrator Management (`manage_admin.py`)

Show faculty that administrator accounts are governed by a secure CLI rather than insecure public registration:

```bash
# 1. Safely list all administrators (emails are masked to protect PII)
python manage_admin.py list

# 2. Promote an existing registered customer to Administrator
python manage_admin.py promote customer@nexusmart.com

# 3. Demote an administrator back to regular customer
python manage_admin.py demote former_admin@nexusmart.com
# (Note: Built-in safety check prevents demoting the last remaining admin)

# 4. Create a new administrator account directly
python manage_admin.py create --name "Demo Admin" --email "demoadmin@nexusmart.com" --password "AdminPass123!"
```

---

## 9. Common Demonstration Questions & Answers (Defense Prep)

**Q1: How does the system prevent double-spending or overselling of stock?**  
*Answer:* NexusMart utilizes atomic transactions with SQLite's `BEGIN IMMEDIATE` (and row-level `SELECT ... FOR UPDATE` in PostgreSQL). When an order is placed, stock availability is re-verified inside the lock. If available, stock is deducted and the order is committed simultaneously. If any step fails, the entire transaction rolls back.

**Q2: What happens if a customer manipulates the order amount in their browser?**  
*Answer:* The client-side amount is completely ignored. The final payable amount is recomputed from the database product unit prices, active cart quantities, and validated coupon logic on the server right before initiating payment.

**Q3: How does NexusMart verify Razorpay payments?**  
*Answer:* We compute `HMAC-SHA256(razorpay_order_id + "|" + razorpay_payment_id, RAZORPAY_KEY_SECRET)` on the server and compare it against the client's `razorpay_signature` using constant-time comparison (`hmac.compare_digest`). Orders can never be marked paid without a cryptographically verified signature.

**Q4: How was the logout back-button problem fixed?**  
*Answer:* We implemented an `@app.after_request` handler that injects `Cache-Control: no-cache, no-store, must-revalidate, private`, `Pragma: no-cache`, and `Expires: 0` headers on all sensitive routes, coupled with an explicit cookie expiration header on logout and a front-end `pageshow` reload listener to invalidate modern browser Back/Forward Cache (`bfcache`).
