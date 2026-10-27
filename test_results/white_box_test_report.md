# White-Box Test Report & Structural Code Coverage Analysis

**Project:** E-Commerce Website (Practical-11)  
**Testing Type:** White-Box Testing (Statement Coverage, Branch Coverage, Basis Path Testing, Decision / Condition Coverage)  
**Testing Frameworks:** `pytest 9.1.1`, Python `unittest`, `coverage 7.17.0`, `pytest-cov 7.1.0`  
**Target Codebase:** `ecommerce_practical10/app.py`, `ecommerce_practical10/database.py`  
**Execution Date:** 2026-10-24  

---

## 1. Executive Summary

White-box testing was conducted by analyzing the internal control flow, logic conditions, database query builders, and exception handlers across the three implemented modules. All unit tests were executed against an isolated, temporary SQLite test database to ensure zero mutation or loss of existing project data.

| Component Under Test | Statements | Missed | Branches | Partial Branches | Coverage | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ecommerce_practical10/app.py`** | **409** | **4** | **102** | **2** | **99%** | **PASSED** |
| `ecommerce_practical10/database.py` | 41 | 13 | 8 | 2 | 65% | PASSED |
| `tests/test_auth.py` | 361 | 2 | 8 | 2 | 99% | PASSED |
| `tests/test_cart.py` | 174 | 2 | 4 | 2 | 98% | PASSED |
| `tests/test_products.py` | 96 | 2 | 6 | 2 | 96% | PASSED |
| **TOTAL SUITE** | **1148** | **39** | **134** | **12** | **96%** | **PASSED** |

- **Total Unit Test Cases:** 68
- **Tests Passed:** 68
- **Tests Failed:** 0
- **Execution Time:** ~11.9 seconds

---

## 2. Tested Functions & Code Paths

### Module 1: Customer Registration / Authentication (`test_auth.py`)

#### 1. Function: `register()`
- **Path 1.1 (Session Guard):** If `customer_id` is already in session, redirects immediately to `/dashboard`.
- **Path 1.2 (GET Request):** Renders clean `register.html` template.
- **Path 1.3 (Empty Field Validation):** Checks `not name or not email or not password or not confirm_password`. Displays danger flash `"All fields are required."`.
- **Path 1.4 (Email Format Regex):** Validates email against `^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$`. Rejects invalid addresses with `"Please enter a valid email address."`.
- **Path 1.5 (Password Minimum Length):** Checks `len(password) < 6`. Rejects with `"Password must be at least 6 characters long."`.
- **Path 1.6 (Password Confirmation Match):** Checks `password != confirm_password`. Rejects with `"Passwords do not match. Please re-enter."`.
- **Path 1.7 (Duplicate Email Detection):** Queries `SELECT id FROM customers WHERE email = ?`. Rejects existing emails with `"An account with this email already exists. Please login."`.
- **Path 1.8 (Password Hashing & Storage):** Executes `generate_password_hash(password)` and inserts into SQLite with PBKDF2/SHA-256 hash. Redirects to `/login`.

#### 2. Function: `login()`
- **Path 2.1 (Session Guard):** Redirects active session to `/dashboard`.
- **Path 2.2 (Blank Field Check):** Rejects missing email or password with `"Please enter both email and password."`.
- **Path 2.3 (Customer Lookup & Missing Account):** Queries customer by email. Returns `"Invalid email or password. Please try again."` if not found.
- **Path 2.4 (OAuth-Only Account Guard):** If customer exists but `password_hash is NULL`, prompts user to use Google Sign-In button.
- **Path 2.5 (Password Verification):** Uses `check_password_hash(hash, password)`. Rejects wrong password with `"Invalid email or password."`.
- **Path 2.6 (Session Initiation):** On valid password, clears session, sets `customer_id`, `customer_name`, `customer_email`, and `auth_provider="local"`. Redirects to `/dashboard`.

#### 3. Function: `logout()`
- **Path 3.1 (Session Teardown):** Calls `session.clear()`, displays success flash, and redirects to `/login`.

#### 4. Decorator: `@login_required`
- **Path 4.1 (Unauthorized Access):** If `"customer_id" not in session`, flashes warning and redirects to `/login`.
- **Path 4.2 (Authorized Access):** Passes through to decorated view function.

#### 5. Google OAuth 2.0 Logic: `google_login()`, `google_callback()`, `link_account()`, `cancel_link()`
- **Path 5.1 (Missing Server Config):** Checks `GOOGLE_CLIENT_ID`. If empty, redirects to `/login` with explanatory flash.
- **Path 5.2 (Authorization URL Construction):** Generates 32-byte cryptographically secure anti-forgery `oauth_state` via `secrets.token_urlsafe(32)`. Constructs redirect URL with scopes `openid email profile`.
- **Path 5.3 (Callback User Cancellation):** Handles `error=access_denied` with warning flash.
- **Path 5.4 (CSRF State Validation):** Compares request `state` against `session.pop("oauth_state")`. Rejects mismatches.
- **Path 5.5 (Missing Auth Code / Missing Secrets):** Rejects requests missing `code` or server credentials.
- **Path 5.6 (Token Exchange Error Handling):** Handles `requests.RequestException` and non-200 responses from Google token endpoint.
- **Path 5.7 (ID Token Cryptographic Verification):** Uses `id_token.verify_oauth2_token`. Catches `ValueError` and token expiry.
- **Path 5.8 (Issuer & Verification Checks):** Validates issuer against `accounts.google.com` and asserts `email_verified == True`.
- **Path 5.9 (First-Time User Registration):** Inserts new customer record with `google_id`, `password_hash=NULL`, logs in to dashboard.
- **Path 5.10 (Returning User Login):** Identifies customer by `google_id`, initiates session directly.
- **Path 5.11 (Safe Account Linking):** If email matches an existing local account, sets `pending_google_link` and redirects to `/auth/google/link`. Verifies existing account password before linking `google_id`.
- **Path 5.12 (Direct In-Session Account Link):** Handles `action="link"` for logged-in users, detecting conflict if Google ID is already linked to another user.

---

### Module 2: Product Search / Filtering (`test_products.py`)

#### Function: `products()`
- **Path 1 (Category List Query):** Executes `SELECT DISTINCT category FROM products ORDER BY category;` to populate dropdown.
- **Path 2 (Dynamic SQL Building - Keyword Search):**
  - If `search_query` is provided, appends `AND name LIKE ?` with `%query%`.
- **Path 3 (Dynamic SQL Building - Category Filter):**
  - If `selected_category` is provided, appends `AND category = ?`.
- **Path 4 (Dynamic SQL Building - Minimum Price):**
  - Attempts `float(min_price)`. If valid, appends `AND price >= ?`. Catches `ValueError` gracefully on invalid input.
- **Path 5 (Dynamic SQL Building - Maximum Price):**
  - Attempts `float(max_price)`. If valid, appends `AND price <= ?`. Catches `ValueError` gracefully on invalid input.
- **Path 6 (Multi-Parameter Combination):** Combines keyword, category, min price, and max price in a single parameterized SQL query.
- **Path 7 (Inverted Price Range / Zero Match):** Evaluates `min_price > max_price`, returning empty dataset and rendering the empty search state.
- **Path 8 (Filter Reset / Clear):** Accessing `/products` with no query parameters removes all WHERE conditions and returns all products.

---

### Module 3: Cart Management (`test_cart.py`)

#### 1. Function: `view_cart()`
- **Path 1.1 (Customer Isolation):** Queries `cart_items` with `WHERE ci.customer_id = ?`.
- **Path 1.2 (Subtotal Calculation):** Computes `subtotal = round(price * quantity, 2)` for each item.
- **Path 1.3 (Cart Total Calculation):** Computes `cart_total = round(sum(subtotals), 2)`.
- **Path 1.4 (Empty Cart State):** When items list is empty, renders empty state banner with product browsing link.

#### 2. Function: `add_to_cart()`
- **Path 2.1 (Input Parsing & Validation):** Validates `product_id` and `quantity`. Rejects non-integers and quantities $\le 0$.
- **Path 2.2 (Product Existence):** Looks up product in `products` table. Rejects missing product IDs with `"Product not found."`.
- **Path 2.3 (Existing Item Detection):** Checks if customer already has this `product_id` in `cart_items`.
- **Path 2.4 (Stock Boundary Validation):** Evaluates `new_total_qty > product["stock"]`. If exceeded, rejects operation and flashes available stock notice.
- **Path 2.5 (Increment Existing Row):** If already present and within stock, executes `UPDATE cart_items SET quantity = ?`.
- **Path 2.6 (Insert New Row):** If not present, executes `INSERT INTO cart_items (customer_id, product_id, quantity)`.

#### 3. Function: `update_cart_quantity()`
- **Path 3.1 (Input Validation):** Parses `quantity`. Rejects non-integers and values $\le 0$ with `"Quantity must be at least 1..."`.
- **Path 3.2 (Ownership & Existence Check):** Queries `cart_items` where `ci.id = ? AND ci.customer_id = ?`. If missing or owned by another user, rejects with `"Cart item not found."`.
- **Path 3.3 (Stock Limit Check):** Validates `new_qty > item["stock"]`. Rejects with warning if inventory is exceeded.
- **Path 3.4 (Database Update):** Executes `UPDATE cart_items SET quantity = ? WHERE id = ? AND customer_id = ?`.

#### 4. Function: `remove_cart_item()`
- **Path 4.1 (Owned Item Deletion):** Verifies ownership via `customer_id`. Executes `DELETE FROM cart_items WHERE id = ? AND customer_id = ?`.
- **Path 4.2 (Unauthorized / Missing Item):** Rejects deletion with `"Item could not be found in your cart."`.

#### 5. Function: `clear_cart()`
- **Path 5.1 (Customer Cart Wipe):** Executes `DELETE FROM cart_items WHERE customer_id = ?`. Confirms only the current customer's items are removed.

#### 6. Context Processor: `inject_cart_count()`
- **Path 6.1 (Unauthenticated):** Returns `cart_count = 0`.
- **Path 6.2 (Authenticated):** Executes `SELECT COALESCE(SUM(quantity), 0) FROM cart_items WHERE customer_id = ?` and injects count into template context.

---

## 3. Temporary Test Database Strategy

To guarantee that actual project data (`ecommerce.db`) is never corrupted or deleted during automated testing:
1. `tests/conftest.py` creates a unique temporary database file via `tempfile.NamedTemporaryFile`.
2. The global `database.DB_PATH` is dynamically pointed to the temporary file path.
3. `database.init_db()` is invoked on the temporary database, seeding test tables and initial products.
4. Each test suite runs in isolation, resetting mutable tables between tests.
5. On test teardown, the temporary database file is cleanly deleted from the filesystem.
6. The actual database containing customer data remains completely untouched.

---

## 4. Coverage Summary & Analysis

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

### Explanation of Remaining Uncovered Lines:
- **`app.py:766` (`app.run()`):** Standalone server startup block executed only when running `python app.py` directly, omitted during test suite import.
- **`app.py:308-310` (`except Exception as ex:`):** Generic fallback exception handler for token verification errors beyond `ValueError`.
- **`database.py:43-69` (Schema Migration):** One-time database migration block executed only when upgrading legacy SQLite tables without `google_id`; skipped during fresh test database initialization.
