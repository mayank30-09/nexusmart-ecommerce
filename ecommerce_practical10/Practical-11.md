# Practical-11

**TITLE:** Practical-11: Software Testing (Black-Box & White-Box Testing)  
**AIM:** Perform testing for the 3 modules implemented in Practical-10 using black-box and white-box testing methods.  

---

## 1. Modules Tested

Testing was conducted on the three core modules implemented for the E-Commerce Website (Practical-10):

1. **Module 1: Customer Registration / Authentication**
   - Customer account creation with validation (required fields, email format, password minimum length, password confirmation match, duplicate email check).
   - Password hashing and verification using `werkzeug.security`.
   - Customer login, active session management, and logout.
   - Protected route access control (`@login_required`).
   - Google OAuth 2.0 flow handling, CSRF anti-forgery state verification, token exchange, and safe account linking.

2. **Module 2: Product Search / Filtering**
   - Full catalog retrieval and dynamic category list aggregation.
   - Case-insensitive keyword search by product name.
   - Category filtering.
   - Minimum and maximum price threshold filtering.
   - Combined multi-parameter search and filtering.
   - Boundary checks (non-numeric price inputs, inverted price ranges, zero matching results).
   - Filter reset and catalog restoration.

3. **Module 3: Cart Management**
   - Adding products to the shopping cart.
   - Quantity increment for items already present (duplicate prevention).
   - Stock inventory limits on add and update operations.
   - Cart item quantity update and single item removal.
   - Complete cart clearing.
   - Item subtotal calculation: $\text{Price} \times \text{Quantity}$.
   - Cart grand total calculation: $\sum \text{Item Subtotals}$.
   - Customer cart isolation (preventing cross-customer viewing, updating, or deleting).

---

## 2. Testing Tools Used

- **Test Frameworks:** `pytest 9.1.1` and Python built-in `unittest`
- **HTTP / Route Testing:** Flask Test Client (`app.test_client()`)
- **Code Coverage Tool:** `coverage 7.17.0` (with branch coverage `--branch`) and `pytest-cov 7.1.0`
- **Mocking & Isolation:** `unittest.mock` (`patch`, `MagicMock`) for Google OAuth token endpoints
- **Database Isolation:** Python `tempfile` SQLite instances to prevent mutation of actual project data (`ecommerce.db`)
- **Document Generation:** `python-docx 1.2.0`

---

## 3. Black-Box Testing: Test Cases and Actual Results

Black-box test cases evaluate external system behavior, inputs, and expected outputs without relying on internal code implementation.

### Module 1: Customer Registration / Authentication

| Test ID | Module | Input / Action | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-BB-AUTH-01** | Customer Auth | Submit registration with valid Name, Email, Password, Confirm Password. | Account created; redirect to `/login` with *"Registration successful!"* | Redirected to login; success message displayed; user created in DB. | **PASS** |
| **TC-BB-AUTH-02** | Customer Auth | Submit registration with blank required fields (Name or Email empty). | Form rejected with alert: *"All fields are required."* | Form rejected; warning alert displayed; no user created. | **PASS** |
| **TC-BB-AUTH-03** | Customer Auth | Submit registration with invalid email formats (e.g. `not-an-email`, `user@`). | Rejected with alert: *"Please enter a valid email address."* | Form rejected; validation alert displayed. | **PASS** |
| **TC-BB-AUTH-04** | Customer Auth | Submit registration with mismatched passwords. | Rejected with alert: *"Passwords do not match. Please re-enter."* | Form rejected; mismatch message displayed. | **PASS** |
| **TC-BB-AUTH-05** | Customer Auth | Submit registration with an already registered email. | Rejected with alert: *"An account with this email already exists."* | Duplicate blocked; error alert displayed. | **PASS** |
| **TC-BB-AUTH-06** | Customer Auth | Login with valid registered email and password. | Session created; redirect to `/dashboard` with personalized welcome. | Redirected to dashboard; session established; welcome banner shown. | **PASS** |
| **TC-BB-AUTH-07** | Customer Auth | Login with incorrect password or non-existent email. | Rejected with alert: *"Invalid email or password. Please try again."* | Login rejected; error alert displayed; session not set. | **PASS** |
| **TC-BB-AUTH-08** | Customer Auth | Login with blank email or blank password. | Rejected with alert: *"Please enter both email and password."* | Alert displayed; form submission halted. | **PASS** |
| **TC-BB-AUTH-09** | Customer Auth | Authenticated customer clicks Logout (`/logout`). | Session destroyed; redirect to `/login` with logout notice. | Session cleared; redirected to login with confirmation. | **PASS** |
| **TC-BB-AUTH-10** | Customer Auth | Unauthenticated user accesses `/dashboard`, `/products`, `/cart`. | Access blocked; redirect to `/login` with *"Please login..."* | Redirected to login; warning flash displayed on all protected routes. | **PASS** |
| **TC-BB-AUTH-11** | Customer Auth | Access `/auth/google/login` without `GOOGLE_CLIENT_ID` in `.env`. | Graceful redirect to `/login` with configuration notice. | Redirected to login with *"Google OAuth is not configured..."* | **PASS** |
| **TC-BB-AUTH-12** | Customer Auth | Live interactive Google Sign-In with live external Google accounts. | Redirect to Google, authenticate user, callback creates account. | Live external test requires live Google Cloud Console credentials & interactive browser. | **NOT TESTED** |

