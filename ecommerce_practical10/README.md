# E-Commerce Website - Practical-10 Implementation

A lightweight, complete, and fully functional college mini-project implementation of an **E-Commerce Web Application** built from scratch using **Python (Flask)**, **SQLite**, and **HTML5/CSS3**.

This project implements **3 core modules** designed in prior software engineering practicals (Practical-3 Requirements, Practical-4 SRS, Practical-5 UML, Practical-6 DFD, and Practical-7 Structure Chart):
1. **Module 1**: Customer Registration / Authentication
2. **Module 2**: Product Search / Filtering
3. **Module 3**: Cart Management

---

## 1. Project Information & Traceability

- **Project Name:** E-Commerce Website (Mini-Project)
- **Practical:** Practical-10
- **Aim:** "Perform implementation of any 3 modules from the modules you have designed."
- **Traceability Mapping:**
  - **DFD Process 1.0 (Customer Management)** $\rightarrow$ **Module 1: Customer Registration & Authentication**
  - **DFD Process 2.0 (Product Catalog & Search)** $\rightarrow$ **Module 2: Product Search & Filtering**
  - **DFD Process 3.0 (Shopping Cart)** $\rightarrow$ **Module 3: Cart Management**

---

## 2. Technology Stack

- **Backend Framework:** Python 3.14 + Flask 3.1
- **Authentication & OAuth:** Google OAuth 2.0 / OpenID Connect (`google-auth`, `requests`, `python-dotenv`) + Werkzeug Password Hashing
- **Database:** SQLite 3 (`ecommerce.db`) with Foreign Keys enabled (`PRAGMA foreign_keys = ON;`)
- **Security:** Official Google ID token validation (cryptographic signature, issuer, audience, expiry, verified email check), CSRF anti-forgery state tokens, safe account linking, session management (`login_required` decorator), parameterized SQL queries (preventing SQL injection)
- **Frontend:** Semantic HTML5 + Custom Vanilla CSS3 (clean, responsive student-project UI with official Google Sign-In button)
- **Automated Testing:** Python `unittest` test suite with 37 test cases (`test_app.py`)
- **Browser Automation:** Playwright Chromium (`capture_screenshots.py`)

---

## 3. Implemented Modules Overview

### Module 1: Customer Registration / Authentication
- **Customer Registration:**
  - Fields: Full Name, Email, Password, Confirm Password.
  - Validations: Required fields, regex-based email format, minimum 6-character password, password matching check.
  - Duplicate detection: Prevents multiple registrations with the same email.
  - Security: Passwords stored as secure cryptographic hashes using `werkzeug.security`.
- **Google Authentication (Sign in with Google):**
  - **Sign in with Google button** integrated into Login and Register pages.
  - **Official OAuth 2.0 Flow:** Secure redirect to Google accounts authorization endpoint with CSRF anti-forgery state token.
  - **Cryptographic Token Verification:** Validates Google ID token via `google.oauth2.id_token.verify_oauth2_token` (signature, issuer `accounts.google.com`, client audience, expiry, `email_verified=True`).
  - **Customer Auto-Creation:** Automatically creates new customer accounts in SQLite upon first-time Google sign-in (`google_id`, `name`, `email`, `password_hash=NULL`).
  - **Returning Customer Login:** Automatically recognizes existing `google_id` and restores session.
  - **Safe Account-Linking:** If a Google email matches an existing local password-based account, automatic merging is safely prevented. The user is prompted to verify their existing password at `/auth/google/link` before linking.
  - **Account Status in Dashboard:** Real-time badge indicating whether Google account is connected.
- **Customer Login:**
  - Supports both traditional Email/Password login and Google Sign-In.
  - Creates secure HTTP session storing `customer_id`, `customer_name`, `customer_email`, and `auth_provider`.
  - Flash error alerts for invalid credentials, unverified accounts, or cancelled Google flows.
- **Customer Logout:**
  - Clears active session (`session.clear()`) and redirects to login for both local and Google authenticated users.