### Module 2: Product Search / Filtering

| Test ID | Module | Input / Action | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-BB-PROD-01** | Search & Filter | Navigate to `/products` without filter parameters. | Display all 10 products and populate 5 category filter options. | Full catalog rendered; 5 distinct categories present in dropdown. | **PASS** |
| **TC-BB-PROD-02** | Search & Filter | Search by product name: `search=Headphones`. | Display only "Noise-Canceling Wireless Headphones". | Only headphones card displayed; other products excluded. | **PASS** |
| **TC-BB-PROD-03** | Search & Filter | Search with lowercase keyword: `search=shoes`. | Case-insensitive match displays "Lightweight Running Sports Shoes". | Sports shoes displayed; case insensitivity verified. | **PASS** |
| **TC-BB-PROD-04** | Search & Filter | Filter by category: `category=Footwear`. | Display only Footwear items (Running Shoes and Canvas Sneakers). | Exactly 2 Footwear products rendered; other categories excluded. | **PASS** |
| **TC-BB-PROD-05** | Search & Filter | Minimum price filter: `min_price=2000`. | Display only items with $\text{Price} \ge ₹2000$ (Headphones ₹2999). | Only items $\ge ₹2000$ displayed; cheaper products excluded. | **PASS** |
| **TC-BB-PROD-06** | Search & Filter | Maximum price filter: `max_price=800`. | Display only items with $\text{Price} \le ₹800$ (T-Shirt ₹499, Sunglasses ₹699). | Only items $\le ₹800$ displayed; expensive products excluded. | **PASS** |
| **TC-BB-PROD-07** | Search & Filter | Combined filter: `search=Watch&category=Accessories&min_price=1000&max_price=2000`. | Displays only "Minimalist Stainless Steel Wristwatch" (₹1499). | Single matching item displayed; Electronics watch excluded. | **PASS** |
| **TC-BB-PROD-08** | Search & Filter | Search for non-existent product: `search=UnobtaniumDevice999`. | Display empty state: *"No products found..."* | Empty state banner rendered; 0 product cards displayed. | **PASS** |
| **TC-BB-PROD-09** | Search & Filter | Invalid price input (`min_price=abc` or `min_price=3000&max_price=1000`). | Non-numeric ignored; inverted range returns 0 items without 500 crash. | Handled gracefully (HTTP 200); catalog displayed safely. | **PASS** |
| **TC-BB-PROD-10** | Search & Filter | Click "Clear" or navigate to `/products`. | Reset all filters and restore all 10 products. | All filter constraints cleared; full catalog displayed. | **PASS** |

### Module 3: Cart Management

| Test ID | Module | Input / Action | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-BB-CART-01** | Cart Management | Add Product 1 (qty=2) via POST `/cart/add`. | Item added to cart; redirect to `/cart` with success notice. | Item appears in cart table with qty=2 and subtotal ₹5998.00. | **PASS** |
| **TC-BB-CART-02** | Cart Management | Add same Product 1 again (qty=3) via POST `/cart/add`. | Existing item updated to qty=5; no duplicate row created. | Single cart row displayed with updated quantity 5. | **PASS** |
| **TC-BB-CART-03** | Cart Management | Update quantity to 4 via POST `/cart/update/<id>`. | Quantity updated to 4 in database; subtotal recomputed. | Cart table reflects updated quantity 4 and new subtotal. | **PASS** |
| **TC-BB-CART-04** | Cart Management | Remove product via POST `/cart/remove/<id>`. | Item deleted from cart; notice: *"Removed '...' from your cart."* | Item deleted; table updated accordingly. | **PASS** |
| **TC-BB-CART-05** | Cart Management | Clear entire cart via POST `/cart/clear`. | All customer items deleted; displays empty cart view. | Empty cart banner shown: *"Your Cart is Currently Empty"*. | **PASS** |
| **TC-BB-CART-06** | Cart Management | Add or update quantity exceeding stock (qty=25 for stock=12). | Operation rejected with notice: *"Only 12 item(s) in stock..."* | Request blocked; inventory protected; cart unchanged. | **PASS** |
| **TC-BB-CART-07** | Cart Management | Verify item subtotal calculation (3 units of ₹499.00). | $\text{Subtotal} = 499.00 \times 3 = ₹1497.00$. | Rendered as `₹1497.00` in cart table. | **PASS** |
| **TC-BB-CART-08** | Cart Management | Verify cart grand total (2x ₹499.00 + 1x ₹1199.00). | $\text{Grand Total} = 998.00 + 1199.00 = ₹2197.00$. | Rendered as `₹2197.00` in total amount box. | **PASS** |
| **TC-BB-CART-09** | Cart Management | View cart when empty. | Displays friendly empty view with link to product catalog. | Empty state rendered with "Explore Products Now" button. | **PASS** |
| **TC-BB-CART-10** | Cart Management | Access `/cart` routes without login. | Redirect to `/login` with warning: *"Please login..."* | Redirected to login across all cart endpoints. | **PASS** |
| **TC-BB-CART-11** | Cart Management | Customer B logs in after Customer A adds items. | Customer B sees empty cart; cannot view/edit Customer A items. | Customer isolation verified; cross-user edits rejected. | **PASS** |

---

## 4. White-Box Testing: Tested Functions, Code Paths, and Coverage Results

White-box testing inspected internal source code paths, conditional logic branches, query generation, and security controls across `app.py` and `database.py`.

### Tested Code Paths

1. **Registration & Duplicate Checks (`register()` in `app.py`):**
   - Condition 1: Missing field validation (`not name or not email...`).
   - Condition 2: Email regex match (`re.match(...)`).
   - Condition 3: Minimum password length (`len(password) < 6`).
   - Condition 4: Password confirmation equality (`password != confirm_password`).
   - Condition 5: Duplicate check via `SELECT id FROM customers WHERE email = ?`.
   - Condition 6: Hashing via `generate_password_hash()` and database insert.

2. **Authentication Logic (`login()`, `login_required()`, `logout()`):**
   - Condition 1: Empty credentials validation.
   - Condition 2: Customer existence lookup.
   - Condition 3: Password-less OAuth user detection (`customer["password_hash"] is None`).
   - Condition 4: Hash verification via `check_password_hash()`.
   - Condition 5: Session initialization and destruction (`session.clear()`).
   - Condition 6: Route protection decorator (`"customer_id" not in session`).

3. **Google OAuth 2.0 Security Paths (`google_login()`, `google_callback()`, `link_account()`):**
   - Anti-forgery state generation (`secrets.token_urlsafe(32)`) and CSRF validation (`state != saved_state`).
   - Google cancellation handling (`error == "access_denied"`).
   - Network failure and non-200 token response handling.
   - ID Token verification (`verify_oauth2_token`), expiration, and issuer check.
   - Email verification enforcement (`email_verified == True`).
   - First-time user creation vs. returning user login.
   - Safe account linking: prevents automatic account merge when email exists; requires existing password verification before linking `google_id`.