- **Customer Dashboard:**
  - Personalized welcome message with customer name and email.
  - Live statistics: Catalog product count and customer's private cart items.
  - Direct quick navigation buttons to Products and Cart.

### Module 2: Product Search / Filtering
- **SQLite Products Catalog:**
  - Seed dataset of 10 products across 5 categories: *Electronics*, *Clothing*, *Footwear*, *Accessories*, *Bags*.
  - Fields: `id`, `name`, `category`, `price`, `stock`, `description`.
- **Search & Filtering Features:**
  - Search by product name keywords (`name LIKE ?`).
  - Filter by category via dropdown (`category = ?`).
  - Filter by minimum price (`price >= ?`).
  - Filter by maximum price (`price <= ?`).
  - Combine multiple filters simultaneously.
  - Clear Filters button to reset all criteria.
  - Empty state alert: "No products found" when search matches nothing.
  - Inline "Add to Cart" form on each product card with stock validation.

### Module 3: Cart Management
- **SQLite Cart Items Table:**
  - Fields: `id`, `customer_id`, `product_id`, `quantity`.
  - Enforced foreign keys referencing `customers(id)` and `products(id)` with cascade deletes.
- **Cart Operations:**
  - **Add to Cart:** Validates stock and adds item. If item already exists, increments quantity without creating duplicate rows.
  - **View Cart:** Shows item name, category, unit price, editable quantity input, item subtotal, and remove action.
  - **Update Quantity:** Dynamically adjusts quantity while preventing values higher than available stock.
  - **Remove Item:** Deletes a specific product from customer's cart.
  - **Clear Cart:** Wipes all items in the customer's cart in one click.
  - **Calculations:**
    - Item Subtotal: $\text{Product Price} \times \text{Quantity}$
    - Grand Cart Total: $\sum \text{Item Subtotals}$
  - **Data Isolation:** Queries strictly use `WHERE customer_id = session['customer_id']`, ensuring Customer A never views Customer B's cart.

---

## 4. Project File Structure

```
ecommerce_practical10/
├── app.py                      # Main Flask web application and routing
├── database.py                 # SQLite schema initialization and product seeding
├── test_app.py                 # Automated unit test suite (25 test cases)
├── capture_screenshots.py      # Playwright screenshot generator
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation and guide
├── Practical-10.md             # Formal university practical report
├── Practical-10.docx           # Formatted Word submission file
├── ecommerce.db                # Auto-generated SQLite database
├── static/
│   ├── style.css               # Clean responsive student-project stylesheet
│   └── screenshots/            # 11 authentic PNG screenshots of the app
│       ├── 01_registration_page.png
│       ├── 02_successful_registration.png
│       ├── 03_login_page.png
│       ├── 04_dashboard.png
│       ├── 05_product_list.png
│       ├── 06_product_search.png
│       ├── 07_product_filtering.png
│       ├── 08_product_added_to_cart.png
│       ├── 09_cart_page.png
│       ├── 10_updated_cart.png
│       └── 11_removed_product_final_cart.png
└── templates/
    ├── base.html               # Base layout with navbar, alerts, footer
    ├── register.html           # Customer registration form
    ├── login.html              # Customer login form
    ├── dashboard.html          # Customer dashboard & navigation
    ├── products.html           # Product catalog with search and filters
    └── cart.html               # Shopping cart with totals and quantity updates
```

---

## 5. Installation & Setup Instructions

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- `pip` package manager