4. **Product Search & Dynamic SQL Generation (`products()` in `app.py`):**
   - Dynamic query builder constructing `WHERE 1=1` with parameterized conditions.
   - Keyword branch: `AND name LIKE ?` with wildcard parameters.
   - Category branch: `AND category = ?`.
   - Price branches: `AND price >= ?` and `AND price <= ?` with `ValueError` exception safety.
   - Distinct category extraction query.

5. **Cart Operations & Math Logic (`view_cart()`, `add_to_cart()`, `update_cart_quantity()`, etc.):**
   - Customer isolation filtering (`WHERE customer_id = ?`).
   - Subtotal formula: `round(row["price"] * row["quantity"], 2)`.
   - Cart grand total formula: `round(sum(subtotals), 2)`.
   - Quantity boundary checking against inventory (`new_total_qty > product["stock"]`).
   - Duplicate prevention logic: updates existing `cart_items` row instead of inserting duplicate rows.
   - Ownership verification on update and remove (`WHERE id = ? AND customer_id = ?`).
   - Cart badge context processor (`inject_cart_count()`).

### Code Coverage Results

Coverage was measured using `coverage run --branch -m pytest tests/`:

```text
Name                                Stmts   Miss Branch BrPart  Cover   Missing
-------------------------------------------------------------------------------
ecommerce_practical10\app.py          409      4    102      2    99%   70->72, 308-310, 766
ecommerce_practical10\database.py      41     13      8      2    65%   43-69, 186-187
tests\__init__.py                       0      0      0      0   100%
tests\conftest.py                      67     16      6      2    75%   14->17, 39->exit, 42-43, 62-65, 72-79, 86-98
tests\test_auth.py                    361      2      8      2    99%   19, 600
tests\test_cart.py                    174      2      4      2    98%   20, 296
tests\test_products.py                 96      2      6      2    96%   19, 158
-------------------------------------------------------------------------------
TOTAL                                1148     39    134     12    96%
```

- **Application Logic Coverage (`app.py`):** **99% statement coverage**, **98% branch coverage**.
- **Overall Codebase Coverage:** **96%**.
- **Uncovered lines explanation:**
  - `app.py:766`: Standalone entry point `app.run()`, only executed during direct CLI execution.
  - `app.py:308-310`: Generic `except Exception` handler for rare token verification errors.
  - `database.py:43-69`: Legacy SQLite table migration block, skipped on fresh test databases.

---

## 5. Failed Tests or Limitations

1. **Google OAuth 2.0 Live External Flow (TC-BB-AUTH-12 - NOT TESTED):**
   - **Reason:** Testing interactive Google OAuth against live Google authentication servers (`accounts.google.com`) requires active Google Cloud Console credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) configured in `.env`, an external internet connection, and manual user consent in a web browser.
   - **Verification Performed:** All internal logic (URL parameter creation, CSRF protection, error callbacks, mock token validation, user creation, returning user login, and password-protected account linking) was tested and passed with 100% pass rate under automated white-box unit tests.

2. **Manual Testing Instructions for Live Google Authentication:**
   - Step 1: Open Google Cloud Console and create an OAuth 2.0 Client ID for Web Application.
   - Step 2: Add `http://127.0.0.1:5000/auth/google/callback` to Authorized Redirect URIs.
   - Step 3: Copy `.env.example` to `.env` and set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
   - Step 4: Run `python app.py` and open `http://127.0.0.1:5000/login`.
   - Step 5: Click **"Sign in with Google"**, authenticate with your Google account, and verify redirection to the customer dashboard.

---

## 6. Final Result

- **Black-Box Testing:** 33 test cases defined; 32 executed and **PASSED**; 1 marked **NOT TESTED** (live external OAuth credentials requirement). Executable pass rate: **100%**.
- **White-Box Testing:** 68 unit test cases executed across 3 test suites (`test_auth.py`, `test_products.py`, `test_cart.py`); **68 PASSED, 0 FAILED**.
- **Code Coverage Achieved:** **99%** statement coverage on main application module (`app.py`), **96%** overall suite coverage.
- **Data Protection:** Isolated temporary SQLite databases ensured that production project data (`ecommerce.db`) remained intact.

Practical-11 testing for all 3 modules completed successfully.