### Step 1: Navigate to Project Directory
```bash
cd d:\AI-Workspace\projects\e-commerce-web\ecommerce_practical10
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables (.env)
Copy `.env.example` to create your local `.env` file:
```bash
cp .env.example .env      # On Linux/macOS
copy .env.example .env    # On Windows PowerShell / Command Prompt
```

Inside `.env`, configure your application secrets and Google OAuth keys:
```ini
FLASK_SECRET_KEY=your-random-secret-key-here
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback
```

> **Note:** If Google OAuth credentials are not provided, traditional email/password registration and login remain 100% functional, and automated tests use mock verification.

---

## 6. Google Cloud Console Setup (Step-by-Step)

To enable live Google Sign-In with real Google accounts:

1. **Open Google Cloud Console:**
   Navigate to [https://console.cloud.google.com/](https://console.cloud.google.com/) and sign in with your Google account.
2. **Create / Select Project:**
   Click the project dropdown in the top bar and click **New Project** (e.g. `ShopMini-Ecommerce`).
3. **Configure OAuth Consent Screen:**
   - Go to **APIs & Services** > **OAuth consent screen**.
   - Choose **External** user type and click **Create**.
   - Fill in:
     - **App name:** `ShopMini E-Commerce`
     - **User support email:** Your email address
     - **Developer contact information:** Your email address
   - In **Scopes**, add: `.../auth/userinfo.email`, `.../auth/userinfo.profile`, and `openid`.
   - In **Test users** (if app publishing status is *Testing*), add the Gmail addresses you will use for testing.
4. **Create OAuth Client ID:**
   - Go to **APIs & Services** > **Credentials**.
   - Click **+ Create Credentials** > **OAuth client ID**.
   - **Application type:** Select **Web application**.
   - **Name:** `ShopMini Web Client`.
   - **Authorized redirect URIs:** Click **+ Add URI** and enter:
     ```
     http://127.0.0.1:5000/auth/google/callback
     ```
   - Click **Create**.
5. **Save Credentials in `.env`:**
   Copy the generated **Client ID** and **Client Secret** into your `.env` file.

---

## 7. How to Run & Use the Application

### Run the Flask Application
```bash
python app.py
```

### Open in Web Browser
Navigate to:
```
http://127.0.0.1:5000
```

### User Workflow:
1. **Google Sign-In:**
   - On the login page, click **Sign in with Google**.
   - Authenticate with your Google account.
   - First-time users are automatically registered and redirected to the Dashboard.
   - Returning users are immediately logged in.
2. **Safe Account Linking:**
   - If an existing account already used that email with a local password, the app requires password verification before linking to prevent account hijacking.
3. **Traditional Registration & Login:**
   - Email/password registration and login remain available alongside Google Auth.
4. **Product Search & Filtering (Module 2):**
   - Search by name keyword, filter by category, minimum price, and maximum price.
5. **Cart Management (Module 3):**
   - Add items, edit quantities with real-time stock validation, calculate subtotals/totals, and isolate customer carts.
6. **Logout:**
   - Terminate active session via the Logout button.

---

## 8. Running Automated Tests

To execute the 37-case automated test suite verifying all required scenarios:

```bash
python test_app.py
```

**Expected Result:**
```
Ran 37 tests in ~6s
OK
```

All 37 test cases cover:
- **Registration Validation (5 tests):** Valid registration, empty fields, invalid email format, password mismatch, duplicate email.
- **Login & Session Management (3 tests):** Valid credentials, incorrect password, logout session termination.
- **Product Search & Filtering (8 tests):** Catalog display, keyword search, category filter, min/max price filters, combined filters, empty search state, clear filters.
- **Cart Management (9 tests):** Add product, increment existing item, update quantity, remove product, clear cart, stock overflow prevention, subtotal calculation, cart grand total, customer isolation.
- **Google Authentication & Security (12 tests):**
  - Missing OAuth configuration handling
  - OAuth authorization initiation and redirect with CSRF state
  - User cancellation handling (`error=access_denied`)
  - CSRF state parameter mismatch rejection
  - Invalid or expired ID token rejection
  - Unverified Google email rejection
  - First-time Google user auto-registration and dashboard redirect
  - Returning Google user direct login
  - Safe account-linking requiring password verification on email collision
  - Prevention of local password login on OAuth-only accounts
  - Logout clearing Google session
  - Unauthenticated access prevention on protected routes
